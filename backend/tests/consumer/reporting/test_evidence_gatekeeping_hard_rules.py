"""Evidence gatekeeping hard-rules deterministic coverage."""

from app.services.consumer.models import (
    DocumentChunk,
    GraphVisibility,
    ResearchFinding,
    ResearchSource,
    ResearchSourceLane,
    ResearchSourceType,
    RetrievalTrace,
)
from app.services.consumer.evidence_validator import (
    apply_evidence_gatekeeping_to_findings,
    build_gatekeeping_summary,
    validate_findings,
)


def test_hard_rule_blocks_insufficient_support_finding():
    """Findings with insufficient_support validation status must be blocked."""
    finding = ResearchFinding(
        finding_id="f-insufficient",
        finding_type="risk_signal",
        summary="Unproven claim",
    )
    validations = validate_findings([finding], traces=None, chunks=None)
    results = apply_evidence_gatekeeping_to_findings([finding], validations)

    assert len(results) == 1
    assert results[0].gatekeeping_status == "blocked"
    assert any("insufficient_support" in v for v in results[0].policy_violations)


def test_hard_rule_blocks_high_stakes_without_retrieval_trace():
    """High-stakes findings (risk_signal, competitor_signal) without trace must be blocked."""
    finding = ResearchFinding(
        finding_id="f-no-trace",
        finding_type="risk_signal",
        summary="Safety risk",
        evidence_snippets=["detail"],
        snippet_id="chk-1",
        source_id="src-a",
    )
    validations = validate_findings([finding], traces=None, chunks=None)
    results = apply_evidence_gatekeeping_to_findings([finding], validations)

    assert results[0].gatekeeping_status == "blocked"
    assert any("missing_retrieval_trace_for_high_stakes" in v for v in results[0].policy_violations)


def test_hard_rule_passes_supported_with_all_evidence():
    """Fully supported high-stakes finding with trace and good source must pass."""
    finding = ResearchFinding(
        finding_id="f-good",
        finding_type="risk_signal",
        summary="Verified risk",
        evidence_snippets=["detail one", "detail two"],
        snippet_id="chk-1",
        retrieval_trace_id="trace-1",
        source_id="src-a",
    )
    traces = [RetrievalTrace(trace_id="trace-1", query="risk", lane=ResearchSourceLane.LaneA, chunk_ids=["chk-1"])]
    chunks = [DocumentChunk(chunk_id="chk-1", doc_id="d1", source_id="src-a", text="detail one")]
    sources = [ResearchSource(source_id="src-a", lane=ResearchSourceLane.LaneA, source_type=ResearchSourceType.Upload, label="QA", trust_tier=1)]

    validations = validate_findings([finding], traces=traces, chunks=chunks)
    results = apply_evidence_gatekeeping_to_findings([finding], validations, sources=sources)

    assert results[0].gatekeeping_status == "allowed"
    assert results[0].policy_violations == []


def test_hard_rule_downgrades_weak_support():
    """Weak support findings without additional violations must be downgraded."""
    finding = ResearchFinding(
        finding_id="f-weak",
        finding_type="trend_signal",
        summary="Weak trend",
        evidence_snippets=["trend detail"],
        snippet_id="chk-2",
        source_id="src-b",
    )
    chunks = [DocumentChunk(chunk_id="chk-2", doc_id="d2", source_id="src-b", text="trend detail")]
    validations = validate_findings([finding], traces=None, chunks=chunks)
    results = apply_evidence_gatekeeping_to_findings([finding], validations)

    assert results[0].gatekeeping_status == "downgraded"


def test_hard_rule_downgrades_low_tier_source_for_high_stakes():
    """High-stakes finding with source tier exceeding maximum must be downgraded."""
    finding = ResearchFinding(
        finding_id="f-tier",
        finding_type="risk_signal",
        summary="Risky claim",
        evidence_snippets=["risk detail", "risk detail 2"],
        snippet_id="chk-3",
        retrieval_trace_id="trace-3",
        source_id="src-c",
    )
    traces = [RetrievalTrace(trace_id="trace-3", query="risk", lane=ResearchSourceLane.LaneA, chunk_ids=["chk-3"])]
    chunks = [DocumentChunk(chunk_id="chk-3", doc_id="d3", source_id="src-c", text="risk detail")]
    sources = [ResearchSource(source_id="src-c", lane=ResearchSourceLane.LaneA, source_type=ResearchSourceType.Upload, label="Old", trust_tier=4)]

    validations = validate_findings([finding], traces=traces, chunks=chunks)
    results = apply_evidence_gatekeeping_to_findings([finding], validations, sources=sources)

    assert results[0].gatekeeping_status == "downgraded"
    assert any("source_tier_too_low" in v for v in results[0].policy_violations)


