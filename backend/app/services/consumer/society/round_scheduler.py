"""Round scheduler for the consumer society runtime."""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Mapping

from ..reasoning_trace import ReasoningTrace
from .agent_step_executor import AgentStepExecutor
from .population_models import ConsumerSocietyAgent, ConsumerSocietyRunConfig
from .progress_buffer import ProgressBuffer


class RoundScheduler:
    """Schedule agents within a round by layer: core, expanded, shadow."""

    def __init__(
        self,
        executor: AgentStepExecutor,
        population: List[ConsumerSocietyAgent],
        config: ConsumerSocietyRunConfig,
    ):
        self.executor = executor
        self.population = population
        self.config = config

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
            event, trace = self.executor.execute(
                agent=agent,
                round_index=round_index,
                claims=claims,
                brief_context=brief_context,
                research_findings=research_findings,
                previous_events=previous_events,
                budget=budget,
            )
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
                futures = {
                    pool.submit(
                        self.executor.execute,
                        agent=agent,
                        round_index=round_index,
                        claims=claims,
                        brief_context=brief_context,
                        research_findings=research_findings,
                        previous_events=previous_events,
                        budget=safe_budget,
                    ): (idx, agent)
                    for idx, agent in enumerate(expanded)
                }
                for future in as_completed(futures):
                    idx, agent = futures[future]
                    try:
                        event, trace = future.result()
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
            batch_events, batch_traces = self.executor.execute_shadow_batch(
                agents=shadow,
                round_index=round_index,
                claims=claims,
                brief_context=brief_context,
                research_findings=research_findings,
                previous_events=previous_events,
            )
            for event in batch_events:
                round_events.append(event)
                counters["completed_agents"] += 1
                counters["rules_count"] += 1
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
