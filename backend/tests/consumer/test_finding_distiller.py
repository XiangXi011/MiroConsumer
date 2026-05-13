from app.services.consumer.finding_distiller import (
    build_retrieval_trace,
    distill_findings_from_chunks,
)
from app.services.consumer.models import DocumentChunk, GraphVisibility, ResearchSourceLane


def test_distill_findings_from_chunks_classifies_risk():
    chunks = [
        DocumentChunk(
            chunk_id="chk_1",
            doc_id="doc_1",
            source_id="src_1",
            text="There is a safety concern about the ingredient.",
            index=0,
            char_start=0,
            char_end=47,
        )
    ]

    findings = distill_findings_from_chunks(chunks)

    assert len(findings) == 1
    assert findings[0].finding_type == "risk_signal"
    assert findings[0].source_id == "src_1"
    assert findings[0].snippet_id == "chk_1"
    assert findings[0].source_label == "ingested_document"


def test_distill_findings_from_chunks_classifies_trend():
    chunks = [
        DocumentChunk(
            chunk_id="chk_2",
            doc_id="doc_1",
            source_id="src_1",
            text="Viral trend: group chat discussions are rising fast.",
            index=1,
            char_start=48,
            char_end=100,
        )
    ]

    findings = distill_findings_from_chunks(chunks)

    assert len(findings) == 1
    assert findings[0].finding_type == "trend_signal"


def test_distill_findings_from_chunks_deduplicates_by_text():
    chunks = [
        DocumentChunk(
            chunk_id="chk_3",
            doc_id="doc_1",
            source_id="src_1",
            text="Duplicate text about safety.",
            index=0,
        ),
        DocumentChunk(
            chunk_id="chk_4",
            doc_id="doc_1",
            source_id="src_1",
            text="Duplicate text about safety.",
            index=1,
        ),
    ]

    findings = distill_findings_from_chunks(chunks)
    assert len(findings) == 1


def test_distill_findings_from_chunks_sets_lane_b_source_label():
    chunks = [
        DocumentChunk(
            chunk_id="chk_5",
            doc_id="doc_1",
            source_id="src_web",
            text="Competitor launched a rival product this week.",
            index=0,
        )
    ]

    findings = distill_findings_from_chunks(chunks, lane=ResearchSourceLane.LaneB)

    assert findings[0].source_label == "public_web"


def test_distill_findings_skips_empty_chunks():
    chunks = [
        DocumentChunk(
            chunk_id="chk_empty",
            doc_id="doc_1",
            source_id="src_1",
            text="   ",
            index=0,
        ),
        DocumentChunk(
            chunk_id="chk_real",
            doc_id="doc_1",
            source_id="src_1",
            text="Real content here.",
            index=1,
        ),
    ]

    findings = distill_findings_from_chunks(chunks)
    assert len(findings) == 1
    assert findings[0].snippet_id == "chk_real"


def test_distill_findings_sets_visibility():
    chunks = [
        DocumentChunk(
            chunk_id="chk_risk",
            doc_id="doc_1",
            source_id="src_1",
            text="There is a lawsuit risk if this claim is overstated.",
            index=0,
        ),
        DocumentChunk(
            chunk_id="chk_norm",
            doc_id="doc_1",
            source_id="src_1",
            text="General category information about the product.",
            index=1,
        ),
    ]

    findings = distill_findings_from_chunks(chunks)
    assert len(findings) == 2

    risk_finding = next(f for f in findings if f.snippet_id == "chk_risk")
    normal_finding = next(f for f in findings if f.snippet_id == "chk_norm")

    assert risk_finding.visibility == GraphVisibility.Restricted
    assert normal_finding.visibility == GraphVisibility.GraphVisible


def test_build_retrieval_trace():
    trace = build_retrieval_trace(
        query="safety concerns",
        lane=ResearchSourceLane.LaneA,
        chunk_ids=["chk_1", "chk_2"],
        scores=[0.9, 0.8],
        trace_id="trace_abc",
    )

    assert trace.trace_id == "trace_abc"
    assert trace.query == "safety concerns"
    assert trace.lane == ResearchSourceLane.LaneA
    assert trace.chunk_ids == ["chk_1", "chk_2"]
    assert trace.scores == [0.9, 0.8]
    assert trace.retrieved_at != ""


def test_distill_findings_truncates_long_summaries():
    long_text = "A" * 500
    chunks = [
        DocumentChunk(
            chunk_id="chk_long",
            doc_id="doc_1",
            source_id="src_1",
            text=long_text,
            index=0,
        )
    ]

    findings = distill_findings_from_chunks(chunks)
    assert len(findings[0].summary) <= 200
