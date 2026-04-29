import json

import pytest

from app.services.consumer.event_ontology import ConsumerEventType
from app.services.consumer.society.channel_metrics import (
    ChannelMetricsAggregator,
    calculate_fit_score,
    load_channel_fit_weights,
    validate_channel_fit_weights,
)


def _event(channel_id, event_type, strength=0.8, round_index=0):
    return {
        "event_id": f"{channel_id}:{event_type}:{round_index}",
        "consumer_event_type": event_type,
        "channel_id": channel_id,
        "round_index": round_index,
        "actor_id": "agent-1",
        "target_ids": [],
        "claim_id": "claim-1",
        "finding_ids": [],
        "quote": "quote",
        "strength": strength,
        "cross_channel": False,
        "source_channel_id": "",
        "target_channel_id": "",
    }


def test_channel_fit_weights_are_loaded_from_config_and_validated(tmp_path):
    weights = load_channel_fit_weights()
    assert weights == {
        "resonance": 0.30,
        "purchase_intent_delta": 0.25,
        "trust_repair_factor": 0.15,
        "misread_risk": -0.15,
        "price_resistance": -0.10,
        "evidence_demand": -0.05,
    }

    invalid_path = tmp_path / "bad_weights.json"
    invalid_path.write_text(json.dumps({"resonance": 1.0}), encoding="utf-8")
    with pytest.raises(ValueError):
        load_channel_fit_weights(invalid_path)

    with pytest.raises(ValueError, match="positive weight sum"):
        validate_channel_fit_weights({**weights, "resonance": 0.20})


def test_fit_score_uses_configured_weights_and_clamps():
    weights = load_channel_fit_weights()
    assert calculate_fit_score(
        {
            "resonance": 1.0,
            "purchase_intent_delta": 1.0,
            "trust_repair_factor": 1.0,
            "misread_risk": 0.0,
            "price_resistance": 0.0,
            "evidence_demand": 0.0,
        },
        weights,
    ) == 0.7
    assert calculate_fit_score(
        {
            "resonance": 0.0,
            "purchase_intent_delta": 0.0,
            "trust_repair_factor": 0.0,
            "misread_risk": 1.0,
            "price_resistance": 1.0,
            "evidence_demand": 1.0,
        },
        weights,
    ) == 0.0


def test_channel_metrics_aggregate_fixed_fields_and_channel_selectors():
    events = [
        _event("xiaohongshu", ConsumerEventType.AMPLIFY_CLAIM.value),
        _event("xiaohongshu", ConsumerEventType.PURCHASE_INTENT_UP.value),
        _event("xiaohongshu", ConsumerEventType.TRUST_RECOVERY.value),
        _event("douyin", ConsumerEventType.MISREAD_CLAIM.value),
        _event("douyin", ConsumerEventType.NEGATIVE_CASCADE.value),
        _event("ecommerce_review", ConsumerEventType.PRICE_RESISTANCE.value),
        _event("zhihu_qa", ConsumerEventType.ASK_PROOF.value),
    ]

    metrics = ChannelMetricsAggregator().aggregate(
        events,
        enabled_channels=["xiaohongshu", "douyin", "ecommerce_review", "zhihu_qa"],
    )

    assert set(metrics) == {
        "channels",
        "cross_channel_spread",
        "best_launch_channel",
        "highest_misread_channel",
        "highest_evidence_demand_channel",
        "highest_price_resistance_channel",
    }
    assert metrics["best_launch_channel"] == "xiaohongshu"
    assert metrics["highest_misread_channel"] == "douyin"
    assert metrics["highest_evidence_demand_channel"] == "zhihu_qa"
    assert metrics["highest_price_resistance_channel"] == "ecommerce_review"

    for channel_metrics in metrics["channels"].values():
        for key, value in channel_metrics.items():
            assert 0.0 <= value <= 1.0, key
