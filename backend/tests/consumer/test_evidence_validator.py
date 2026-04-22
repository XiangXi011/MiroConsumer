from pathlib import Path
import sys


BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.consumer.models import (
    DocumentChunk,
    GraphVisibility,
    ResearchFinding,
    ResearchSource,
    RetrievalTrace,
)
from app.services.consumer.evidence_validator import (
    EvidenceValidationResult,
    EvidenceGatekeepingPolicy,
    apply_evidence_gatekeeping,
    apply_evidence_gatekeeping_to_findings,
    build_evidence_validation_summary,
    build_gatekeeping_summary,
    filter_allowed_findings,
    validate_finding,
    validate_findings,
)


def test_supported_finding_with_trace_and_chunk():
    finding = ResearchFinding(
        finding_id="f1",
        finding_type="risk_signal",
        summary="Safety concern",
        evidence_snippets=["Safety concern detail"],
        snippet_id="chk_1",
        retrieval_trace_id="trace_1",
        source_id="src_a",
    )
    traces = [
        RetrievalTrace(
            trace_id="trace_1",
            query="safety",
            lane="lane_a",
            chunk_ids=["chk_1"],
            scores=[0.9],
        )
    ]
    chunks = [
        DocumentChunk(
            chunk_id="chk_1",
            doc_id="doc_1",
            source_id="src_a",
            text="Safety concern detail",
        )
    ]
    result = validate_finding(finding, traces=traces, chunks=chunks)
    assert result.validation_status == "supported"
    assert result.evidence_sufficiency >= 0.6
    assert "chk_1" in result.aligned_snippet_ids


def test_weak_support_finding_with_snippets_but_no_trace():
    finding = ResearchFinding(
        finding_id="f2",
        finding_type="risk_signal",
        summary="Price concern",
        evidence_snippets=["Price concern detail"],
        snippet_id="chk_2",
        source_id="src_b",
    )
    chunks = [
        DocumentChunk(
            chunk_id="chk_2",
            doc_id="doc_2",
            source_id="src_b",
            text="Price concern detail",
        )
    ]
    result = validate_finding(finding, traces=None, chunks=chunks)
    assert result.validation_status == "weak_support"
    assert result.evidence_sufficiency >= 0.3
    assert result.evidence_sufficiency < 0.6
    assert "no_retrieval_trace" in result.missing_support_reasons


def test_insufficient_support_finding_with_nothing():
    finding = ResearchFinding(
        finding_id="f3",
        finding_type="category_context",
        summary="Category note",
        source_id="",
    )
    result = validate_finding(finding, traces=None, chunks=None)
    assert result.validation_status == "insufficient_support"
    assert result.evidence_sufficiency < 0.3
    assert "no_snippet_id" in result.missing_support_reasons
    assert "no_retrieval_trace" in result.missing_support_reasons


def test_validate_findings_list():
    findings = [
        ResearchFinding(
            finding_id="f1",
            finding_type="risk_signal",
            summary="A",
            evidence_snippets=["A detail"],
            snippet_id="chk_1",
            retrieval_trace_id="trace_1",
        ),
        ResearchFinding(
            finding_id="f2",
            finding_type="risk_signal",
            summary="B",
            evidence_snippets=["B detail"],
            snippet_id="chk_2",
        ),
        ResearchFinding(
            finding_id="f3",
            finding_type="category_context",
            summary="C",
        ),
    ]
    traces = [
        RetrievalTrace(
            trace_id="trace_1",
            query="a",
            lane="lane_a",
            chunk_ids=["chk_1"],
        )
    ]
    chunks = [
        DocumentChunk(chunk_id="chk_1", doc_id="d1", source_id="s1", text="A detail"),
        DocumentChunk(chunk_id="chk_2", doc_id="d2", source_id="s2", text="B detail"),
    ]
    results = validate_findings(findings, traces=traces, chunks=chunks)
    assert len(results) == 3
    assert results[0].validation_status == "supported"
    assert results[1].validation_status == "weak_support"
    assert results[2].validation_status == "insufficient_support"


def test_build_evidence_validation_summary():
    results = [
        EvidenceValidationResult(
            finding_id="f1",
            validation_status="supported",
            evidence_sufficiency=0.8,
            aligned_snippet_ids=["chk_1"],
            missing_support_reasons=[],
            validator_notes="ok",
        ),
        EvidenceValidationResult(
            finding_id="f2",
            validation_status="weak_support",
            evidence_sufficiency=0.4,
            aligned_snippet_ids=[],
            missing_support_reasons=["no_retrieval_trace"],
            validator_notes="weak",
        ),
        EvidenceValidationResult(
            finding_id="f3",
            validation_status="insufficient_support",
            evidence_sufficiency=0.1,
            aligned_snippet_ids=[],
            missing_support_reasons=["no_snippet_id", "no_retrieval_trace"],
            validator_notes="insufficient",
        ),
    ]
    summary = build_evidence_validation_summary(results)
    assert summary["finding_count"] == 3
    assert summary["supported_count"] == 1
    assert summary["weak_support_count"] == 1
    assert summary["insufficient_support_count"] == 1
    assert summary["average_evidence_sufficiency"] > 0


