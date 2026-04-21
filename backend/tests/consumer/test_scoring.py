from app.services.consumer.models import GraphVisibility, PropagationEvent, ResearchFinding
from app.services.consumer.report_context import ConsumerReportContextBuilder, build_consumer_report_context
from app.services.consumer.scoring import ConsumerScoringService, build_consumer_summary


def test_scoring_extracts_representative_quotes():
    events = [
        {
            "quote": "This actually sounds like a real breakfast fix",
            "engagement": 9,
            "bucket": "resonance",
        },
        {
            "quote": "Low sugar? I don't trust that claim",
            "engagement": 7,
            "bucket": "risk",
        },
    ]

    bundle = ConsumerScoringService().build_evidence_bundle(events)

    assert bundle.top_resonance_quotes[0]["quote"].startswith("This actually")
    assert bundle.top_risk_quotes[0]["quote"].startswith("Low sugar")


def test_summary_tracks_attitude_shift():
    summary = ConsumerScoringService().summarize(
        initial_labels=["positive", "neutral", "negative"],
        final_labels=["positive", "positive", "negative"],
    )

    assert summary.attitude_shift_rate > 0


def test_report_context_builder_surfaces_consumer_metrics_and_voc():
    events = [
        {
            "round_num": 0,
            "agent_id": "persona_a",
            "attitude_label": "positive",
            "bucket": "resonance",
            "engagement": 9,
            "quote": "This actually sounds like a real breakfast fix",
            "visible_nodes": [{"type": "ProductConcept", "text": "breakfast yogurt pouch"}],
        },
        {
            "round_num": 1,
            "agent_id": "persona_a",
            "attitude_label": "negative",
            "bucket": "risk",
            "engagement": 8,
            "quote": "Low sugar? I don't trust that claim",
            "visible_nodes": [{"type": "RiskPoint", "text": "sweetener debate"}],
        },
        {
            "round_num": 1,
            "agent_id": "persona_b",
            "attitude_label": "neutral",
            "bucket": "question",
            "engagement": 6,
            "quote": "I keep seeing this, but I still need more proof.",
            "visible_nodes": [{"type": "CopyPoint", "text": "low sugar"}],
        },
    ]

    context = ConsumerReportContextBuilder().build(events)

    assert context["summary"]["attitude_shift_rate"] > 0
    assert context["top_risk_points"][0] == "sweetener debate"
    assert context["representative_voc_quotes"]["risk"][0]["quote"].startswith("Low sugar")


def test_scoring_groups_events_into_causal_findings():
    summary = build_consumer_summary(
        events=[
            PropagationEvent(
                event_id="e1",
                event_type="risk_discovery",
                actor_id="agent_1",
                target_ids=["agent_2"],
                trigger_finding_ids=["r1"],
                supporting_quote="Wait, what sweetener is in this?",
                round_index=2,
            )
        ],
        findings=[
            ResearchFinding(
                finding_id="r1",
                finding_type="risk_signal",
                summary="Sweetener concern",
                visibility=GraphVisibility.Restricted,
            )
        ],
    )

    assert summary.top_risk_findings[0]["finding_id"] == "r1"
    assert summary.event_counts["risk_discovery"] == 1


def test_scoring_event_counts_multiple_types():
    summary = build_consumer_summary(
        events=[
            PropagationEvent(
                event_id="e1",
                event_type="risk_discovery",
                actor_id="agent_1",
                target_ids=[],
                trigger_finding_ids=["r1"],
                supporting_quote="Quote 1",
                round_index=1,
            ),
            PropagationEvent(
                event_id="e2",
                event_type="skeptical_challenge",
                actor_id="agent_2",
                target_ids=[],
                trigger_finding_ids=["r1"],
                supporting_quote="Quote 2",
                round_index=1,
            ),
        ],
        findings=[],
    )
    assert summary.event_counts["risk_discovery"] == 1
    assert summary.event_counts["skeptical_challenge"] == 1


def test_scoring_empty_events_returns_zero_counts():
    summary = build_consumer_summary(events=[], findings=[])
    assert summary.event_counts == {}
    assert summary.top_risk_findings == []


def test_report_context_keeps_trigger_finding_and_event_chain():
    summary = build_consumer_summary(
        events=[
            PropagationEvent(
                event_id="e1",
                event_type="risk_discovery",
                actor_id="agent_1",
                target_ids=["agent_2"],
                trigger_finding_ids=["r1"],
                supporting_quote="Wait, what sweetener is in this?",
                round_index=2,
            )
        ],
        findings=[
            ResearchFinding(
                finding_id="r1",
                finding_type="risk_signal",
                summary="Sweetener concern",
                visibility=GraphVisibility.Restricted,
            )
        ],
    )

    context = build_consumer_report_context(
        summary=summary,
        findings=[
            ResearchFinding(
                finding_id="r1",
                finding_type="risk_signal",
                summary="Sweetener concern",
                visibility=GraphVisibility.Restricted,
            )
        ],
        events=[
            PropagationEvent(
                event_id="e1",
                event_type="risk_discovery",
                actor_id="agent_1",
                target_ids=["agent_2"],
                trigger_finding_ids=["r1"],
                supporting_quote="Wait, what sweetener is in this?",
                round_index=2,
            )
        ],
    )

    assert context["causal_chains"][0]["trigger_finding_ids"] == ["r1"]
    assert context["causal_chains"][0]["event_ids"] == ["e1"]
