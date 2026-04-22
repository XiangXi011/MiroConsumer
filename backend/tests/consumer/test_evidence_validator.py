from pathlib import Path
import sys


BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.consumer.models import (
    DocumentChunk,
    GraphVisibility,
    ResearchFinding,
    RetrievalTrace,
)
from app.services.consumer.evidence_validator import (
    EvidenceValidationResult,
    validate_finding,
    validate_findings,
    build_evidence_validation_summary,
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
