"""Channel metric aggregation for Phase 6H consumer propagation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Sequence

from ..event_ontology import ConsumerEventType
from .channel_policy import resolve_runtime_channels


FIT_WEIGHT_KEYS = (
    "resonance",
    "purchase_intent_delta",
    "trust_repair_factor",
    "misread_risk",
    "price_resistance",
    "evidence_demand",
)


def _clamp(value: float) -> float:
    return round(max(0.0, min(1.0, float(value))), 4)


def _default_weights_path() -> Path:
    return Path(__file__).with_name("channel_fit_weights.json")


def validate_channel_fit_weights(weights: Mapping[str, Any]) -> Dict[str, float]:
    missing = [key for key in FIT_WEIGHT_KEYS if key not in weights]
    if missing:
        raise ValueError(f"channel fit weights missing keys: {missing}")
    parsed: Dict[str, float] = {}
    for key in FIT_WEIGHT_KEYS:
        value = weights[key]
        if not isinstance(value, (int, float)):
            raise ValueError(f"channel fit weight {key} must be numeric")
        parsed[key] = float(value)
    positive_sum = round(sum(value for value in parsed.values() if value > 0), 2)
    negative_sum = round(sum(abs(value) for value in parsed.values() if value < 0), 2)
    if positive_sum != 0.70:
        raise ValueError("positive weight sum must equal 0.70")
    if negative_sum != 0.30:
        raise ValueError("negative weight absolute sum must equal 0.30")
    return parsed


def load_channel_fit_weights(path: str | Path | None = None) -> Dict[str, float]:
    weights_path = Path(path) if path is not None else _default_weights_path()
    payload = json.loads(weights_path.read_text(encoding="utf-8"))
    return validate_channel_fit_weights(payload)


def calculate_fit_score(values: Mapping[str, Any], weights: Mapping[str, float] | None = None) -> float:
    resolved_weights = validate_channel_fit_weights(weights or load_channel_fit_weights())
    score = 0.0
    for key, weight in resolved_weights.items():
        score += float(values.get(key, 0.0) or 0.0) * weight
    return _clamp(score)


class ChannelMetricsAggregator:
    """Aggregate fixed Phase 6H channel metrics from channel events."""

    def __init__(self, weights_path: str | Path | None = None):
        self.weights_path = weights_path

    def aggregate(
        self,
        events: Iterable[Mapping[str, Any]],
        enabled_channels: Sequence[str] | None,
        mode: str = "large_society",
    ) -> Dict[str, Any]:
        rows = list(events)
        channels = resolve_runtime_channels(enabled_channels, mode)
        weights = load_channel_fit_weights(self.weights_path)
        channel_metrics: Dict[str, Dict[str, float]] = {}

        for channel_id in channels:
            channel_rows = [event for event in rows if event.get("channel_id") == channel_id]
            channel_metrics[channel_id] = self._aggregate_one(channel_rows, weights)

        total_events = max(len(rows), 1)
        cross_events = sum(1 for event in rows if event.get("cross_channel") is True)

        return {
            "channels": channel_metrics,
            "cross_channel_spread": _clamp(cross_events / total_events),
            "best_launch_channel": self._max_channel(channel_metrics, "fit_score"),
            "highest_misread_channel": self._max_channel(channel_metrics, "misread_risk"),
            "highest_evidence_demand_channel": self._max_channel(channel_metrics, "evidence_demand"),
            "highest_price_resistance_channel": self._max_channel(channel_metrics, "price_resistance"),
        }

    def _aggregate_one(
        self,
        events: Sequence[Mapping[str, Any]],
        weights: Mapping[str, float],
    ) -> Dict[str, float]:
        if not events:
            values = {
                "fit_score": 0.0,
                "resonance": 0.0,
                "misread_risk": 0.0,
                "evidence_demand": 0.0,
                "price_resistance": 0.0,
                "trust_objection": 0.0,
                "purchase_intent_delta": 0.0,
                "negative_cascade_probability": 0.0,
                "trust_repair_factor": 0.0,
            }
            return values

        total = max(len(events), 1)

        def count(*event_types: ConsumerEventType) -> int:
            expected = {event.value for event in event_types}
            return sum(1 for event in events if event.get("consumer_event_type") in expected)

        resonance = _clamp(
            count(
                ConsumerEventType.AMPLIFY_CLAIM,
                ConsumerEventType.SHARE_TO_CHANNEL,
                ConsumerEventType.PURCHASE_INTENT_UP,
                ConsumerEventType.FIRST_IMPRESSION,
            )
            / total
        )
        misread_risk = _clamp(
            count(ConsumerEventType.MISREAD_CLAIM, ConsumerEventType.NEGATIVE_CASCADE) / total
        )
        evidence_demand = _clamp(count(ConsumerEventType.ASK_PROOF) / total)
        price_resistance = _clamp(count(ConsumerEventType.PRICE_RESISTANCE) / total)
        trust_repair_factor = _clamp(count(ConsumerEventType.TRUST_RECOVERY) / total)
        trust_objection = _clamp(
            count(ConsumerEventType.ASK_PROOF, ConsumerEventType.TRUST_DECAY) / total
        )
        purchase_intent_delta = _clamp(
            count(
                ConsumerEventType.PURCHASE_INTENT_UP,
                ConsumerEventType.AMPLIFY_CLAIM,
                ConsumerEventType.SHARE_TO_CHANNEL,
            )
            / total
        )
        negative_cascade_probability = _clamp(
            count(ConsumerEventType.NEGATIVE_CASCADE) / total
        )
        values = {
            "resonance": resonance,
            "misread_risk": misread_risk,
            "evidence_demand": evidence_demand,
            "price_resistance": price_resistance,
            "trust_objection": trust_objection,
            "purchase_intent_delta": purchase_intent_delta,
            "negative_cascade_probability": negative_cascade_probability,
            "trust_repair_factor": trust_repair_factor,
        }
        values["fit_score"] = calculate_fit_score(values, weights)
        return values

    def _max_channel(self, channels: Mapping[str, Mapping[str, float]], key: str) -> str:
        if not channels:
            return ""
        return max(channels.items(), key=lambda item: float(item[1].get(key, 0.0)))[0]


__all__ = [
    "ChannelMetricsAggregator",
    "FIT_WEIGHT_KEYS",
    "calculate_fit_score",
    "load_channel_fit_weights",
    "validate_channel_fit_weights",
]
