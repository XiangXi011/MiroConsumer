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
    ) -> tuple[List[Dict[str, Any]], List[ReasoningTrace]]:
        """Execute shadow agents as a batch (no LLM) with one aggregate trace."""
        events: List[Dict[str, Any]] = []
        agents_list = list(agents)
        for agent in agents_list:
            event = self.event_mapper.map_agent_event(
                agent=agent,
                round_index=round_index,
                visible_claims=claims,
                previous_events=previous_events,
                brief_context=brief_context,
                research_findings=research_findings,
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

        fallback_reason = ""
        if backend == "template_fallback" and reasoning_error:
            fallback_reason = str(reasoning_error)
        elif backend == "template_fallback":
            fallback_reason = "unknown"

        return ReasoningTrace(
            reasoning_backend=backend,
            llm_invoked=llm_invoked,
            source="society_runtime",
            fallback_reason=fallback_reason,
            model="",
            latency_ms=0.0,
            reasoning_summary=str(quote) if quote else "",
        )


__all__ = ["AgentStepExecutor"]