def test_validation_summary_empty():
    summary = build_evidence_validation_summary([])
    assert summary["finding_count"] == 0
    assert summary["average_evidence_sufficiency"] == 0.0


def test_finding_with_missing_snippet_reference():
    finding = ResearchFinding(
        finding_id="f4",
        finding_type="risk_signal",
        summary="Missing ref",
        evidence_snippets=["Some text"],
        snippet_id="chk_missing",
        retrieval_trace_id="trace_missing",
    )
    result = validate_finding(finding, traces=[], chunks=[])
    assert result.validation_status == "insufficient_support"
    assert "referenced_snippet_not_found_in_chunks" in result.missing_support_reasons
    assert "referenced_trace_not_found" in result.missing_support_reasons


# Phase 5C: Evidence gatekeeping tests

def test_gatekeeping_allows_strong_supported_finding():
    finding = ResearchFinding(
        finding_id="f1",
        finding_type="risk_signal",
        summary="Safety concern",
        evidence_snippets=["Safety concern detail", "Another detail"],
        snippet_id="chk_1",
        retrieval_trace_id="trace_1",
        source_id="src_a",
    )
    validation = EvidenceValidationResult(
        finding_id="f1",
        validation_status="supported",
        evidence_sufficiency=0.8,
        aligned_snippet_ids=["chk_1"],
        missing_support_reasons=[],
        validator_notes="ok",
    )
    source = ResearchSource(
        source_id="src_a",
        lane="lane_a",
        source_type="upload",
        label="Brief",
        trust_tier=1,
    )
    result = apply_evidence_gatekeeping(finding, validation, source=source)
    assert result.gatekeeping_status == "allowed"
    assert result.policy_violations == []


def test_gatekeeping_blocks_insufficient_support_finding():
    finding = ResearchFinding(
        finding_id="f2",
        finding_type="risk_signal",
        summary="Price concern",
        evidence_snippets=["Price concern detail"],
        snippet_id="chk_2",
        source_id="src_b",
    )
    validation = EvidenceValidationResult(
        finding_id="f2",
        validation_status="insufficient_support",
        evidence_sufficiency=0.1,
        aligned_snippet_ids=[],
        missing_support_reasons=["no_retrieval_trace"],
        validator_notes="insufficient",
    )
    source = ResearchSource(
        source_id="src_b",
        lane="lane_b",
        source_type="public_web",
        label="Web",
        trust_tier=1,
    )
    result = apply_evidence_gatekeeping(finding, validation, source=source)
    assert result.gatekeeping_status == "blocked"
    assert any("validation_status:insufficient_support" in v for v in result.policy_violations)


def test_gatekeeping_blocks_high_stakes_without_trace():
    finding = ResearchFinding(
        finding_id="f3",
        finding_type="risk_signal",
        summary="Safety issue",
        evidence_snippets=["Detail"],
        snippet_id="chk_3",
        source_id="src_c",
    )
    validation = EvidenceValidationResult(
        finding_id="f3",
        validation_status="supported",
        evidence_sufficiency=0.7,
        aligned_snippet_ids=["chk_3"],
        missing_support_reasons=[],
        validator_notes="ok",
    )
    source = ResearchSource(
        source_id="src_c",
        lane="lane_a",
        source_type="upload",
        label="Doc",
        trust_tier=1,
    )
    result = apply_evidence_gatekeeping(finding, validation, source=source)
    assert result.gatekeeping_status == "blocked"
    assert any("missing_retrieval_trace_for_high_stakes" in v for v in result.policy_violations)


def test_gatekeeping_downgrades_weak_support():
    finding = ResearchFinding(
        finding_id="f4",
        finding_type="trend_signal",
        summary="Trend note",
        evidence_snippets=["Trend detail"],
        snippet_id="chk_4",
        retrieval_trace_id="trace_4",
        source_id="src_d",
    )
    validation = EvidenceValidationResult(
        finding_id="f4",
        validation_status="weak_support",
        evidence_sufficiency=0.4,
        aligned_snippet_ids=["chk_4"],
        missing_support_reasons=["some_reason"],
        validator_notes="weak",
    )
    source = ResearchSource(
        source_id="src_d",
        lane="lane_b",
        source_type="public_web",
        label="Article",
        trust_tier=1,
    )
    result = apply_evidence_gatekeeping(finding, validation, source=source)
    # weak_support without additional violations -> downgraded per policy
    assert result.gatekeeping_status == "downgraded"


