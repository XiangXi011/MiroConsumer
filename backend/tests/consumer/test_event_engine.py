from app.services.consumer.event_engine import (
    build_propagation_event,
    classify_propagation_event,
    derive_speech_act_from_bucket,
    derive_trigger_from_findings,
)
from app.services.consumer.models import PropagationEvent


def test_event_engine_labels_misread_events():
    event_type = classify_propagation_event(
        before_attitude="positive",
        after_attitude="negative",
        trigger="risk_signal",
        speech_act="reinterpretation",
    )
    assert event_type == "misread_amplification"


def test_event_engine_records_event_chain_metadata():
    event = build_propagation_event(
        actor_id="agent_1",
        target_ids=["agent_2"],
        event_type="skeptical_challenge",
        trigger_finding_ids=["r1"],
        supporting_quote="This sounds too good to be true",
        round_index=2,
    )
    assert event.trigger_finding_ids == ["r1"]
    assert event.round_index == 2
    assert event.actor_id == "agent_1"
    assert event.event_type == "skeptical_challenge"


def test_classify_risk_discovery():
    event_type = classify_propagation_event(
        before_attitude="positive",
        after_attitude="negative",
        trigger="risk_signal",
        speech_act="challenge",
    )
    assert event_type == "risk_discovery"


def test_classify_clarification_recovery():
    event_type = classify_propagation_event(
        before_attitude="negative",
        after_attitude="positive",
        trigger="category_context",
        speech_act="endorsement",
    )
    assert event_type == "clarification_recovery"


def test_classify_unknown_transition_defaults_to_challenge_not_positive_relay():
    event_type = classify_propagation_event(
        before_attitude="neutral",
        after_attitude="neutral",
        trigger="category_context",
        speech_act="statement",
    )
    assert event_type == "skeptical_challenge"


def test_derive_trigger_from_findings_prefers_risk():
    findings = [
        {"finding_type": "category_context", "finding_id": "c1"},
        {"finding_type": "risk_signal", "finding_id": "r1"},
    ]
    assert derive_trigger_from_findings(findings) == "risk_signal"


def test_derive_speech_act_mapping():
    assert derive_speech_act_from_bucket("resonance") == "endorsement"
    assert derive_speech_act_from_bucket("risk") == "challenge"
    assert derive_speech_act_from_bucket("question") == "inquiry"
    assert derive_speech_act_from_bucket("misread") == "reinterpretation"
