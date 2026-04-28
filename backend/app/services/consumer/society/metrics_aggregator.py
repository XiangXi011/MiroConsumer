"""Aggregate society-level metrics from consumer events."""

from __future__ import annotations

from typing import Any, Dict, Iterable, Mapping

from ..event_ontology import ConsumerEventType


METRIC_KEYS = (
    "reach_rate",
    "cascade_depth",
    "cross_segment_spread",
    "amplifier_ratio",
    "skeptic_ratio",
    "lurker_ratio",
    "misread_rate",
    "negative_cascade_probability",
    "trust_decay_rate",
    "trust_recovery_rate",
    "evidence_demand_rate",
    "price_resistance_index",
    "purchase_intent_delta",
)


def _clamp(value: float) -> float:
    return round(max(0.0, min(1.0, value)), 4)


class SocietyMetricsAggregator:
    """Compute fixed Phase 6G society metrics."""

    def aggregate(
        self,
        events: Iterable[Mapping[str, Any]],
        population_size: int,
        segments_count: int,
    ) -> Dict[str, Any]:
        rows = list(events)
        total = max(len(rows), 1)
        population = max(int(population_size or 0), 1)
        reached_agents = {str(event.get("agent_id", "")) for event in rows if event.get("agent_id")}
        reached_segments = {str(event.get("segment", "")) for event in rows if event.get("segment")}

        def count(event_type: ConsumerEventType) -> int:
            return sum(1 for event in rows if event.get("consumer_event_type") == event_type.value)

        up = count(ConsumerEventType.PURCHASE_INTENT_UP)
        down = count(ConsumerEventType.PURCHASE_INTENT_DOWN)
        intent_delta = _clamp((up - down + total) / (2 * total))

        return {
            "reach_rate": _clamp(len(reached_agents) / population),
            "cascade_depth": max((int(event.get("round_index", 0) or 0) for event in rows), default=0) + (1 if rows else 0),
            "cross_segment_spread": _clamp(len(reached_segments) / max(int(segments_count or 0), 1)),
            "amplifier_ratio": _clamp((count(ConsumerEventType.AMPLIFY_CLAIM) + count(ConsumerEventType.SHARE_TO_CHANNEL)) / total),
            "skeptic_ratio": _clamp(count(ConsumerEventType.ASK_PROOF) / total),
            "lurker_ratio": _clamp(count(ConsumerEventType.FIRST_IMPRESSION) / total),
            "misread_rate": _clamp(count(ConsumerEventType.MISREAD_CLAIM) / total),
            "negative_cascade_probability": _clamp(count(ConsumerEventType.NEGATIVE_CASCADE) / total),
            "trust_decay_rate": _clamp(count(ConsumerEventType.TRUST_DECAY) / total),
            "trust_recovery_rate": _clamp(count(ConsumerEventType.TRUST_RECOVERY) / total),
            "evidence_demand_rate": _clamp(count(ConsumerEventType.ASK_PROOF) / total),
            "price_resistance_index": _clamp(count(ConsumerEventType.PRICE_RESISTANCE) / total),
            "purchase_intent_delta": intent_delta,
        }


__all__ = ["METRIC_KEYS", "SocietyMetricsAggregator"]