def test_gatekeeping_blocks_low_tier_source_for_high_stakes():
    finding = ResearchFinding(
        finding_id="f5",
        finding_type="risk_signal",
        summary="Risky claim",
        evidence_snippets=["Risk detail"],
        snippet_id="chk_5",
        retrieval_trace_id="trace_5",
        source_id="src_e",
    )
    validation = EvidenceValidationResult(
        finding_id="f5",
        validation_status="supported",
        evidence_sufficiency=0.8,
        aligned_snippet_ids=["chk_5"],
        missing_support_reasons=[],
        validator_notes="ok",
    )
    # trust_tier=4 exceeds max tier of 2 for risk_signal
    source = ResearchSource(
        source_id="src_e",
        lane="lane_a",
        source_type="upload",
        label="Old doc",
        trust_tier=4,
    )
    result = apply_evidence_gatekeeping(finding, validation, source=source)
    assert result.gatekeeping_status == "downgraded"
    assert any("source_tier_too_low" in v for v in result.policy_violations)


def test_gatekeeping_to_findings_batch():
    findings = [
        ResearchFinding(
            finding_id="f1",
            finding_type="risk_signal",
            summary="A",
            evidence_snippets=["A detail", "Another detail"],
            snippet_id="chk_1",
            retrieval_trace_id="trace_1",
            source_id="src_a",
        ),
        ResearchFinding(
            finding_id="f2",
            finding_type="category_context",
            summary="B",
        ),
    ]
    validations = [
        EvidenceValidationResult(
            finding_id="f1",
            validation_status="supported",
            evidence_sufficiency=0.8,
            aligned_snippet_ids=["chk_1"],
            missing_support_reasons=[],
            validator_notes="ok",
        ),
        EvidenceValidationResult(
            finding_id="f2",
            validation_status="insufficient_support",
            evidence_sufficiency=0.1,
            aligned_snippet_ids=[],
            missing_support_reasons=["no_snippet_id"],
            validator_notes="insufficient",
        ),
    ]
    sources = [
        ResearchSource(
            source_id="src_a",
            lane="lane_a",
            source_type="upload",
            label="Brief",
            trust_tier=1,
        ),
    ]
    results = apply_evidence_gatekeeping_to_findings(findings, validations, sources=sources)
    assert len(results) == 2
    assert results[0].gatekeeping_status == "allowed"
    assert results[1].gatekeeping_status == "blocked"


def test_build_gatekeeping_summary():
    results = [
        apply_evidence_gatekeeping(
            ResearchFinding(finding_id="f1", finding_type="category_context", summary="A", evidence_snippets=["x"], snippet_id="c1", retrieval_trace_id="t1"),
            EvidenceValidationResult(finding_id="f1", validation_status="supported", evidence_sufficiency=0.8, aligned_snippet_ids=["c1"], missing_support_reasons=[], validator_notes="ok"),
        ),
        apply_evidence_gatekeeping(
            ResearchFinding(finding_id="f2", finding_type="category_context", summary="B"),
            EvidenceValidationResult(finding_id="f2", validation_status="insufficient_support", evidence_sufficiency=0.1, aligned_snippet_ids=[], missing_support_reasons=["no_snippet_id"], validator_notes="insufficient"),
        ),
    ]
    summary = build_gatekeeping_summary(results)
    assert summary["finding_count"] == 2
    assert summary["allowed_count"] == 1
    assert summary["blocked_count"] == 1
    assert summary["downgraded_count"] == 0


def test_filter_allowed_findings():
    findings = [
        ResearchFinding(finding_id="f1", finding_type="category_context", summary="A", evidence_snippets=["x"], snippet_id="c1", retrieval_trace_id="t1"),
        ResearchFinding(finding_id="f2", finding_type="category_context", summary="B"),
        ResearchFinding(finding_id="f3", finding_type="trend_signal", summary="C", evidence_snippets=["y"], snippet_id="c2"),
    ]
    gatekeeping_results = [
        apply_evidence_gatekeeping(
            findings[0],
            EvidenceValidationResult(finding_id="f1", validation_status="supported", evidence_sufficiency=0.8, aligned_snippet_ids=["c1"], missing_support_reasons=[], validator_notes="ok"),
        ),
        apply_evidence_gatekeeping(
            findings[1],
            EvidenceValidationResult(finding_id="f2", validation_status="insufficient_support", evidence_sufficiency=0.1, aligned_snippet_ids=[], missing_support_reasons=["no_snippet_id"], validator_notes="insufficient"),
        ),
        apply_evidence_gatekeeping(
            findings[2],
            EvidenceValidationResult(finding_id="f3", validation_status="weak_support", evidence_sufficiency=0.4, aligned_snippet_ids=["c2"], missing_support_reasons=["no_retrieval_trace"], validator_notes="weak"),
        ),
    ]
    allowed = filter_allowed_findings(findings, gatekeeping_results)
    # f1 is allowed; f2 is blocked; f3 is downgraded (weak_support without violations)
    assert len(allowed) == 1
    assert allowed[0].finding_id == "f1"

    allowed_with_downgraded = filter_allowed_findings(findings, gatekeeping_results, include_downgraded=True)
    assert len(allowed_with_downgraded) == 2
    assert {f.finding_id for f in allowed_with_downgraded} == {"f1", "f3"}


