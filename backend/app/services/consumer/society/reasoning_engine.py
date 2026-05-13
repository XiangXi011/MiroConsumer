"""Layered reasoning bridge for the Phase 6G consumer society runtime."""

from __future__ import annotations

import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from typing import Any, Callable, Dict, Iterable, List, Mapping

from ....config import Config
from ....security.prompt_guard import get_prompt_guard
from ....utils.llm_governance import get_fallback_response, validate_llm_output
from ..event_ontology import ConsumerEventType
from .population_models import ConsumerSocietyAgent
from .reasoning_evidence_digest import build_evidence_digest

logger = logging.getLogger(__name__)


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


def _text(value: Any) -> str:
    return str(value or "").strip()


def _reasoning_triplet(perception: str, decision: str, expression: str) -> List[Dict[str, str]]:
    if not any((perception, decision, expression)):
        return []
    return [{"input": perception, "evidence": decision, "conclusion": expression}]


def _fallback_segments(
    *,
    agent: ConsumerSocietyAgent,
    event: Mapping[str, Any],
    reasoning_mode: str,
    quote: str,
    reasoning_summary: str,
) -> Dict[str, str]:
    claim = _text(event.get("claim")) or "consumer claim"
    event_type = _text(event.get("consumer_event_type")) or "consumer reaction"
    role = agent.role.value
    mode = reasoning_mode.replace("_", " ")
    summary = _text(reasoning_summary)
    perception = (
        f"Perception: agent={agent.agent_id}, segment={agent.segment}, "
        f"role={role}, claim={claim}."
    )
    decision = (
        f"Decision: event_type={event_type}, mode={mode}, "
        f"trust={event.get('trust', '')}, summary={summary or 'n/a'}."
    )
    expression = f"Expression: {quote or summary or 'No expression generated.'}"
    return {
        "perception_reasoning": perception,
        "decision_reasoning": decision,
        "expression_reasoning": expression,
    }


def _apply_segmented_reasoning(
    *,
    event: Dict[str, Any],
    agent: ConsumerSocietyAgent,
    reasoning_mode: str,
    quote: str,
    reasoning_summary: str,
    payload: Mapping[str, Any] | None = None,
) -> None:
    payload = payload or {}
    fallback = _fallback_segments(
        agent=agent,
        event=event,
        reasoning_mode=reasoning_mode,
        quote=quote,
        reasoning_summary=reasoning_summary,
    )
    perception = _text(payload.get("perception_reasoning")) or fallback["perception_reasoning"]
    decision = _text(payload.get("decision_reasoning")) or fallback["decision_reasoning"]
    expression = _text(payload.get("expression_reasoning")) or fallback["expression_reasoning"]
    event["perception_reasoning"] = perception
    event["decision_reasoning"] = decision
    event["expression_reasoning"] = expression
    event["reasoning_triplets"] = _reasoning_triplet(perception, decision, expression)


