"""Layered reasoning bridge for the Phase 6G consumer society runtime."""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
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

    def __init__(
        self,
        llm_client_factory: Callable[[], Any] | None = None,
        per_call_timeout_seconds: float | None = None,
    ):
        self.llm_client_factory = llm_client_factory
        self.per_call_timeout_seconds = float(
            per_call_timeout_seconds
            if per_call_timeout_seconds is not None
            else os.environ.get("SOCIETY_LLM_TIMEOUT_SECONDS", "30")
        )

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
                    {"role": "user", "content": prompt},
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
            future.cancel()
            raise TimeoutError(f"TimeoutError: LLM reasoning exceeded {self.per_call_timeout_seconds}s") from exc
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

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
            "Return JSON with keys: consumer_event_type, quote, trust, purchase_intent, reasoning_summary."
        )

    def _build_evidence_digest(self, findings: List[Any]) -> List[Dict[str, Any]]:
        """Build a structured evidence digest from research findings."""
        digest: List[Dict[str, Any]] = []
        for finding in findings:
            if isinstance(finding, dict):
                fid = finding.get("finding_id", "")
                claim = finding.get("claim", "")
                summary = finding.get("summary")
                display_claim = summary if summary is not None else claim

                evidence_snippets = finding.get("evidence_snippets")
                if evidence_snippets is not None:
                    supporting = list(evidence_snippets) if evidence_snippets else []
                else:
                    supporting = finding.get("supporting_evidence", [])

                contradicting = finding.get("contradicting_evidence", [])
                raw_source_quality = self._derive_source_quality(finding)
                raw_confidence = finding.get("confidence", "")
            else:
                fid = getattr(finding, "finding_id", "")
                claim = getattr(finding, "claim", "")
                summary = getattr(finding, "summary", None)
                display_claim = summary if summary is not None else claim

                evidence_snippets = getattr(finding, "evidence_snippets", None)
                if evidence_snippets is not None:
                    supporting = list(evidence_snippets) if evidence_snippets else []
                else:
                    supporting = getattr(finding, "supporting_evidence", [])

                contradicting = getattr(finding, "contradicting_evidence", [])
                raw_source_quality = self._derive_source_quality_from_obj(finding)
                raw_confidence = getattr(finding, "confidence", "")

            source_quality = self._constrain_source_quality(raw_source_quality)
            confidence = self._constrain_confidence(raw_confidence)

            digest.append({
                "finding_id": fid,
                "claim": display_claim,
                "supporting_evidence": list(supporting) if supporting else [],
                "contradicting_evidence": list(contradicting) if contradicting else [],
                "source_quality": source_quality,
                "confidence": confidence,
            })
        return digest

    @staticmethod
    def _derive_source_quality(finding: Dict[str, Any]) -> Any:
        for key in ("source_quality", "source_label", "source_id", "lane", "source_lane"):
            val = finding.get(key, "")
            if val:
                return val
        source = finding.get("source")
        if source and isinstance(source, dict):
            lane = source.get("lane", "")
            if lane:
                return lane
        return ""

    @staticmethod
    def _derive_source_quality_from_obj(finding: Any) -> Any:
        for key in ("source_quality", "source_label", "source_id", "lane", "source_lane"):
            val = getattr(finding, key, "")
            if val:
                return val
        source = getattr(finding, "source", None)
        if source is not None:
            lane = getattr(source, "lane", "")
            if lane:
                return lane
        return ""

    @staticmethod
    def _constrain_source_quality(value: Any) -> str:
        allowed = {"lane_a", "lane_b", "simulation", "unknown"}
        v = str(value).strip().lower() if value else ""
        if v in allowed:
            return v
        if "public_web" in v or "lane_b" in v:
            return "lane_b"
        if "ingested_document" in v or "brief_background" in v or "lane_a" in v:
            return "lane_a"
        if "auto_enrich" in v or "simulation" in v:
            return "simulation"
        return "unknown"

    @staticmethod
    def _constrain_confidence(value: Any) -> str:
        allowed = {"high", "medium", "low", "unknown"}
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            v = str(value).strip().lower() if value else ""
            return v if v in allowed else "unknown"

        if numeric >= 0.75:
            return "high"
        elif numeric >= 0.45:
            return "medium"
        elif numeric > 0:
            return "low"
        else:
            return "unknown"


__all__ = ["LayeredSocietyReasoningEngine", "VALID_REASONING_MODES"]
