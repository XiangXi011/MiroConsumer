from app.services.consumer.models import ResearchFinding, RetrievalTrace
from app.services.consumer.report_context import (
    ConsumerReportContextBuilder,
    _build_provenance_summary,
    build_consumer_report_context,
)
from app.services.consumer.scoring import ConsumerScoringService


def test_build_consumer_report_context_without_traces():
    summary = ConsumerScoringService().summarize(
        initial_labels=["positive", "neutral"],
        final_labels=["positive", "negative"],
    )
    findings = [
        ResearchFinding(
            finding_id="f1",
            finding_type="risk_signal",
            summary="Safety concern",
            visibility="Propagation_Only",
            source_label="brief_background",
        )
    ]
    events = []

    context = build_consumer_report_context(summary, findings, events)
    assert "retrieval_provenance" not in context
    assert "retrieval_traces" not in context


def test_build_consumer_report_context_with_traces():
    summary = ConsumerScoringService().summarize(
        initial_labels=["positive", "neutral"],
        final_labels=["positive", "negative"],
    )
    findings = [
        ResearchFinding(
            finding_id="f1",
            finding_type="risk_signal",
            summary="Safety concern",
            visibility="Propagation_Only",
            source_label="public_web",
            snippet_id="chk_1",
            retrieval_trace_id="trace_abc",
        )
    ]
    traces = [
        RetrievalTrace(
            trace_id="trace_abc",
            query="safety concerns",
            lane="lane_b",
            chunk_ids=["chk_1"],
            scores=[0.9],
        )
    ]
    events = []

    context = build_consumer_report_context(summary, findings, events, traces=traces)
    assert "retrieval_provenance" in context
    assert "retrieval_traces" in context
    prov = context["retrieval_provenance"]
    assert prov["trace_count"] == 1
    assert prov["lane_counts"]["lane_b"] == 1
    assert prov["findings"][0]["retrieval_trace_id"] == "trace_abc"
    assert prov["findings"][0]["retrieval_query"] == "safety concerns"


def test_build_provenance_summary_counts_lanes():
    findings = [
        ResearchFinding(
            finding_id="f1",
            finding_type="category_context",
            summary="A",
            source_label="brief_background",
        ),
        ResearchFinding(
            finding_id="f2",
            finding_type="risk_signal",
            summary="B",
            source_label="ingested_document",
        ),
        ResearchFinding(
            finding_id="f3",
            finding_type="trend_signal",
            summary="C",
            source_label="public_web",
        ),
    ]
    traces = []
    prov = _build_provenance_summary(findings, traces)
    assert prov["lane_counts"]["lane_a"] == 2
    assert prov["lane_counts"]["lane_b"] == 1
    assert prov["lane_counts"]["unknown"] == 0


def test_consumer_report_context_builder_loads_events():
    builder = ConsumerReportContextBuilder()
    events = builder.load_events("nonexistent_path.jsonl")
    assert events == []
