"""Round scheduler for the consumer society runtime."""

from __future__ import annotations

import threading
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, Iterable, List, Mapping, Sequence

from ..reasoning_trace import ReasoningTrace
from ..event_ontology import ConsumerEventType
from ..access_policy import resolve_visible_findings
from .agent_step_executor import AgentStepExecutor
from .dynamic_participation import DynamicParticipationModel, ParticipationDecision
from .population_models import ConsumerSocietyAgent, ConsumerSocietyRunConfig
from .progress_buffer import ProgressBuffer


class RoundScheduler:
    """Schedule agents within a round by layer: core, expanded, shadow."""

    def __init__(
        self,
        executor: AgentStepExecutor,
        population: List[ConsumerSocietyAgent],
        config: ConsumerSocietyRunConfig,
        participation_model: DynamicParticipationModel | None = None,
        network_topology: Mapping[str, Any] | None = None,
        propagation_max_depth: int = 2,
    ):
        self.executor = executor
        self.population = population
        self.config = config
        self.participation_model = participation_model or DynamicParticipationModel(
            seed=config.random_seed
        )
        self.network_topology = dict(network_topology or {})
        self.propagation_max_depth = max(1, int(propagation_max_depth or 1))
        self._incoming_edges = self._build_incoming_edges(self.network_topology.get("edges", []))

    @staticmethod
    def _record_event_counters(event: Mapping[str, Any], counters: Dict[str, Any]) -> None:
        if event.get("llm_invoked"):
            counters["llm_invoked_count"] += 1
        if event.get("reasoning_backend") == "template_fallback":
            counters["template_fallback_count"] += 1
        if event.get("reasoning_backend") == "rules" and not event.get("llm_invoked"):
            counters["rules_count"] += 1

    @staticmethod
    def _progress_step(
        progress_buffer: ProgressBuffer,
        *,
        event: Mapping[str, Any],
        agent: ConsumerSocietyAgent,
        round_index: int,
        total_agents: int,
        counters: Dict[str, Any],
    ) -> None:
        progress_buffer.step_completed(
            status="running",
            phase="agent_reasoning",
            current_round=round_index,
            completed_agents=counters["completed_agents"],
            total_agents=total_agents,
            current_agent_id=agent.agent_id,
            current_layer=agent.layer,
            reasoning_backend=event.get("reasoning_backend", "unknown"),
            llm_invoked_count=counters["llm_invoked_count"],
            rules_count=counters["rules_count"],
            template_fallback_count=counters["template_fallback_count"],
            failed_count=counters["failed_count"],
        )
        progress_buffer.maybe_time_flush()

    def _decide_participation(
        self,
        *,
        agent: ConsumerSocietyAgent,
        round_index: int,
        claims: List[str],
        brief_context: Mapping[str, Any],
        previous_events: List[Dict[str, Any]],
    ) -> ParticipationDecision:
        return self.participation_model.decide(
            agent=agent,
            round_index=round_index,
            claims=claims,
            brief_context=brief_context,
            previous_events=previous_events,
        )

    @staticmethod
    def _build_incoming_edges(edges: Iterable[Mapping[str, Any]]) -> Dict[str, List[Mapping[str, Any]]]:
        incoming: Dict[str, List[Mapping[str, Any]]] = defaultdict(list)
        for edge in edges or []:
            if not isinstance(edge, Mapping):
                continue
            source = str(edge.get("source_agent_id") or "").strip()
            target = str(edge.get("target_agent_id") or "").strip()
            if not source or not target:
                continue
            incoming[target].append(edge)
        return dict(incoming)

    @staticmethod
    def _agent_persona(agent: ConsumerSocietyAgent) -> Dict[str, Any]:
        persona = dict(agent.traits or {})
        persona.setdefault("segment", agent.segment)
        persona.setdefault("role", agent.role.value)
        persona.setdefault("agent_id", agent.agent_id)
        return persona

    def _visible_research_findings(
        self,
        *,
        agent: ConsumerSocietyAgent,
        round_index: int,
        research_findings: Sequence[Any],
    ) -> List[Any]:
        try:
            return list(
                resolve_visible_findings(
                    persona=self._agent_persona(agent),
                    findings=research_findings,
                    round_index=round_index,
                )
            )
        except AttributeError:
            return list(research_findings or [])

    @staticmethod
    def _event_actor_id(event: Mapping[str, Any]) -> str:
        return str(event.get("agent_id") or event.get("actor_id") or "").strip()

    @staticmethod
    def _event_id(event: Mapping[str, Any]) -> str:
        return str(event.get("event_id") or "").strip()

    @staticmethod
    def _edge_strength(edge: Mapping[str, Any]) -> float:
        def _number(key: str, fallback: float) -> float:
            try:
                return float(edge.get(key, fallback))
            except (TypeError, ValueError):
                return fallback

        trust = _number("trust_weight", 0.5)
        influence = _number("influence_weight", 0.5)
        exposure = _number("exposure_frequency", 0.5)
        misread = _number("misread_probability", 0.0)
        base = (trust + influence + exposure) / 3
        return round(max(0.0, min(1.0, base * (1.0 - min(0.8, misread * 0.5)))), 4)

    def _reachable_sources(self, target_agent_id: str) -> Dict[str, Dict[str, Any]]:
        if not self._incoming_edges:
            return {}
        reachable: Dict[str, Dict[str, Any]] = {}
        queue = deque([(target_agent_id, 0, 1.0, [])])
        visited = {target_agent_id}
        while queue:
            current_id, depth, current_strength, path = queue.popleft()
            if depth >= self.propagation_max_depth:
                continue
            for edge in self._incoming_edges.get(current_id, []):
                source_id = str(edge.get("source_agent_id") or "").strip()
                if not source_id or source_id in visited:
                    continue
                edge_strength = self._edge_strength(edge)
                route_strength = round(current_strength * edge_strength, 4)
                route_path = [
                    *path,
                    str(edge.get("edge_id") or f"{source_id}->{current_id}"),
                ]
                reachable[source_id] = {
                    "depth": depth + 1,
                    "strength": route_strength,
                    "edge_path": route_path,
                }
                visited.add(source_id)
                queue.append((source_id, depth + 1, route_strength, route_path))
        return reachable

    def _route_previous_events(
        self,
        *,
        agent: ConsumerSocietyAgent,
        previous_events: Sequence[Mapping[str, Any]],
    ) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
        previous = [dict(event) for event in (previous_events or []) if isinstance(event, Mapping)]
        if not self._incoming_edges:
            context = {
                "router": "broadcast",
                "target_agent_id": agent.agent_id,
                "max_depth": 0,
                "routed_event_ids": [
                    self._event_id(event)
                    for event in previous
                    if self._event_actor_id(event) != agent.agent_id and self._event_id(event)
                ],
                "source_agent_ids": [
                    self._event_actor_id(event)
                    for event in previous
                    if self._event_actor_id(event) and self._event_actor_id(event) != agent.agent_id
                ],
                "routes": [],
                "propagation_strength": 0.0,
            }
            return previous, context

        reachable_sources = self._reachable_sources(agent.agent_id)
        routed: List[Dict[str, Any]] = []
        route_entries: List[Dict[str, Any]] = []
        strengths: List[float] = []
        for event in previous:
            actor_id = self._event_actor_id(event)
            if actor_id == agent.agent_id:
                routed.append(event)
                continue
            route = reachable_sources.get(actor_id)
            if not route:
                continue
            event_id = self._event_id(event)
            routed.append(event)
            route_entries.append(
                {
                    "source_agent_id": actor_id,
                    "event_id": event_id,
                    "depth": route["depth"],
                    "strength": route["strength"],
                    "edge_path": list(route["edge_path"]),
                }
            )
            strengths.append(float(route["strength"]))
        propagation_strength = round(sum(strengths) / len(strengths), 4) if strengths else 0.0
        context = {
            "router": "network_topology_bfs",
            "target_agent_id": agent.agent_id,
            "max_depth": self.propagation_max_depth,
            "routed_event_ids": [
                entry["event_id"] for entry in route_entries if entry.get("event_id")
            ],
            "source_agent_ids": [
                entry["source_agent_id"] for entry in route_entries if entry.get("source_agent_id")
            ],
            "routes": route_entries,
            "propagation_strength": propagation_strength,
        }
        return routed, context

    def _prepare_agent_view(
        self,
        *,
        agent: ConsumerSocietyAgent,
        round_index: int,
        brief_context: Mapping[str, Any],
        research_findings: Sequence[Any],
        previous_events: Sequence[Mapping[str, Any]],
    ) -> Dict[str, Any]:
        routed_events, propagation_context = self._route_previous_events(
            agent=agent,
            previous_events=previous_events,
        )
        visible_findings = self._visible_research_findings(
            agent=agent,
            round_index=round_index,
            research_findings=research_findings,
        )
        scoped_brief_context = dict(brief_context or {})
        scoped_brief_context["propagation_context"] = propagation_context
        agent.state["received_messages"] = [
            event for event in routed_events
            if self._event_actor_id(event) != agent.agent_id
        ]
        return {
            "previous_events": routed_events,
            "research_findings": visible_findings,
            "brief_context": scoped_brief_context,
            "propagation_context": propagation_context,
        }

    @staticmethod
    def _annotate_event_with_propagation(
        event: Dict[str, Any],
        propagation_context: Mapping[str, Any],
    ) -> Dict[str, Any]:
        context = dict(propagation_context or {})
        event["propagation_context"] = context
        event["propagation_strength"] = float(context.get("propagation_strength", 0.0) or 0.0)
        routed_event_ids = [
            str(event_id)
            for event_id in context.get("routed_event_ids", [])
            if str(event_id).strip()
        ]
        if routed_event_ids:
            existing_refs = event.get("source_input_refs") or []
            if isinstance(existing_refs, (str, bytes)):
                refs = [str(existing_refs)]
            else:
                refs = [str(ref) for ref in existing_refs if str(ref or "").strip()]
            event["source_input_refs"] = list(dict.fromkeys([*refs, *routed_event_ids]))
        return event

    def _skipped_participation_event(
        self,
        *,
        agent: ConsumerSocietyAgent,
        round_index: int,
        decision: ParticipationDecision,
    ) -> Dict[str, Any]:
        trust = max(0.0, min(1.0, float(agent.state.get("trust", agent.trust_baseline))))
        purchase_intent = max(0.0, min(1.0, float(agent.state.get("purchase_intent", 0.5))))
        return {
            "event_id": f"{agent.agent_id}:r{round_index}:PARTICIPATION_SKIPPED",
            "round_index": round_index,
            "agent_id": agent.agent_id,
            "segment": agent.segment,
            "role": agent.role.value,
            "layer": agent.layer,
            "consumer_event_type": ConsumerEventType.PARTICIPATION_SKIPPED.value,
            "event_type": ConsumerEventType.IGNORE.value,
            "channel": ConsumerEventType.IGNORE.value,
            "claim": "",
            "trust": round(trust, 4),
            "purchase_intent": round(purchase_intent, 4),
            "quote": "",
            "reasoning_layer": agent.layer,
            "reasoning_method": "dynamic_participation_model",
            "reasoning_backend": "rules",
            "llm_invoked": False,
            "participation": {
                "participated": False,
                "probability": decision.participation_probability,
                "random_draw": decision.random_draw,
                "reason": decision.reason,
                "engagement_level": decision.engagement_level,
                "topic_relevance": decision.topic_relevance,
                "fatigue": decision.fatigue,
                "neighbor_activity": decision.neighbor_activity,
            },
        }

    def _record_skipped_participation(
        self,
        *,
        agent: ConsumerSocietyAgent,
        round_index: int,
        decision: ParticipationDecision,
        progress_buffer: ProgressBuffer,
        counters: Dict[str, Any],
        total_agents: int,
        propagation_context: Mapping[str, Any] | None = None,
    ) -> tuple[Dict[str, Any], ReasoningTrace]:
        event = self._skipped_participation_event(
            agent=agent,
            round_index=round_index,
            decision=decision,
        )
        self._annotate_event_with_propagation(event, propagation_context or {})
        trace = self.executor._trace_from_event(agent, event, round_index)
        counters["completed_agents"] += 1
        counters["rules_count"] += 1
        self._progress_step(
            progress_buffer,
            event=event,
            agent=agent,
            round_index=round_index,
            total_agents=total_agents,
            counters=counters,
        )
        store = getattr(self.executor, "store", None)
        if store is not None and hasattr(store, "append_runtime_event"):
            store.append_runtime_event(
                getattr(self.executor, "simulation_id", ""),
                {
                    "event_type": "agent_participation_skipped",
                    "agent_id": agent.agent_id,
                    "round_index": round_index,
                    "probability": decision.participation_probability,
                    "reason": decision.reason,
                },
            )
        return event, trace

    def run_round(
        self,
        round_index: int,
        claims: List[str],
        brief_context: Mapping[str, Any],
        research_findings: List[Any],
        previous_events: List[Dict[str, Any]],
        budget: Any,
        progress_buffer: ProgressBuffer,
        counters: Dict[str, Any],
    ) -> tuple[List[Dict[str, Any]], List[ReasoningTrace]]:
        """Run one round and return (round_events, reasoning_traces)."""
        core = [a for a in self.population if a.layer == "core"]
        expanded = [a for a in self.population if a.layer == "expanded"]
        shadow = [a for a in self.population if a.layer == "shadow"]
        audit = [a for a in self.population if a.layer == "audit_sample"]

        round_events: List[Dict[str, Any]] = []
        reasoning_traces: List[ReasoningTrace] = []
        total_agents = len(self.population) * self.config.max_rounds

        # Core agents: sequential
        for agent in core + audit:
            view = self._prepare_agent_view(
                agent=agent,
                round_index=round_index,
                brief_context=brief_context,
                research_findings=research_findings,
                previous_events=previous_events,
            )
            decision = self._decide_participation(
                agent=agent,
                round_index=round_index,
                claims=claims,
                brief_context=view["brief_context"],
                previous_events=view["previous_events"],
            )
            if not decision.participated:
                event, trace = self._record_skipped_participation(
                    agent=agent,
                    round_index=round_index,
                    decision=decision,
                    progress_buffer=progress_buffer,
                    counters=counters,
                    total_agents=total_agents,
                    propagation_context=view["propagation_context"],
                )
                round_events.append(event)
                reasoning_traces.append(trace)
                continue
            event, trace = self.executor.execute(
                agent=agent,
                round_index=round_index,
                claims=claims,
                brief_context=view["brief_context"],
                research_findings=view["research_findings"],
                previous_events=view["previous_events"],
                budget=budget,
            )
            self._annotate_event_with_propagation(event, view["propagation_context"])
            trace = self.executor._trace_from_event(agent, event, round_index)
            round_events.append(event)
            reasoning_traces.append(trace)
            counters["completed_agents"] += 1
            self._record_event_counters(event, counters)
            self._progress_step(
                progress_buffer,
                event=event,
                agent=agent,
                round_index=round_index,
                total_agents=total_agents,
                counters=counters,
            )

        # Expanded agents: bounded concurrency, stable output order.
        if expanded:
            budget_lock = threading.Lock()

            class ThreadSafeBudget:
                def __init__(self, wrapped: Any):
                    self._wrapped = wrapped

                def record_llm_call(self, layer: str) -> bool:
                    with budget_lock:
                        return self._wrapped.record_llm_call(layer)

            safe_budget = ThreadSafeBudget(budget)
            indexed_results: List[tuple[int, ConsumerSocietyAgent, Dict[str, Any], ReasoningTrace]] = []
            with ThreadPoolExecutor(max_workers=max(1, int(self.executor.max_concurrency))) as pool:
                futures = {}
                future_views: Dict[Any, Dict[str, Any]] = {}
                for idx, agent in enumerate(expanded):
                    view = self._prepare_agent_view(
                        agent=agent,
                        round_index=round_index,
                        brief_context=brief_context,
                        research_findings=research_findings,
                        previous_events=previous_events,
                    )
                    decision = self._decide_participation(
                        agent=agent,
                        round_index=round_index,
                        claims=claims,
                        brief_context=view["brief_context"],
                        previous_events=view["previous_events"],
                    )
                    if not decision.participated:
                        event, trace = self._record_skipped_participation(
                            agent=agent,
                            round_index=round_index,
                            decision=decision,
                            progress_buffer=progress_buffer,
                            counters=counters,
                            total_agents=total_agents,
                            propagation_context=view["propagation_context"],
                        )
                        indexed_results.append((idx, agent, event, trace))
                        continue
                    future = pool.submit(
                        self.executor.execute,
                        agent=agent,
                        round_index=round_index,
                        claims=claims,
                        brief_context=view["brief_context"],
                        research_findings=view["research_findings"],
                        previous_events=view["previous_events"],
                        budget=safe_budget,
                    )
                    futures[future] = (idx, agent)
                    future_views[future] = view
                for future in as_completed(futures):
                    idx, agent = futures[future]
                    view = future_views.get(future, {"propagation_context": {}})
                    try:
                        event, trace = future.result()
                        self._annotate_event_with_propagation(event, view["propagation_context"])
                        trace = self.executor._trace_from_event(agent, event, round_index)
                    except Exception as exc:
                        base_event = {
                            "event_id": f"{agent.agent_id}:r{round_index}:FAILED",
                            "round_index": round_index,
                            "agent_id": agent.agent_id,
                            "segment": agent.segment,
                            "role": agent.role.value,
                            "layer": agent.layer,
                            "consumer_event_type": "FIRST_IMPRESSION",
                            "claim": "",
                            "trust": 0.5,
                            "purchase_intent": 0.5,
                        }
                        event = self.executor._failed_reasoning_event(
                            agent,
                            base_event,
                            "agent_step_executor",
                            exc,
                        )
                        self._annotate_event_with_propagation(event, view["propagation_context"])
                        trace = self.executor._trace_from_event(agent, event, round_index)
                    indexed_results.append((idx, agent, event, trace))
                    counters["completed_agents"] += 1
                    self._record_event_counters(event, counters)
                    self._progress_step(
                        progress_buffer,
                        event=event,
                        agent=agent,
                        round_index=round_index,
                        total_agents=total_agents,
                        counters=counters,
                    )

            for _, agent, event, trace in sorted(indexed_results, key=lambda item: item[0]):
                round_events.append(event)
                reasoning_traces.append(trace)

        # Shadow agents: batch rule execution (no LLM), one aggregate trace.
        if shadow:
            shadow_indexed_results: List[tuple[int, Dict[str, Any], ReasoningTrace]] = []
            active_shadow: List[tuple[int, ConsumerSocietyAgent]] = []
            shadow_views: Dict[str, Dict[str, Any]] = {}
            for idx, agent in enumerate(shadow):
                view = self._prepare_agent_view(
                    agent=agent,
                    round_index=round_index,
                    brief_context=brief_context,
                    research_findings=research_findings,
                    previous_events=previous_events,
                )
                decision = self._decide_participation(
                    agent=agent,
                    round_index=round_index,
                    claims=claims,
                    brief_context=view["brief_context"],
                    previous_events=view["previous_events"],
                )
                if not decision.participated:
                    event, trace = self._record_skipped_participation(
                        agent=agent,
                        round_index=round_index,
                        decision=decision,
                        progress_buffer=progress_buffer,
                        counters=counters,
                        total_agents=total_agents,
                        propagation_context=view["propagation_context"],
                    )
                    shadow_indexed_results.append((idx, event, trace))
                else:
                    shadow_views[agent.agent_id] = view
                    active_shadow.append((idx, agent))

            batch_events, batch_traces = self.executor.execute_shadow_batch(
                agents=[agent for _, agent in active_shadow],
                round_index=round_index,
                claims=claims,
                brief_context=brief_context,
                research_findings=research_findings,
                previous_events=previous_events,
                agent_brief_contexts={
                    agent_id: view["brief_context"] for agent_id, view in shadow_views.items()
                },
                agent_research_findings={
                    agent_id: view["research_findings"] for agent_id, view in shadow_views.items()
                },
                agent_previous_events={
                    agent_id: view["previous_events"] for agent_id, view in shadow_views.items()
                },
            )
            for (idx, _), event in zip(active_shadow, batch_events):
                agent = next(agent for agent_idx, agent in active_shadow if agent_idx == idx)
                view = shadow_views.get(agent.agent_id, {"propagation_context": {}})
                self._annotate_event_with_propagation(event, view["propagation_context"])
                shadow_indexed_results.append(
                    (idx, event, self.executor._trace_from_event(
                        agent,
                        event,
                        round_index,
                    ))
                )
                counters["completed_agents"] += 1
                counters["rules_count"] += 1
            for _, event, trace in sorted(shadow_indexed_results, key=lambda item: item[0]):
                round_events.append(event)
                reasoning_traces.append(trace)
            reasoning_traces.extend(batch_traces)
            progress_buffer.step_completed(
                status="running",
                phase="agent_reasoning",
                current_round=round_index,
                completed_agents=counters["completed_agents"],
                total_agents=total_agents,
                current_agent_id="shadow_batch",
                current_layer="shadow",
                reasoning_backend="rules",
                llm_invoked_count=counters["llm_invoked_count"],
                rules_count=counters["rules_count"],
                template_fallback_count=counters["template_fallback_count"],
                failed_count=counters["failed_count"],
            )
            progress_buffer.maybe_time_flush()

        return round_events, reasoning_traces


__all__ = ["RoundScheduler"]
