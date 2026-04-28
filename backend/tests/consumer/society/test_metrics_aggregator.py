from app.services.consumer.event_ontology import ConsumerEventType
from app.services.consumer.society.metrics_aggregator import SocietyMetricsAggregator


def test_metrics_aggregator_outputs_fixed_fields_in_range():
    events = [
        {"agent_id": "a1", "segment": "seg1", "consumer_event_type": ConsumerEventType.AMPLIFY_CLAIM.value},
        {"agent_id": "a2", "segment": "seg2", "consumer_event_type": ConsumerEventType.ASK_PROOF.value},
        {"agent_id": "a3", "segment": "seg2", "consumer_event_type": ConsumerEventType.MISREAD_CLAIM.value},
        {"agent_id": "a4", "segment": "seg3", "consumer_event_type": ConsumerEventType.TRUST_RECOVERY.value},
        {"agent_id": "a5", "segment": "seg3", "consumer_event_type": ConsumerEventType.PURCHASE_INTENT_UP.value},
    ]

    metrics = SocietyMetricsAggregator().aggregate(events, population_size=10, segments_count=4)

    assert set(metrics) == {
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
    }
    for key, value in metrics.items():
        if key == "cascade_depth":
            assert isinstance(value, int)
        else:
            assert 0.0 <= value <= 1.0
    assert metrics["reach_rate"] == 0.5
    assert metrics["purchase_intent_delta"] > 0
