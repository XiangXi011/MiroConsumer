"""Tests for Lane B governance: quality checks, duplicate suppression, downgrade rules, and trace recording."""

from app.services.consumer.document_ingest import DocumentIngestService
from app.services.consumer.finding_distiller import distill_findings_from_chunks
from app.services.consumer.lane_b_provider import (
    GovernedDocumentChunk,
    LaneBGovernance,
    OpenAIWebSearchProvider,
    WebSearchResultItem,
)
from app.services.consumer.models import DocumentChunk, ResearchSourceLane
from app.services.consumer.retrieval import RetrievalService
from app.services.consumer.source_registry import SourceRegistry


# ---------------------------------------------------------------------------
# LaneBGovernance unit tests
# ---------------------------------------------------------------------------

def test_governance_rejects_short_snippets():
    gov = LaneBGovernance()
    chunks = [
        DocumentChunk(chunk_id="c1", doc_id="d1", source_id="s1", text="Too short.", index=0),
        DocumentChunk(chunk_id="c2", doc_id="d1", source_id="s1", text="This is a substantially longer snippet that should pass the minimum length check.", index=1),
    ]
    accepted, decisions = gov.evaluate(chunks)
    assert len(accepted) == 1
    assert accepted[0].chunk_id == "c2"

    rejected = [d for d in decisions if d.status == "rejected"]
    assert len(rejected) == 1
    assert rejected[0].chunk_id == "c1"
    assert any("minimum snippet length" in r.lower() for r in rejected[0].reasons)


def test_governance_rejects_empty_snippets():
    gov = LaneBGovernance()
    chunks = [
        DocumentChunk(chunk_id="c1", doc_id="d1", source_id="s1", text="   ", index=0),
        DocumentChunk(chunk_id="c2", doc_id="d1", source_id="s1", text="Valid snippet with enough content to pass.", index=1),
    ]
    accepted, decisions = gov.evaluate(chunks)
    assert len(accepted) == 1
    assert accepted[0].chunk_id == "c2"

    rejected = [d for d in decisions if d.status == "rejected"]
    assert len(rejected) == 1
    assert rejected[0].chunk_id == "c1"


def test_governance_suppresses_duplicates():
    gov = LaneBGovernance()
    chunks = [
        DocumentChunk(chunk_id="c1", doc_id="d1", source_id="s1", text="Duplicate content about product safety concerns.", index=0),
        DocumentChunk(chunk_id="c2", doc_id="d2", source_id="s2", text="Duplicate content about product safety concerns.", index=0),
        DocumentChunk(chunk_id="c3", doc_id="d1", source_id="s1", text="Unique content about market trends and growth.", index=1),
    ]
    accepted, decisions = gov.evaluate(chunks)
    assert len(accepted) == 2
    accepted_ids = {c.chunk_id for c in accepted}
    assert "c1" in accepted_ids
    assert "c3" in accepted_ids

    rejected = [d for d in decisions if d.status == "rejected"]
    assert len(rejected) == 1
    assert rejected[0].chunk_id == "c2"
    assert any("duplicate" in r.lower() for r in rejected[0].reasons)


def test_governance_downgrades_weak_provenance():
    gov = LaneBGovernance()
    chunks = [
        DocumentChunk(chunk_id="c1", doc_id="d1", source_id="s1", text="This snippet comes from a reputable source with strong provenance and detail.", index=0),
    ]
    accepted, decisions = gov.evaluate(chunks)
    assert len(accepted) == 1
    # Weak provenance is determined heuristically; for a long detailed snippet it should NOT be downgraded
    assert not decisions[0].downgraded


def test_governance_downgrades_short_provenance():
    gov = LaneBGovernance()
    # A borderline-length snippet with vague content should be downgraded
    chunks = [
        DocumentChunk(chunk_id="c1", doc_id="d1", source_id="s1", text="Some product info here.", index=0),
    ]
    accepted, decisions = gov.evaluate(chunks)
    assert len(accepted) == 1
    # Short and vague = weak provenance
    assert decisions[0].downgraded


