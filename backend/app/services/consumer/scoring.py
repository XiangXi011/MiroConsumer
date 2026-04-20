"""Consumer scoring and VOC evidence helpers."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping


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


__all__ = [
    "ConsumerAttitudeSummary",
    "ConsumerEvidenceBundle",
    "ConsumerScoringService",
]
