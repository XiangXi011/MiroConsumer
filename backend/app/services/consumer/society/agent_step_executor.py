"""Agent step executor for the consumer society runtime."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping

from ..reasoning_trace import ReasoningTrace
from .population_models import ConsumerSocietyAgent


class AgentStepExecutor:
    """Execute a single agent step: event mapping, reasoning, state update, trace collection."""

    def __init__(
        self,
        event_mapper: Any,
        reasoning_engine: Any,
        store: Any,
        simulation_id: str,
        *,
        max_concurrency: int = 8,
    ):
        self.event_mapper = event_mapper
        self.reasoning_engine = reasoning_engine
        self.store = store
        self.simulation_id = simulation_id
        self.max_concurrency = max_concurrency

    def execute(
        self,
        agent: ConsumerSocietyAgent,
        round_index: int,
        claims: List[str],
        brief_context: Mapping[str, Any],
        research_findings: List[Any],
        previous_events: List[Dict[str, Any]],
        budget: Any,
    ) -> tuple[Dict[str, Any], ReasoningTrace]:
        """Execute one agent step and return (event, trace)."""
        event = self.event_mapper.map_agent_event(
            agent=agent,
            round_index=round_index,
            visible_claims=claims,
            previous_events=previous_events,
            brief_context=brief_context,
            research_findings=research_findings,
        )
        reasoning_mode = self._reasoning_mode_for_layer(agent.layer)

        if reasoning_mode is None:
            event["reasoning_layer"] = agent.layer
            event["reasoning_method"] = "rule_state_machine"
            event["reasoning_backend"] = "rules"
            event["llm_invoked"] = False
        elif budget.record_llm_call(agent.layer):
            try:
                event = self.reasoning_engine.reason(
                    agent=agent,
                    base_event=event,
                    brief_context=brief_context,
                    research_findings=research_findings,
                    reasoning_mode=reasoning_mode,
                )
            except Exception as exc:
                event = self._failed_reasoning_event(agent, event, reasoning_mode, exc)
                self.store.append_runtime_event(
                    self.simulation_id,
                    {
                        "event_type": "agent_reasoning_failed",
                        "agent_id": agent.agent_id,
                        "round_index": round_index,
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                        "fallback": "template_fallback",
                    },
                )
                self.store.append_error(
                    self.simulation_id,
                    {
                        "event_type": "agent_reasoning_failed",
                        "agent_id": agent.agent_id,
                        "round_index": round_index,
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                    },
                )
        else:
            event["reasoning_layer"] = agent.layer
            event["reasoning_method"] = "rule_fallback_budget_exhausted"
            event["reasoning_backend"] = "rules"
            event["llm_invoked"] = False

        trace = self._trace_from_event(agent, event, round_index)
        self._update_agent_state(agent, event)
        self.store.append_runtime_event(
            self.simulation_id,
            {
                "event_type": "agent_completed",
                "agent_id": agent.agent_id,
                "round_index": round_index,
                "reasoning_backend": event.get("reasoning_backend", "unknown"),
            },
        )
        return event, trace

    def execute_shadow_batch(
        self,
        agents: Iterable[ConsumerSocietyAgent],
        round_index: int,
        claims: List[str],
        brief_context: Mapping[str, Any],
        research_findings: List[Any],
        previous_events: List[Dict[str, Any]],
        *,
        agent_brief_contexts: Mapping[str, Mapping[str, Any]] | None = None,
        agent_research_findings: Mapping[str, List[Any]] | None = None,
        agent_previous_events: Mapping[str, List[Dict[str, Any]]] | None = None,
    ) -> tuple[List[Dict[str, Any]], List[ReasoningTrace]]:
        """Execute shadow agents as a batch (no LLM) with one aggregate trace."""
        events: List[Dict[str, Any]] = []
        agents_list = list(agents)
        for agent in agents_list:
            scoped_brief_context = (
                agent_brief_contexts.get(agent.agent_id, brief_context)
                if agent_brief_contexts
                else brief_context
            )
            scoped_research_findings = (
                agent_research_findings.get(agent.agent_id, research_findings)
                if agent_research_findings
                else research_findings
            )
            scoped_previous_events = (
                agent_previous_events.get(agent.agent_id, previous_events)
                if agent_previous_events
                else previous_events
            )
            event = self.event_mapper.map_agent_event(
                agent=agent,
                round_index=round_index,
                visible_claims=claims,
                previous_events=scoped_previous_events,
                brief_context=scoped_brief_context,
                research_findings=scoped_research_findings,
            )
            event["reasoning_layer"] = agent.layer
            event["reasoning_method"] = "rule_state_machine"
            event["reasoning_backend"] = "rules"
            event["llm_invoked"] = False
            self._update_agent_state(agent, event)
            self.store.append_runtime_event(
                self.simulation_id,
                {
                    "event_type": "agent_completed",
                    "agent_id": agent.agent_id,
                    "round_index": round_index,
                    "reasoning_backend": "rules",
                },
            )
            events.append(event)
        trace = ReasoningTrace(
            reasoning_backend="rules",
            llm_invoked=False,
            source="society_runtime",
            fallback_reason="",
            model="",
            latency_ms=0.0,
            reasoning_summary=f"shadow_batch:{len(agents_list)} agents",
            perception_reasoning=(
                f"input=shadow_batch; round_index={round_index}; "
                f"agent_count={len(agents_list)}"
            ),
            decision_reasoning="reasoning_method=rule_state_machine; llm_invoked=False",
            expression_reasoning=f"output_events={len(events)}",
            reasoning_triplets=[
                {
                    "input": f"input=shadow_batch; round_index={round_index}; agent_count={len(agents_list)}",
                    "evidence": "reasoning_method=rule_state_machine; llm_invoked=False",
                    "conclusion": f"output_events={len(events)}",
                }
            ],
            round_index=round_index,
        )
        return events, [trace]

    @staticmethod
    def _reasoning_mode_for_layer(layer: str) -> str | None:
        if layer == "core":
            return "llm_deep_reasoning"
        if layer == "expanded":
            return "lightweight_llm"
        if layer == "audit_sample":
            return "llm_audit_sample"
        return None

    @staticmethod
    def _failed_reasoning_event(
        agent: ConsumerSocietyAgent,
        base_event: Mapping[str, Any],
        reasoning_mode: str,
        exc: Exception,
    ) -> Dict[str, Any]:
        event = dict(base_event)
        event["reasoning_layer"] = agent.layer
        event["reasoning_method"] = reasoning_mode
        event["reasoning_backend"] = "template_fallback"
        event["llm_invoked"] = False
        event["reasoning_error"] = str(exc)
        event["quote"] = (
            f"{agent.segment}: 这条信息需要更多证据，我会先保留判断。"
        )
        return event

    @staticmethod
    def _update_agent_state(agent: ConsumerSocietyAgent, event: Mapping[str, Any]) -> None:
        event_type = event.get("consumer_event_type", "")
        trust = float(agent.state.get("trust", agent.trust_baseline))
        purchase = float(agent.state.get("purchase_intent", 0.5))
        if event_type in {"TRUST_DECAY", "ASK_PROOF", "MISREAD_CLAIM", "PRICE_RESISTANCE"}:
            trust -= 0.03 * agent.skepticism
            purchase -= 0.02 * agent.price_sensitivity
        if event_type in {"TRUST_RECOVERY", "AMPLIFY_CLAIM", "PURCHASE_INTENT_UP", "SHARE_TO_CHANNEL"}:
            trust += 0.03 * agent.evidence_sensitivity
            purchase += 0.02 * agent.share_propensity
        agent.state["trust"] = round(max(0.0, min(1.0, trust)), 4)
        agent.state["purchase_intent"] = round(max(0.0, min(1.0, purchase)), 4)
        agent.state["awareness"] = 1.0

    @staticmethod
    def _trace_from_event(
        agent: ConsumerSocietyAgent,
        event: Mapping[str, Any],
        round_index: int,
    ) -> ReasoningTrace:
        backend = str(event.get("reasoning_backend", "unknown") or "unknown")
        llm_invoked = bool(event.get("llm_invoked", False))
        reasoning_error = event.get("reasoning_error", "")
        quote = event.get("quote", "")
        event_id = str(event.get("event_id", "") or "")
        finding_id = AgentStepExecutor._first_value(
            event.get("trigger_finding_ids")
            or event.get("trigger_finding_id")
            or event.get("related_finding_id")
        )
        source_input_refs = AgentStepExecutor._join_values(event.get("source_input_refs"))
        claim = str(event.get("claim", "") or "")
        event_type = str(
            event.get("consumer_event_type")
            or event.get("event_type")
            or event.get("channel")
            or ""
        )
        reasoning_method = str(event.get("reasoning_method", "") or "")

        fallback_reason = ""
        if backend == "template_fallback" and reasoning_error:
            fallback_reason = str(reasoning_error)
        elif backend == "template_fallback":
            fallback_reason = "unknown"

        generated_by = AgentStepExecutor._expression_source(event, backend)
        propagation_context = event.get("propagation_context") if isinstance(event.get("propagation_context"), Mapping) else {}
        visible_finding_ids = AgentStepExecutor._join_values(
            event.get("visible_finding_ids") or event.get("trigger_finding_ids")
        )
        reason_codes = AgentStepExecutor._join_values(event.get("reason_codes"))
        candidate_action_scores = AgentStepExecutor._format_candidate_scores(
            event.get("candidate_action_scores")
            or event.get("candidate_scores")
            or event.get("action_scores")
        )

        fallback_perception = AgentStepExecutor._join_reasoning_parts(
            [
                f"claim={claim}" if claim else "",
                f"agent_id={agent.agent_id}",
                f"segment={agent.segment}",
                f"source_input_refs={source_input_refs}" if source_input_refs else "",
                f"visible_finding_ids={visible_finding_ids}" if visible_finding_ids else "",
                (
                    f"propagation_strength={propagation_context.get('propagation_strength')}"
                    if propagation_context.get("propagation_strength") is not None
                    else ""
                ),
            ]
        )
        perception_reasoning = str(event.get("perception_reasoning") or "").strip() or fallback_perception

        fallback_decision = AgentStepExecutor._join_reasoning_parts(
            [
                f"event_type={event_type}" if event_type else "",
                f"reasoning_method={reasoning_method}" if reasoning_method else "",
                f"trust={event.get('trust')}" if event.get("trust") is not None else "",
                (
                    f"purchase_intent={event.get('purchase_intent')}"
                    if event.get("purchase_intent") is not None
                    else ""
                ),
                f"candidate_action_scores={candidate_action_scores}" if candidate_action_scores else "",
                f"reason_codes={reason_codes}" if reason_codes else "",
            ]
        )
        decision_reasoning = str(event.get("decision_reasoning") or "").strip() or fallback_decision
        decision_reasoning = AgentStepExecutor._append_reasoning_parts(
            decision_reasoning,
            [
                f"candidate_action_scores={candidate_action_scores}" if candidate_action_scores else "",
                f"reason_codes={reason_codes}" if reason_codes else "",
            ],
        )

        fallback_expression = AgentStepExecutor._join_reasoning_parts(
            [
                f"generated_by={generated_by}" if generated_by else "",
                AgentStepExecutor._template_generation_part(event),
                f"quote={quote}" if quote else "",
            ]
        )
        expression_reasoning = str(event.get("expression_reasoning") or "").strip() or fallback_expression
        expression_reasoning = AgentStepExecutor._append_reasoning_parts(
            expression_reasoning,
            [
                f"generated_by={generated_by}" if generated_by else "",
                AgentStepExecutor._template_generation_part(event),
            ],
        )
        reasoning_triplets = AgentStepExecutor._normalize_reasoning_triplets(
            event.get("reasoning_triplets")
        )
        if not reasoning_triplets:
            reasoning_triplets = AgentStepExecutor._build_reasoning_triplets(
                perception_reasoning=perception_reasoning,
                decision_reasoning=decision_reasoning,
                expression_reasoning=expression_reasoning,
                source_input_refs=source_input_refs,
                visible_finding_ids=visible_finding_ids,
                event_type=event_type,
                propagation_context=propagation_context,
                primary_conclusion=str(quote or ""),
            )

        return ReasoningTrace(
            reasoning_backend=backend,
            llm_invoked=llm_invoked,
            source="society_runtime",
            fallback_reason=fallback_reason,
            model=str(event.get("model_version", "") or ""),
            latency_ms=float(event.get("latency_ms", 0.0) or 0.0),
            reasoning_summary=str(event.get("reasoning_summary") or quote or ""),
            perception_reasoning=perception_reasoning,
            decision_reasoning=decision_reasoning,
            expression_reasoning=expression_reasoning,
            reasoning_triplets=reasoning_triplets,
            related_finding_id=finding_id,
            related_event_id=event_id,
            agent_id=agent.agent_id,
            round_index=round_index,
        )

    @staticmethod
    def _first_value(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, (str, bytes)):
            return str(value).strip()
        if isinstance(value, Iterable):
            for item in value:
                text = str(item or "").strip()
                if text:
                    return text
            return ""
        return str(value).strip()

    @staticmethod
    def _join_values(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, (str, bytes)):
            return str(value).strip()
        if isinstance(value, Iterable):
            return ",".join(str(item).strip() for item in value if str(item or "").strip())
        return str(value).strip()

    @staticmethod
    def _join_reasoning_parts(parts: Iterable[str]) -> str:
        return "; ".join(part for part in parts if part)

    @staticmethod
    def _append_reasoning_parts(base: str, parts: Iterable[str]) -> str:
        existing = str(base or "")
        additions = [
            part for part in parts
            if part and part not in existing
        ]
        if not additions:
            return existing
        return AgentStepExecutor._join_reasoning_parts([existing, *additions])

    @staticmethod
    def _expression_source(event: Mapping[str, Any], backend: str) -> str:
        metadata = event.get("quote_metadata")
        if isinstance(metadata, Mapping) and metadata.get("source"):
            return str(metadata.get("source") or "").strip()
        return str(event.get("generated_by") or backend or "").strip()

    @staticmethod
    def _template_generation_part(event: Mapping[str, Any]) -> str:
        metadata = event.get("quote_metadata")
        if isinstance(metadata, Mapping) and "template_generated" in metadata:
            return f"template_generated={bool(metadata.get('template_generated'))}"
        if event.get("reasoning_backend") == "template_fallback":
            return "template_generated=True"
        return ""

    @staticmethod
    def _format_candidate_scores(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, Mapping):
            items = sorted(value.items(), key=lambda item: str(item[0]))
            return ",".join(f"{key}:{score}" for key, score in items)
        if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
            parts: List[str] = []
            for item in value:
                if isinstance(item, Mapping):
                    action = item.get("action") or item.get("event_type") or item.get("name")
                    score = item.get("score")
                    if action is not None and score is not None:
                        parts.append(f"{action}:{score}")
                    elif action is not None:
                        parts.append(str(action))
                else:
                    parts.append(str(item))
            return ",".join(part for part in parts if part)
        return str(value).strip()

    @staticmethod
    def _normalize_reasoning_triplets(value: Any) -> List[Dict[str, str]]:
        if not isinstance(value, list):
            return []
        triplets: List[Dict[str, str]] = []
        for item in value:
            if not isinstance(item, Mapping):
                continue
            triplet = {
                "input": str(item.get("input", "") or ""),
                "evidence": str(item.get("evidence", "") or ""),
                "conclusion": str(item.get("conclusion", "") or ""),
            }
            if any(part.strip() for part in triplet.values()):
                triplets.append(triplet)
        return triplets

    @staticmethod
    def _build_reasoning_triplets(
        *,
        perception_reasoning: str,
        decision_reasoning: str,
        expression_reasoning: str,
        source_input_refs: str,
        visible_finding_ids: str,
        event_type: str,
        propagation_context: Mapping[str, Any],
        primary_conclusion: str = "",
    ) -> List[Dict[str, str]]:
        triplets = [
            {
                "input": perception_reasoning,
                "evidence": decision_reasoning,
                "conclusion": str(primary_conclusion or "").strip() or expression_reasoning,
            }
        ]
        if source_input_refs or propagation_context.get("routed_event_ids"):
            triplets.append(
                {
                    "input": f"source_input_refs={source_input_refs}",
                    "evidence": (
                        f"propagation_strength={propagation_context.get('propagation_strength', 0.0)}"
                    ),
                    "conclusion": f"event_type={event_type}",
                }
            )
        if visible_finding_ids:
            triplets.append(
                {
                    "input": f"visible_finding_ids={visible_finding_ids}",
                    "evidence": decision_reasoning,
                    "conclusion": f"event_type={event_type}",
                }
            )
        return [
            triplet for triplet in triplets
            if any(str(triplet.get(key, "")).strip() for key in ("input", "evidence", "conclusion"))
        ]


__all__ = ["AgentStepExecutor"]