def test_governance_preserves_order_of_first_occurrence():
    gov = LaneBGovernance()
    chunks = [
        DocumentChunk(chunk_id="c_first", doc_id="d1", source_id="s1", text="First occurrence of shared text.", index=0),
        DocumentChunk(chunk_id="c_second", doc_id="d2", source_id="s2", text="First occurrence of shared text.", index=0),
    ]
    accepted, decisions = gov.evaluate(chunks)
    accepted_ids = [c.chunk_id for c in accepted]
    assert accepted_ids == ["c_first"]
    rejected = [d for d in decisions if d.status == "rejected"]
    assert rejected[0].chunk_id == "c_second"


# ---------------------------------------------------------------------------
# Provider governance integration tests
# ---------------------------------------------------------------------------

def test_provider_returns_only_accepted_chunks(tmp_path):
    root = str(tmp_path / "uploads")
    provider = OpenAIWebSearchProvider("proj_gov", upload_root=root)

    provider._search = lambda query, top_k: [
        WebSearchResultItem(url="https://a.com", title="A", snippet="Short."),
        WebSearchResultItem(url="https://b.com", title="B", snippet="This is a valid and sufficiently long snippet that should be accepted by governance."),
    ]

    chunks = provider("query", top_k=3)
    assert len(chunks) == 1
    assert chunks[0].text == "This is a valid and sufficiently long snippet that should be accepted by governance."

    # Verify governance decisions are accessible
    decisions = provider.last_governance()
    assert len(decisions) == 2
    rejected = [d for d in decisions if d.status == "rejected"]
    accepted = [d for d in decisions if d.status == "accepted"]
    assert len(rejected) == 1
    assert len(accepted) == 1


def test_provider_applies_duplicate_suppression(tmp_path):
    root = str(tmp_path / "uploads")
    provider = OpenAIWebSearchProvider("proj_dup", upload_root=root)

    provider._search = lambda query, top_k: [
        WebSearchResultItem(url="https://a.com", title="A", snippet="This is a long snippet about product safety concerns that should pass quality checks."),
        WebSearchResultItem(url="https://b.com", title="B", snippet="This is a long snippet about product safety concerns that should pass quality checks."),
    ]

    chunks = provider("query", top_k=3)
    assert len(chunks) == 1

    decisions = provider.last_governance()
    rejected = [d for d in decisions if d.status == "rejected"]
    assert len(rejected) == 1
    assert any("duplicate" in r.lower() for r in rejected[0].reasons)


def test_provider_downgrades_weak_sources(tmp_path):
    root = str(tmp_path / "uploads")
    provider = OpenAIWebSearchProvider("proj_down", upload_root=root)

    provider._search = lambda query, top_k: [
        WebSearchResultItem(url="https://vague.com", title="Vague", snippet="Some info here that is vague and lacks specific detail."),
    ]

    chunks = provider("query", top_k=3)
    assert len(chunks) == 1
    # The chunk should carry governance metadata indicating it was downgraded
    assert isinstance(chunks[0], GovernedDocumentChunk)
    assert chunks[0].downgraded is True


def test_provider_skips_url_only_results_without_snippet(tmp_path):
    root = str(tmp_path / "uploads")
    provider = OpenAIWebSearchProvider("proj_nosnip", upload_root=root)

    provider._search = lambda query, top_k: [
        WebSearchResultItem(url="https://empty.com", title="Empty", snippet=""),
    ]

    chunks = provider("query", top_k=3)
    assert len(chunks) == 0

    decisions = provider.last_governance()
    # Empty snippets are filtered before governance, but if a title fallback
    # were used the governance result may still be recorded. With the current
    # implementation empty snippets produce no decisions.
    assert len(decisions) == 0


# ---------------------------------------------------------------------------
# Retrieval trace governance recording tests
# ---------------------------------------------------------------------------