def test_hard_rule_blocks_insufficient_evidence_for_risk_signal():
    """risk_signal with only 1 evidence snippet (needs 2) must be downgraded/blocked."""
    finding = ResearchFinding(
        finding_id="f-one-snippet",
        finding_type="risk_signal",
        summary="Risk with one snippet",
        evidence_snippets=["only one"],
        snippet_id="chk-4",
        retrieval_trace_id="trace-4",
        source_id="src-d",
    )
    traces = [RetrievalTrace(trace_id="trace-4", query="risk", lane=ResearchSourceLane.LaneA, chunk_ids=["chk-4"])]
    chunks = [DocumentChunk(chunk_id="chk-4", doc_id="d4", source_id="src-d", text="only one")]
    sources = [ResearchSource(source_id="src-d", lane=ResearchSourceLane.LaneA, source_type=ResearchSourceType.Upload, label="Doc", trust_tier=1)]

    validations = validate_findings([finding], traces=traces, chunks=chunks)
    results = apply_evidence_gatekeeping_to_findings([finding], validations, sources=sources)

    # supported but insufficient_evidence_snippets violation -> downgraded
    assert results[0].gatekeeping_status == "downgraded"
    assert any("insufficient_evidence_snippets" in v for v in results[0].policy_violations)


def test_gatekeeping_summary_counts_blocked_and_downgraded():
    """Summary must correctly count allowed, downgraded, and blocked."""
    findings = [
        ResearchFinding(finding_id="f-allowed", finding_type="category_context", summary="A category context", evidence_snippets=["A category context detail"], snippet_id="c1", retrieval_trace_id="t1", source_id="s1"),
        ResearchFinding(finding_id="f-blocked", finding_type="category_context", summary="B"),
        ResearchFinding(finding_id="f-downgraded", finding_type="trend_signal", summary="C trend signal", evidence_snippets=["C trend signal detail"], snippet_id="c2", source_id="s2"),
    ]
    traces = [RetrievalTrace(trace_id="t1", query="a", lane=ResearchSourceLane.LaneA, chunk_ids=["c1"])]
    chunks = [
        DocumentChunk(chunk_id="c1", doc_id="d1", source_id="s1", text="A category context detail"),
        DocumentChunk(chunk_id="c2", doc_id="d2", source_id="s2", text="C trend signal detail"),
    ]
    sources = [
        ResearchSource(source_id="s1", lane=ResearchSourceLane.LaneA, source_type=ResearchSourceType.Upload, label="A", trust_tier=1),
        ResearchSource(source_id="s2", lane=ResearchSourceLane.LaneB, source_type=ResearchSourceType.PublicWeb, label="B", trust_tier=2),
    ]

    validations = validate_findings(findings, traces=traces, chunks=chunks)
    results = apply_evidence_gatekeeping_to_findings(findings, validations, sources=sources)
    summary = build_gatekeeping_summary(results)

    assert summary["finding_count"] == 3
    assert summary["allowed_count"] == 1
    assert summary["blocked_count"] == 1
    assert summary["downgraded_count"] == 1


def test_default_hard_rules_keep_weak_support_out_of_strong_outputs():
    """Default hard rules keep weak_support as downgraded rather than allowed."""
    finding = ResearchFinding(
        finding_id="f-default-weak",
        finding_type="trend_signal",
        summary="Weak category trend",
        evidence_snippets=["one weak signal"],
        snippet_id="chk-default-weak",
        source_id="src-default-weak",
    )
    chunks = [
        DocumentChunk(
            chunk_id="chk-default-weak",
            doc_id="doc-default-weak",
            source_id="src-default-weak",
            text="one weak signal",
        )
    ]

    validations = validate_findings([finding], traces=None, chunks=chunks)
    results = apply_evidence_gatekeeping_to_findings([finding], validations)

    assert validations[0].validation_status == "weak_support"
    assert results[0].gatekeeping_status == "downgraded"


def test_branch_base_isolation_gatekeeping_results():
    """Base and branch findings must be gatekept independently."""
    base_finding = ResearchFinding(
        finding_id="f-base",
        finding_type="risk_signal",
        summary="Base risk",
        evidence_snippets=["base ev", "base ev 2"],
        snippet_id="chk-base",
        retrieval_trace_id="trace-base",
        source_id="src-base",
    )
    branch_finding = ResearchFinding(
        finding_id="f-branch",
        finding_type="risk_signal",
        summary="Branch risk",
        evidence_snippets=["branch ev"],
        snippet_id="chk-branch",
        source_id="src-branch",
    )

    base_traces = [RetrievalTrace(trace_id="trace-base", query="base", lane=ResearchSourceLane.LaneA, chunk_ids=["chk-base"])]
    base_chunks = [DocumentChunk(chunk_id="chk-base", doc_id="d-base", source_id="src-base", text="base ev")]
    base_sources = [ResearchSource(source_id="src-base", lane=ResearchSourceLane.LaneA, source_type=ResearchSourceType.Upload, label="Base", trust_tier=1)]

    base_validations = validate_findings([base_finding], traces=base_traces, chunks=base_chunks)
    base_results = apply_evidence_gatekeeping_to_findings([base_finding], base_validations, sources=base_sources)

    branch_validations = validate_findings([branch_finding], traces=None, chunks=None)
    branch_results = apply_evidence_gatekeeping_to_findings([branch_finding], branch_validations)

    assert base_results[0].gatekeeping_status == "allowed"
    assert branch_results[0].gatekeeping_status == "blocked"
