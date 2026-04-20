from app.services.consumer.report_context import ConsumerReportContextBuilder
from app.services.consumer.scoring import ConsumerScoringService


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