def test_retrieval_records_governance_in_traces(tmp_path):
    root = str(tmp_path / "uploads")
    provider = OpenAIWebSearchProvider("proj_trace", upload_root=root)

    provider._search = lambda query, top_k: [
        WebSearchResultItem(url="https://a.com", title="A", snippet="This is a valid long snippet from source A."),
        WebSearchResultItem(url="https://b.com", title="B", snippet="Short."),
    ]

    retrieval = RetrievalService("proj_trace", upload_root=root)
    result = retrieval.retrieve_dual("test query", top_k_a=0, top_k_b=5, provider=provider)

    # Governance traces should be persisted
    gov_traces = retrieval.load_governance_traces()
    assert len(gov_traces) >= 1

    lane_b_gov = [g for g in gov_traces if g.get("lane") == "lane_b"]
    assert len(lane_b_gov) >= 1
    assert len(lane_b_gov[0].get("accepted_ids", [])) == 1
    assert len(lane_b_gov[0].get("rejected_ids", [])) == 1


def test_retrieval_governance_traces_include_reasons(tmp_path):
    root = str(tmp_path / "uploads")
    provider = OpenAIWebSearchProvider("proj_reasons", upload_root=root)

    provider._search = lambda query, top_k: [
        WebSearchResultItem(url="https://a.com", title="A", snippet="This is a valid long snippet from source A."),
        WebSearchResultItem(url="https://b.com", title="B", snippet="Short."),
    ]

    retrieval = RetrievalService("proj_reasons", upload_root=root)
    retrieval.retrieve_dual("test query", top_k_a=0, top_k_b=5, provider=provider)

    gov_traces = retrieval.load_governance_traces()
    lane_b_gov = [g for g in gov_traces if g.get("lane") == "lane_b"]
    assert len(lane_b_gov) >= 1
    reasons = lane_b_gov[0].get("reasons", {})
    rejected_reasons = reasons.get("rejected", [])
    assert len(rejected_reasons) >= 1


# ---------------------------------------------------------------------------
# Finding distiller acceptance tests
# ---------------------------------------------------------------------------

def test_distiller_skips_rejected_chunks():
    chunks = [
        GovernedDocumentChunk(
            chunk_id="c_accepted",
            doc_id="d1",
            source_id="s1",
            text="This is a valid finding about competitor launch.",
            index=0,
            governance_status="accepted",
        ),
        GovernedDocumentChunk(
            chunk_id="c_rejected",
            doc_id="d1",
            source_id="s1",
            text="This is another finding about market trends.",
            index=1,
            governance_status="rejected",
            governance_reasons=["duplicate"],
        ),
    ]

    findings = distill_findings_from_chunks(chunks, lane=ResearchSourceLane.LaneB)
    assert len(findings) == 1
    assert findings[0].snippet_id == "c_accepted"


def test_distiller_preserves_governance_on_findings():
    chunks = [
        GovernedDocumentChunk(
            chunk_id="c_downgraded",
            doc_id="d1",
            source_id="s1",
            text="This finding has weak provenance but is still accepted.",
            index=0,
            governance_status="accepted",
            governance_reasons=["weak provenance"],
            downgraded=True,
        ),
    ]

    findings = distill_findings_from_chunks(chunks, lane=ResearchSourceLane.LaneB)
    assert len(findings) == 1
    # Governance metadata should be reflected in finding fields
    finding = findings[0]
    assert finding.source_label == "public_web"
    # Confidence should be lower for downgraded chunks
    assert finding.confidence < 0.6


def test_distiller_handles_plain_chunks_without_governance():
    """Non-governed chunks (e.g., Lane A) should still be distilled normally."""
    chunks = [
        DocumentChunk(chunk_id="c1", doc_id="d1", source_id="s1", text="Normal Lane A content.", index=0),
    ]

    findings = distill_findings_from_chunks(chunks, lane=ResearchSourceLane.LaneA)
    assert len(findings) == 1
    assert findings[0].confidence == 0.6  # Default confidence


def test_distiller_ignores_rejected_even_when_text_unique():
    chunks = [
        DocumentChunk(chunk_id="c1", doc_id="d1", source_id="s1", text="Unique text one.", index=0),
        GovernedDocumentChunk(
            chunk_id="c2",
            doc_id="d1",
            source_id="s1",
            text="Unique text two.",
            index=1,
            governance_status="rejected",
            governance_reasons=["minimum snippet length"],
        ),
    ]

    findings = distill_findings_from_chunks(chunks, lane=ResearchSourceLane.LaneB)
    assert len(findings) == 1
    assert findings[0].snippet_id == "c1"
