from app.services.consumer.cascade_metrics import compute_cascade_metrics
from app.services.consumer.social_topology import build_social_topology


def test_metrics_detect_cross_community_spread():
    topology = build_social_topology()
    events = [
        {
            "event_id": "e1",
            "event_type": "positive_relay",
            "actor_id": "M01",
            "target_ids": ["M02"],
            "actor_community": topology.persona_community.get("M01", ""),
            "actor_role": topology.persona_role.get("M01", ""),
            "cross_community": True,
            "round_index": 1,
        },
        {
            "event_id": "e2",
            "event_type": "positive_relay",
            "actor_id": "M01",
            "target_ids": ["M03"],
            "actor_community": topology.persona_community.get("M01", ""),
            "actor_role": topology.persona_role.get("M01", ""),
            "cross_community": False,
            "round_index": 1,
        },
    ]

    metrics = compute_cascade_metrics(events, topology=topology)
    assert metrics["cross_community_event_count"] == 1


def test_metrics_detect_narrative_takeover():
    topology = build_social_topology()
    events = [
        {
            "event_id": "e1",
            "event_type": "positive_relay",
            "actor_id": "M02",
            "target_ids": ["M04"],
            "round_index": 1,
        },
        {
            "event_id": "e2",
            "event_type": "positive_relay",
            "actor_id": "M04",
            "target_ids": ["M06"],
            "round_index": 1,
        },
        {
            "event_id": "e3",
            "event_type": "skeptical_challenge",
            "actor_id": "M05",
            "target_ids": ["M07"],
            "round_index": 1,
        },
    ]

    metrics = compute_cascade_metrics(events, topology=topology)
    assert metrics["dominant_event_type"] == "positive_relay"
    assert metrics["narrative_takeover_score"] == round(2 / 3, 4)


def test_metrics_count_blocked_and_reversal_events():
    topology = build_social_topology()
    events = [
        {
            "event_id": "e1",
            "event_type": "skeptical_challenge",
            "actor_id": "M05",
            "target_ids": ["M07"],
            "round_index": 1,
        },
        {
            "event_id": "e2",
            "event_type": "clarification_recovery",
            "actor_id": "M07",
            "target_ids": ["M05"],
            "round_index": 1,
        },
        {
            "event_id": "e3",
            "event_type": "misread_amplification",
            "actor_id": "M02",
            "target_ids": ["M04"],
            "round_index": 1,
        },
        {
            "event_id": "e4",
            "event_type": "risk_discovery",
            "actor_id": "M01",
            "target_ids": ["M03"],
            "round_index": 1,
        },
    ]

    metrics = compute_cascade_metrics(events, topology=topology)
    assert metrics["blocked_event_count"] == 2  # skeptical_challenge + clarification_recovery
    assert metrics["reversal_event_count"] == 3  # misread_amplification + clarification_recovery + risk_discovery


def test_metrics_with_empty_events():
    metrics = compute_cascade_metrics([], topology=build_social_topology())
    assert metrics["community_count"] >= 2
    assert metrics["active_community_count"] == 0
    assert metrics["community_coverage"] == 0.0
    assert metrics["cross_community_event_count"] == 0
    assert metrics["bridge_event_count"] == 0
    assert metrics["dominant_event_type"] == ""
    assert metrics["narrative_takeover_score"] == 0.0
    assert metrics["blocked_event_count"] == 0
    assert metrics["reversal_event_count"] == 0
    assert metrics["avg_reach"] == 0.0


def test_metrics_include_community_counts():
    topology = build_social_topology()
    events = [
        {
            "event_id": "e1",
            "event_type": "positive_relay",
            "actor_id": "M01",
            "target_ids": ["M03"],
            "actor_community": topology.persona_community.get("M01", ""),
            "round_index": 1,
        },
        {
            "event_id": "e2",
            "event_type": "positive_relay",
            "actor_id": "M05",
            "target_ids": ["M07"],
            "actor_community": topology.persona_community.get("M05", ""),
            "round_index": 1,
        },
    ]

    metrics = compute_cascade_metrics(events, topology=topology)
    assert metrics["active_community_count"] >= 2
    assert metrics["community_coverage"] > 0.0


def test_metrics_derive_role_from_topology_when_missing():
    topology = build_social_topology()
    bridge_id = next(iter(topology.bridges))
    events = [
        {
            "event_id": "e1",
            "event_type": "positive_relay",
            "actor_id": bridge_id,
            "target_ids": ["M02"],
            "actor_role": "",
            "round_index": 1,
        },
    ]

    metrics = compute_cascade_metrics(events, topology=topology)
    assert metrics["bridge_event_count"] == 1


def test_metrics_avg_reach_computed_correctly():
    topology = build_social_topology()
    events = [
        {
            "event_id": "e1",
            "event_type": "positive_relay",
            "actor_id": "M02",
            "target_ids": ["M04", "M06"],
            "round_index": 1,
        },
        {
            "event_id": "e2",
            "event_type": "positive_relay",
            "actor_id": "M04",
            "target_ids": ["M06"],
            "round_index": 1,
        },
    ]

    metrics = compute_cascade_metrics(events, topology=topology)
    assert metrics["avg_reach"] == 1.5
