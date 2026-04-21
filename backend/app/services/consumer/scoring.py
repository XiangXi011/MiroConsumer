"""Consumer scoring and VOC evidence helpers."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Optional


@dataclass
class ConsumerEvidenceBundle:
    top_resonance_quotes: List[Dict[str, Any]] = field(default_factory=list)
    top_risk_quotes: List[Dict[str, Any]] = field(default_factory=list)
    top_misread_quotes: List[Dict[str, Any]] = field(default_factory=list)
    quote_metadata: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "top_resonance_quotes": self.top_resonance_quotes,
            "top_risk_quotes": self.top_risk_quotes,
            "top_misread_quotes": self.top_misread_quotes,
            "quote_metadata": self.quote_metadata,
        }


@dataclass
class ConsumerAttitudeSummary:
    initial_acceptance: Dict[str, float]
    post_propagation_acceptance: Dict[str, float]
    attitude_shift_rate: float
    initial_counts: Dict[str, int]
    final_counts: Dict[str, int]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "initial_acceptance": self.initial_acceptance,
            "post_propagation_acceptance": self.post_propagation_acceptance,
            "attitude_shift_rate": self.attitude_shift_rate,
            "initial_counts": self.initial_counts,
            "final_counts": self.final_counts,
        }


class ConsumerScoringService:
    """Summarize Phase 1 consumer propagation outcomes."""

    _MISREAD_BUCKETS = {"misread", "question"}

    def build_evidence_bundle(self, events: Iterable[Mapping[str, Any]]) -> ConsumerEvidenceBundle:
        normalized = [self._normalize_quote_event(event) for event in events]
        normalized = [event for event in normalized if event["quote"]]

        resonance_quotes = self._top_quotes(normalized, {"resonance"})
        risk_quotes = self._top_quotes(normalized, {"risk"})
        misread_quotes = self._top_quotes(normalized, self._MISREAD_BUCKETS)

        return ConsumerEvidenceBundle(
            top_resonance_quotes=resonance_quotes,
            top_risk_quotes=risk_quotes,
            top_misread_quotes=misread_quotes,
            quote_metadata=normalized,
        )

    def summarize(
        self,
        initial_labels: Iterable[str],
        final_labels: Iterable[str],
    ) -> ConsumerAttitudeSummary:
        initial = [self._normalize_label(label) for label in initial_labels]
        final = [self._normalize_label(label) for label in final_labels]

        pair_count = min(len(initial), len(final))
        if pair_count == 0:
            attitude_shift_rate = 0.0
        else:
            changed = sum(1 for before, after in zip(initial[:pair_count], final[:pair_count]) if before != after)
            attitude_shift_rate = round(changed / pair_count, 4)

        initial_counts = self._count_labels(initial)
        final_counts = self._count_labels(final)
        return ConsumerAttitudeSummary(
            initial_acceptance=self._to_ratio_dict(initial_counts, len(initial)),
            post_propagation_acceptance=self._to_ratio_dict(final_counts, len(final)),
            attitude_shift_rate=attitude_shift_rate,
            initial_counts=initial_counts,
            final_counts=final_counts,
        )

    def _top_quotes(
        self,
        events: Iterable[Mapping[str, Any]],
        buckets: set[str],
        limit: int = 3,
    ) -> List[Dict[str, Any]]:
        filtered = [event for event in events if event["bucket"] in buckets]
        filtered.sort(
            key=lambda item: (
                -int(item.get("engagement", 0)),
                str(item.get("quote", "")).casefold(),
            )
        )
        return filtered[:limit]

    def _normalize_quote_event(self, event: Mapping[str, Any]) -> Dict[str, Any]:
        quote = str(event.get("quote", "")).strip()
        bucket = str(event.get("bucket", "question")).strip().lower() or "question"
        engagement = int(event.get("engagement", 0) or 0)
        return {
            "quote": quote,
            "bucket": bucket,
            "engagement": engagement,
            "agent_id": event.get("agent_id"),
            "round_num": event.get("round_num"),
        }

    def _normalize_label(self, label: Any) -> str:
        text = str(label or "neutral").strip().lower()
        if text not in {"positive", "neutral", "negative"}:
            return "neutral"
        return text

    def _count_labels(self, labels: Iterable[str]) -> Dict[str, int]:
        counts = Counter(labels)
        return {
            "positive": int(counts.get("positive", 0)),
            "neutral": int(counts.get("neutral", 0)),
            "negative": int(counts.get("negative", 0)),
        }

    def _to_ratio_dict(self, counts: Mapping[str, int], total: int) -> Dict[str, float]:
        if total <= 0:
            return {"positive": 0.0, "neutral": 0.0, "negative": 0.0}
        return {
            label: round(count / total, 4)
            for label, count in counts.items()
        }


@dataclass
class ConsumerPhase2Summary:
    """Phase 2 enriched consumer summary with event-driven evidence."""

    attitude_summary: ConsumerAttitudeSummary
    event_counts: Dict[str, int]
    top_risk_findings: List[Dict[str, Any]]
    top_clarification_opportunities: List[Dict[str, Any]]
    causal_voc_quotes: List[Dict[str, Any]]
    evidence_bundle: ConsumerEvidenceBundle
    cascade_metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "attitude_summary": self.attitude_summary.to_dict(),
            "event_counts": self.event_counts,
            "top_risk_findings": self.top_risk_findings,
            "top_clarification_opportunities": self.top_clarification_opportunities,
            "causal_voc_quotes": self.causal_voc_quotes,
            "evidence_bundle": self.evidence_bundle.to_dict(),
            "cascade_metrics": self.cascade_metrics,
        }


def build_consumer_summary(
    events: Iterable[Any],
    findings: Iterable[Any],
    initial_labels: Optional[Iterable[str]] = None,
    final_labels: Optional[Iterable[str]] = None,
) -> ConsumerPhase2Summary:
    """Build a Phase 2 consumer summary from propagation events and research findings.

    Args:
        events: PropagationEvent objects or dicts.
        findings: ResearchFinding objects or dicts.
        initial_labels: Optional initial attitude labels for baseline metrics.
        final_labels: Optional final attitude labels for shift metrics.

    Returns:
        A ConsumerPhase2Summary with event counts, risk findings, and VOC quotes.
    """
    from .models import PropagationEvent, ResearchFinding

    # Normalize events
    typed_events: List[PropagationEvent] = []
    for e in events:
        if isinstance(e, PropagationEvent):
            typed_events.append(e)
        elif isinstance(e, dict):
            typed_events.append(PropagationEvent(**e))

    # Normalize findings
    typed_findings: List[ResearchFinding] = []
    for f in findings:
        if isinstance(f, ResearchFinding):
            typed_findings.append(f)
        elif isinstance(f, dict):
            typed_findings.append(ResearchFinding(**f))

    # Count events by type
    event_counts: Dict[str, int] = {}
    for event in typed_events:
        event_counts[event.event_type] = event_counts.get(event.event_type, 0) + 1

    # Build top risk findings from events that triggered negative turns
    risk_finding_ids: set[str] = set()
    for event in typed_events:
        if event.event_type in {"risk_discovery", "misread_amplification", "skeptical_challenge"}:
            risk_finding_ids.update(event.trigger_finding_ids)

    top_risk_findings: List[Dict[str, Any]] = []
    for finding in typed_findings:
        if finding.finding_id in risk_finding_ids:
            top_risk_findings.append({
                "finding_id": finding.finding_id,
                "finding_type": finding.finding_type,
                "summary": finding.summary,
                "visibility": finding.visibility.value if hasattr(finding.visibility, "value") else str(finding.visibility),
            })

    # Build clarification opportunities from recovery events
    clarification_finding_ids: set[str] = set()
    for event in typed_events:
        if event.event_type == "clarification_recovery":
            clarification_finding_ids.update(event.trigger_finding_ids)

    top_clarification_opportunities: List[Dict[str, Any]] = []
    for finding in typed_findings:
        if finding.finding_id in clarification_finding_ids:
            top_clarification_opportunities.append({
                "finding_id": finding.finding_id,
                "finding_type": finding.finding_type,
                "summary": finding.summary,
            })

    # Causal VOC quotes from events
    causal_voc_quotes: List[Dict[str, Any]] = []
    for event in typed_events:
        if event.supporting_quote:
            causal_voc_quotes.append({
                "event_id": event.event_id,
                "event_type": event.event_type,
                "quote": event.supporting_quote,
                "actor_id": event.actor_id,
                "round_index": event.round_index,
            })

    # Build attitude summary if labels provided
    if initial_labels is not None and final_labels is not None:
        service = ConsumerScoringService()
        attitude_summary = service.summarize(initial_labels, final_labels)
    else:
        attitude_summary = ConsumerAttitudeSummary(
            initial_acceptance={"positive": 0.0, "neutral": 0.0, "negative": 0.0},
            post_propagation_acceptance={"positive": 0.0, "neutral": 0.0, "negative": 0.0},
            attitude_shift_rate=0.0,
            initial_counts={"positive": 0, "neutral": 0, "negative": 0},
            final_counts={"positive": 0, "neutral": 0, "negative": 0},
        )

    evidence_bundle = ConsumerEvidenceBundle(
        top_resonance_quotes=[],
        top_risk_quotes=[],
        top_misread_quotes=[],
        quote_metadata=[],
    )

    from .cascade_metrics import compute_cascade_metrics

    cascade_metrics = compute_cascade_metrics(
        [e.model_dump() if hasattr(e, "model_dump") else dict(e) for e in typed_events],
    )

    return ConsumerPhase2Summary(
        attitude_summary=attitude_summary,
        event_counts=event_counts,
        top_risk_findings=top_risk_findings,
        top_clarification_opportunities=top_clarification_opportunities,
        causal_voc_quotes=causal_voc_quotes,
        evidence_bundle=evidence_bundle,
        cascade_metrics=cascade_metrics,
    )


__all__ = [
    "ConsumerAttitudeSummary",
    "ConsumerEvidenceBundle",
    "ConsumerPhase2Summary",
    "ConsumerScoringService",
    "build_consumer_summary",
]