class LayeredSocietyReasoningEngine:
    """Apply L1/L2/L4 reasoning while keeping L3 shadow agents rule-only."""

    def __init__(
        self,
        llm_client_factory: Callable[[], Any] | None = None,
        per_call_timeout_seconds: float | None = None,
        template_fallback_coverage_target: float = 0.15,
        llm_max_retries: int = 3,
        llm_retry_backoff_base: float = 1.0,
        sleep_fn: Callable[[float], None] | None = None,
    ):
        self.llm_client_factory = llm_client_factory
        self.per_call_timeout_seconds = float(
            per_call_timeout_seconds
            if per_call_timeout_seconds is not None
            else os.environ.get("SOCIETY_LLM_TIMEOUT_SECONDS", "30")
        )
        self.template_fallback_coverage_target = float(template_fallback_coverage_target)
        self.llm_max_retries = max(1, int(llm_max_retries or 1))
        self.llm_retry_backoff_base = max(0.0, float(llm_retry_backoff_base or 0.0))
        self.sleep_fn = sleep_fn or time.sleep

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
            last_error: Exception | None = None
            for attempt in range(1, self.llm_max_retries + 1):
                try:
                    event = self._llm_reason(
                        agent=agent,
                        base_event=base_event,
                        brief_context=brief_context,
                        research_findings=research_findings,
                        reasoning_mode=reasoning_mode,
                    )
                    event["retry_attempts"] = attempt - 1
                    if attempt > 1:
                        event["fallback_reason"] = "llm_retry_recovered"
                    return event
                except Exception as exc:
                    last_error = exc
                    if attempt >= self.llm_max_retries:
                        break
                    self.sleep_fn(min(self.llm_retry_backoff_base * (2 ** (attempt - 1)), 8.0))
            event = self._template_reason(
                agent,
                base_event,
                reasoning_mode,
                backend="template_fallback",
            )
            event["retry_attempts"] = self.llm_max_retries
            event["fallback_reason"] = "llm_retry_exhausted"
            event["reasoning_error"] = str(last_error) if last_error else "LLM reasoning failed"
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
        event["quote_metadata"] = {"template_generated": True, "source": backend}
        reasoning_summary = f"{role} response to {claim}"
        if Config.ENABLE_REASONING_TRACE:
            event["reasoning_summary"] = reasoning_summary
        _apply_segmented_reasoning(
            event=event,
            agent=agent,
            reasoning_mode=reasoning_mode,
            quote=event["quote"],
            reasoning_summary=reasoning_summary,
        )
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
        guarded_prompt = get_prompt_guard().wrap_user_content(prompt)

        def _call_llm() -> Dict[str, Any]:
            return client.chat_json(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a consumer society reasoning adapter. "
                            "Return JSON only and keep values inside the provided schema."
                        ),
                    },
                    {"role": "user", "content": guarded_prompt},
                ],
                temperature=0.2 if reasoning_mode == "llm_deep_reasoning" else 0.35,
                max_tokens=700,
                timeout=self.per_call_timeout_seconds,
            )

        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(_call_llm)
        try:
            payload = future.result(timeout=self.per_call_timeout_seconds)
        except FutureTimeoutError as exc:
            if future.done():
                raise
            future.cancel()
            raise TimeoutError(
                f"TimeoutError: LLM reasoning exceeded {self.per_call_timeout_seconds}s"
            ) from exc
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

        event = dict(base_event)
        requested_type = str(payload.get("consumer_event_type", event.get("consumer_event_type", "")))
        if requested_type in {item.value for item in ConsumerEventType}:
            event["consumer_event_type"] = requested_type

        quote = str(payload.get("quote") or event.get("quote") or "")
        reasoning_summary = str(payload.get("reasoning_summary", ""))
        quote_validation = validate_llm_output(quote, context="reasoning_engine.quote")
        summary_validation = validate_llm_output(
            reasoning_summary,
            context="reasoning_engine.summary",
        )

        if not quote_validation["valid"]:
            logger.warning("reasoning_engine quote validation failed: %s", quote_validation["issues"])
            quote = get_fallback_response("opinion")
        if not summary_validation["valid"]:
            logger.warning(
                "reasoning_engine summary validation failed: %s",
                summary_validation["issues"],
            )
            reasoning_summary = "(reasoning summary generation failed)"

        event["quote"] = quote
        event["trust"] = _clamp(payload.get("trust", event.get("trust", 0.5)))
        event["purchase_intent"] = _clamp(
            payload.get("purchase_intent", event.get("purchase_intent", 0.5))
        )
        event["reasoning_layer"] = agent.layer
        event["reasoning_method"] = reasoning_mode
        event["reasoning_backend"] = "llm"
        event["llm_invoked"] = True
        event["quote_metadata"] = {"template_generated": False, "source": "llm"}
        if Config.ENABLE_REASONING_TRACE:
            event["reasoning_summary"] = reasoning_summary
        _apply_segmented_reasoning(
            event=event,
            agent=agent,
            reasoning_mode=reasoning_mode,
            quote=quote,
            reasoning_summary=reasoning_summary,
            payload=payload,
        )
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
        findings_list = list(research_findings)
        evidence_digest = self._build_evidence_digest(findings_list)
        return (
            "Reason about this consumer agent as part of MiroConsumer society runtime.\n"
            f"reasoning_mode: {reasoning_mode}\n"
            f"agent_id: {agent.agent_id}\n"
            f"layer: {agent.layer}\n"
            f"segment: {agent.segment}\n"
            f"role: {agent.role.value}\n"
            f"traits: {agent.traits}\n"
            f"brief_context: {dict(brief_context)}\n"
            f"research_findings_count: {len(findings_list)}\n"
            f"evidence_digest: {evidence_digest}\n"
            f"base_event: {dict(base_event)}\n"
            "Return JSON with keys: consumer_event_type, quote, trust, purchase_intent, reasoning_summary, perception_reasoning, decision_reasoning, expression_reasoning."
        )

    def _build_evidence_digest(self, findings: List[Any]) -> List[Dict[str, Any]]:
        """Build a structured evidence digest from research findings."""
        return build_evidence_digest(list(findings))


__all__ = ["LayeredSocietyReasoningEngine", "VALID_REASONING_MODES"]