def test_gatekeeping_custom_policy_allows_lenient():
    policy = EvidenceGatekeepingPolicy(
        min_evidence_snippets=0,
        min_aligned_snippets=0,
        require_retrieval_trace=False,
        blocked_statuses={"insufficient_support"},
        downgraded_statuses=set(),
    )
    finding = ResearchFinding(
        finding_id="f1",
        finding_type="category_context",
        summary="Category note",
    )
    validation = EvidenceValidationResult(
        finding_id="f1",
        validation_status="weak_support",
        evidence_sufficiency=0.2,
        aligned_snippet_ids=[],
        missing_support_reasons=["no_snippet_id"],
        validator_notes="weak",
    )
    result = apply_evidence_gatekeeping(finding, validation, policy=policy)
    assert result.gatekeeping_status == "allowed"
    assert result.policy_violations == []


def test_gatekeeping_per_type_evidence_threshold_blocks_risk_signal_with_one_snippet():
    """Phase 5C: risk_signal requires 2 evidence snippets by default."""
    finding = ResearchFinding(
        finding_id="f1",
        finding_type="risk_signal",
        summary="Risky claim",
        evidence_snippets=["Only one snippet"],
        snippet_id="chk_1",
        retrieval_trace_id="trace_1",
        source_id="src_a",
    )
    validation = EvidenceValidationResult(
        finding_id="f1",
        validation_status="supported",
        evidence_sufficiency=0.8,
        aligned_snippet_ids=["chk_1"],
        missing_support_reasons=[],
        validator_notes="ok",
    )
    source = ResearchSource(
        source_id="src_a",
        lane="lane_a",
        source_type="upload",
        label="Brief",
        trust_tier=1,
    )
    result = apply_evidence_gatekeeping(finding, validation, source=source)
    # supported + insufficient_evidence_snippets violation -> downgraded
    assert result.gatekeeping_status == "downgraded"
    assert any("insufficient_evidence_snippets:1<2" in v for v in result.policy_violations)


def test_gatekeeping_per_type_evidence_threshold_allows_risk_signal_with_two_snippets():
    """Phase 5C: risk_signal with 2 snippets meets per-type threshold."""
    finding = ResearchFinding(
        finding_id="f1",
        finding_type="risk_signal",
        summary="Risky claim",
        evidence_snippets=["Snippet one", "Snippet two"],
        snippet_id="chk_1",
        retrieval_trace_id="trace_1",
        source_id="src_a",
    )
    validation = EvidenceValidationResult(
        finding_id="f1",
        validation_status="supported",
        evidence_sufficiency=0.8,
        aligned_snippet_ids=["chk_1"],
        missing_support_reasons=[],
        validator_notes="ok",
    )
    source = ResearchSource(
        source_id="src_a",
        lane="lane_a",
        source_type="upload",
        label="Brief",
        trust_tier=1,
    )
    result = apply_evidence_gatekeeping(finding, validation, source=source)
    assert result.gatekeeping_status == "allowed"
    assert result.policy_violations == []


def test_gatekeeping_category_context_uses_global_threshold():
    """Phase 5C: category_context uses global threshold of 1 snippet."""
    finding = ResearchFinding(
        finding_id="f1",
        finding_type="category_context",
        summary="Category note",
        evidence_snippets=["One snippet"],
        snippet_id="chk_1",
        retrieval_trace_id="trace_1",
        source_id="src_a",
    )
    validation = EvidenceValidationResult(
        finding_id="f1",
        validation_status="supported",
        evidence_sufficiency=0.8,
        aligned_snippet_ids=["chk_1"],
        missing_support_reasons=[],
        validator_notes="ok",
    )
    source = ResearchSource(
        source_id="src_a",
        lane="lane_a",
        source_type="upload",
        label="Brief",
        trust_tier=1,
    )
    result = apply_evidence_gatekeeping(finding, validation, source=source)
    assert result.gatekeeping_status == "allowed"
