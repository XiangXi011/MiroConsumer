"""Layered reasoning bridge for the Phase 6G consumer society runtime."""

from __future__ import annotations

import os
from typing import Any, Callable, Dict, Iterable, Mapping

from ..event_ontology import ConsumerEventType
from .population_models import ConsumerSocietyAgent


VALID_REASONING_MODES = {
    "llm_deep_reasoning",
    "lightweight_llm",
    "llm_audit_sample",
}


def _clamp(value: Any, fallback: float = 0.5) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = fallback
    return round(max(0.0, min(1.0, numeric)), 4)


class LayeredSocietyReasoningEngine:
    """Apply L1/L2/L4 reasoning while keeping L3 shadow agents rule-only."""

    def __init__(self, llm_client_factory: Callable[[], Any] | None = None):
        self.llm_client_factory = llm_client_factory

    def reason(
        self,
        *,
        agent: ConsumerSocietyAgent,
        base_event: Mapping[str, Any],
        brief_context: Mapping[str, Any],
        research_findings: Iterable[Any],
        reasoning_mode: str,
    ) -> Dict[str, Any]:
        if reasoning_mode not in VALID_REASONING_MODES:
            raise ValueError(f"Unsupported reasoning mode: {reasoning_mode}")

        deterministic = os.environ.get("SOCIETY_DETERMINISTIC_MODE", "").strip().lower() == "mock"
        backend = os.environ.get("SOCIETY_REASONING_BACKEND", "template").strip().lower()
        if backend == "llm" and not deterministic:
            try:
                return self._llm_reason(
                    agent=agent,
                    base_event=base_event,
                    brief_context=brief_context,
                    research_findings=research_findings,
                    reasoning_mode=reasoning_mode,
                )
            except Exception as exc:
                event = self._template_reason(agent, base_event, reasoning_mode, backend="template_fallback")
                event["reasoning_error"] = str(exc)
                return event

        return self._template_reason(
            agent,
            base_event,
            reasoning_mode,
            backend="mock" if deterministic else "template",
        )

    def _template_reason(
        self,
        agent: ConsumerSocietyAgent,
        base_event: Mapping[str, Any],
        reasoning_mode: str,
        backend: str,
    ) -> Dict[str, Any]:
        event = dict(base_event)
        claim = str(event.get("claim", "consumer claim"))
        role = agent.role.value
        event["quote"] = (
            f"{agent.segment} / {role}: I react to {claim} through "
            f"{reasoning_mode.replace('_', ' ')} with trust={event.get('trust')}."
        )
        event["reasoning_layer"] = agent.layer
        event["reasoning_method"] = reasoning_mode
        event["reasoning_backend"] = backend
        event["llm_invoked"] = False
        event["reasoning_summary"] = f"{role} response to {claim}"
        return event

    def _llm_reason(
        self,
        *,
        agent: ConsumerSocietyAgent,
        base_event: Mapping[str, Any],
        brief_context: Mapping[str, Any],
        research_findings: Iterable[Any],
        reasoning_mode: str,
    ) -> Dict[str, Any]:
        client = self._build_llm_client()
        prompt = self._build_prompt(agent, base_event, brief_context, research_findings, reasoning_mode)
        payload = client.chat_json(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a consumer society reasoning adapter. "
                        "Return JSON only and keep values inside the provided schema."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.2 if reasoning_mode == "llm_deep_reasoning" else 0.35,
            max_tokens=700,
        )

        event = dict(base_event)
        requested_type = str(payload.get("consumer_event_type", event.get("consumer_event_type", "")))
        if requested_type in {item.value for item in ConsumerEventType}:
            event["consumer_event_type"] = requested_type
        event["quote"] = str(payload.get("quote") or event.get("quote") or "")
        event["trust"] = _clamp(payload.get("trust", event.get("trust", 0.5)))
        event["purchase_intent"] = _clamp(
            payload.get("purchase_intent", event.get("purchase_intent", 0.5))
        )
        event["reasoning_layer"] = agent.layer
        event["reasoning_method"] = reasoning_mode
        event["reasoning_backend"] = "llm"
        event["llm_invoked"] = True
        event["reasoning_summary"] = str(payload.get("reasoning_summary", ""))
        return event

    def _build_llm_client(self) -> Any:
        if self.llm_client_factory is not None:
            return self.llm_client_factory()
        from ....utils.llm_client import LLMClient

        return LLMClient()

    def _build_prompt(
        self,
        agent: ConsumerSocietyAgent,
        base_event: Mapping[str, Any],
        brief_context: Mapping[str, Any],
        research_findings: Iterable[Any],
        reasoning_mode: str,
    ) -> str:
        return (
            "Reason about this consumer agent as part of MiroConsumer society runtime.\n"
            f"reasoning_mode: {reasoning_mode}\n"
            f"agent_id: {agent.agent_id}\n"
            f"layer: {agent.layer}\n"
            f"segment: {agent.segment}\n"
            f"role: {agent.role.value}\n"
            f"traits: {agent.traits}\n"
            f"brief_context: {dict(brief_context)}\n"
            f"research_findings_count: {len(list(research_findings))}\n"
            f"base_event: {dict(base_event)}\n"
            "Return JSON with keys: consumer_event_type, quote, trust, purchase_intent, reasoning_summary."
        )


__all__ = ["LayeredSocietyReasoningEngine", "VALID_REASONING_MODES"]
