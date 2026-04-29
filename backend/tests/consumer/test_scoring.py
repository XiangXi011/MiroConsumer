from app.services.consumer.models import (
    DocumentChunk,
    GraphVisibility,
    PropagationEvent,
    ResearchFinding,
    ResearchSource,
    ResearchSourceLane,
    ResearchSourceType,
    RetrievalTrace,
)
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

    # Phase 5C: unsupported findings are blocked from executive summary
    assert summary.top_risk_findings == []
    assert summary.evidence_gatekeeping_summary is not None
    assert summary.evidence_gatekeeping_summary["blocked_count"] == 1
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


def test_scoring_blocks_unsupported_risk_findings():
    supported = ResearchFinding(
        finding_id="r1",
        finding_type="risk_signal",
        summary="Sugar concern",
        visibility=GraphVisibility.Restricted,
        evidence_snippets=["snippet a", "snippet b"],
        snippet_id="chk_1",
        retrieval_trace_id="trace_1",
        source_id="src_a",
    )
    unsupported = ResearchFinding(
        finding_id="r2",
        finding_type="risk_signal",
        summary="Allergen concern",
        visibility=GraphVisibility.Restricted,
    )
    summary = build_consumer_summary(
        events=[
            PropagationEvent(
                event_id="e1",
                event_type="risk_discovery",
                actor_id="agent_1",
                target_ids=["agent_2"],
                trigger_finding_ids=["r1", "r2"],
                supporting_quote="Wait, what sweetener is in this?",
                round_index=2,
            )
        ],
        findings=[supported, unsupported],
        traces=[
            RetrievalTrace(
                trace_id="trace_1",
                query="sugar",
                lane=ResearchSourceLane.LaneA,
                chunk_ids=["chk_1"],
                scores=[0.9],
            )
        ],
        chunks=[
            DocumentChunk(
                chunk_id="chk_1",
                doc_id="doc_1",
                source_id="src_a",
                text="snippet a",
            )
        ],
        sources=[
            ResearchSource(
                source_id="src_a",
                lane=ResearchSourceLane.LaneA,
                source_type=ResearchSourceType.Upload,
                label="Brief",
                trust_tier=1,
            )
        ],
    )

    # Only the supported finding survives gatekeeping
    assert len(summary.top_risk_findings) == 1
    assert summary.top_risk_findings[0]["finding_id"] == "r1"
    assert summary.evidence_gatekeeping_summary is not None
    assert summary.evidence_gatekeeping_summary["allowed_count"] == 1
    assert summary.evidence_gatekeeping_summary["blocked_count"] == 1


def test_hard_gatekeeping_routes_weak_and_insufficient_findings_out_of_top_findings():
    supported = ResearchFinding(
        finding_id="r-supported",
        finding_type="risk_signal",
        summary="Supported safety concern",
        visibility=GraphVisibility.Restricted,
        evidence_snippets=["supported snippet a", "supported snippet b"],
        snippet_id="chk_supported",
        retrieval_trace_id="trace_supported",
        source_id="src_a",
    )
    weak = ResearchFinding(
        finding_id="r-weak",
        finding_type="trend_signal",
        summary="Weak price concern",
        visibility=GraphVisibility.Restricted,
        evidence_snippets=["weak price concern"],
        snippet_id="chk_weak",
        source_id="src_b",
    )
    insufficient = ResearchFinding(
        finding_id="r-missing",
        finding_type="category_context",
        summary="Missing proof concern",
        visibility=GraphVisibility.Restricted,
    )
    events = [
        PropagationEvent(
            event_id="e-supported",
            event_type="risk_discovery",
            actor_id="agent_1",
            target_ids=[],
            trigger_finding_ids=["r-supported", "r-weak", "r-missing"],
            supporting_quote="I need proof before I trust this.",
            round_index=1,
        )
    ]

    summary = build_consumer_summary(
        events=events,
        findings=[supported, weak, insufficient],
        traces=[
            RetrievalTrace(
                trace_id="trace_supported",
                query="safety",
                lane=ResearchSourceLane.LaneA,
                chunk_ids=["chk_supported"],
                scores=[0.9],
            )
        ],
        chunks=[
            DocumentChunk(
                chunk_id="chk_supported",
                doc_id="doc_1",
                source_id="src_a",
                text="supported snippet a",
            ),
            DocumentChunk(
                chunk_id="chk_weak",
                doc_id="doc_2",
                source_id="src_b",
                text="weak price concern",
            ),
        ],
        sources=[
            ResearchSource(
                source_id="src_a",
                lane=ResearchSourceLane.LaneA,
                source_type=ResearchSourceType.Upload,
                label="Uploaded QA",
                trust_tier=1,
            ),
            ResearchSource(
                source_id="src_b",
                lane=ResearchSourceLane.LaneB,
                source_type=ResearchSourceType.PublicWeb,
                label="Public review",
                trust_tier=2,
            ),
        ],
    )

    assert [f["finding_id"] for f in summary.top_risk_findings] == ["r-supported"]
    assert [f["finding_id"] for f in summary.low_confidence_risk_findings] == ["r-weak"]
    assert [f["finding_id"] for f in summary.findings_requiring_more_evidence] == ["r-missing"]
    assert summary.to_dict()["low_confidence_risk_findings"][0]["support_level"] == "weak_support"
    assert summary.to_dict()["findings_requiring_more_evidence"][0]["support_level"] == "insufficient_support"


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
