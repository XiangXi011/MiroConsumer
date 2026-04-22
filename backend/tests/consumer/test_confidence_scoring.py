from pathlib import Path
import sys


BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.consumer.models import (
    GraphVisibility,
    ResearchFinding,
    ResearchSource,
    ResearchSourceLane,
    ResearchSourceType,
)
from app.services.consumer.evidence_validator import (
    EvidenceValidationResult,
    validate_finding,
)
from app.services.consumer.confidence_scoring import (
    FindingConfidence,
    ReportConfidence,
    compute_finding_confidence,
    compute_report_confidence,
    build_confidence_summary,
    compute_comparison_confidence,
)


def test_compute_finding_confidence_high():
    finding = ResearchFinding(
        finding_id="f1",
        finding_type="risk_signal",
        summary="Safety concern",
        source_id="src_a",
        confidence=0.8,
    )
    validation = EvidenceValidationResult(
        finding_id="f1",
        validation_status="supported",
        evidence_sufficiency=0.9,
        aligned_snippet_ids=["chk_1"],
        missing_support_reasons=[],
        validator_notes="ok",
    )
    source = ResearchSource(
        source_id="src_a",
        lane=ResearchSourceLane.LaneA,
        source_type=ResearchSourceType.Upload,
        label="Upload",
        trust_tier=1,
        source_confidence=0.9,
    )
    fc = compute_finding_confidence(finding, validation, source=source)
    assert fc.confidence_score >= 0.6
    assert fc.confidence_label in ("high", "medium")
    assert any("source_quality" in r for r in fc.confidence_reasons)
    assert any("evidence_sufficiency" in r for r in fc.confidence_reasons)
    assert any("evidence_validated_supported" in r for r in fc.confidence_reasons)


def test_compute_finding_confidence_low():
    finding = ResearchFinding(
        finding_id="f2",
        finding_type="category_context",
        summary="Category note",
        source_id="src_b",
        confidence=0.3,
    )
    validation = EvidenceValidationResult(
        finding_id="f2",
        validation_status="insufficient_support",
        evidence_sufficiency=0.1,
        aligned_snippet_ids=[],
        missing_support_reasons=["no_snippet_id", "no_retrieval_trace"],
        validator_notes="insufficient",
    )
    source = ResearchSource(
        source_id="src_b",
        lane=ResearchSourceLane.LaneB,
        source_type=ResearchSourceType.PublicWeb,
        label="Web",
        trust_tier=2,
        source_confidence=0.5,
    )
    fc = compute_finding_confidence(finding, validation, source=source)
    assert fc.confidence_score < 0.5
    assert fc.confidence_label in ("low", "unknown")
    assert any("evidence_validated_insufficient" in r for r in fc.confidence_reasons)


def test_compute_finding_confidence_unknown_source():
    finding = ResearchFinding(
        finding_id="f3",
        finding_type="risk_signal",
        summary="Risk",
        source_id="unknown",
    )
    validation = EvidenceValidationResult(
        finding_id="f3",
        validation_status="insufficient_support",
        evidence_sufficiency=0.0,
        aligned_snippet_ids=[],
        missing_support_reasons=["no_snippet_id"],
        validator_notes="none",
    )
    fc = compute_finding_confidence(finding, validation, source=None)
    assert fc.confidence_label in ("low", "unknown")
    assert fc.confidence_score < 0.3


def test_compute_report_confidence():
    findings = [
        ResearchFinding(
            finding_id="f1",
            finding_type="risk_signal",
            summary="A",
            source_id="src_a",
        ),
        ResearchFinding(
            finding_id="f2",
            finding_type="trend_signal",
            summary="B",
            source_id="src_b",
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
            validation_status="weak_support",
            evidence_sufficiency=0.4,
            aligned_snippet_ids=[],
            missing_support_reasons=["no_retrieval_trace"],
            validator_notes="weak",
        ),
    ]
    sources = [
        ResearchSource(
            source_id="src_a",
            lane=ResearchSourceLane.LaneA,
            source_type=ResearchSourceType.Upload,
            label="A",
            trust_tier=1,
            source_confidence=0.9,
        ),
        ResearchSource(
            source_id="src_b",
            lane=ResearchSourceLane.LaneB,
            source_type=ResearchSourceType.PublicWeb,
            label="B",
            trust_tier=2,
            source_confidence=0.5,
        ),
    ]
    rc = compute_report_confidence(findings, validations, sources)
    assert rc.confidence_score > 0
    assert rc.confidence_label in ("high", "medium", "low", "unknown")
    assert len(rc.finding_confidences) == 2
    assert rc.replay_alignment == "not_replayed"
    assert any("average_finding_confidence" in r for r in rc.confidence_reasons)


def test_compute_report_confidence_missing_validation_backfill():
    findings = [
        ResearchFinding(
            finding_id="f1",
            finding_type="risk_signal",
            summary="A",
            source_id="src_a",
        ),
    ]
    validations = []  # no validations provided
    sources = [
        ResearchSource(
            source_id="src_a",
            lane=ResearchSourceLane.LaneA,
            source_type=ResearchSourceType.Upload,
            label="A",
            trust_tier=1,
            source_confidence=0.9,
        ),
    ]
    rc = compute_report_confidence(findings, validations, sources)
    assert len(rc.finding_confidences) == 1
    # Good source quality can lift a missing-validation finding above unknown
    assert rc.finding_confidences[0].confidence_label in ("low", "medium", "unknown")
    assert any("evidence_validated_insufficient" in r for r in rc.finding_confidences[0].confidence_reasons)


def test_build_confidence_summary_structure():
    rc = ReportConfidence(
        confidence_label="medium",
        confidence_score=0.55,
        confidence_reasons=["reason"],
        support_summary="summary",
        finding_confidences=[
            FindingConfidence(
                finding_id="f1",
                confidence_label="high",
                confidence_score=0.8,
                confidence_reasons=["r1"],
                support_summary="s1",
            ),
            FindingConfidence(
                finding_id="f2",
                confidence_label="low",
                confidence_score=0.3,
                confidence_reasons=["r2"],
                support_summary="s2",
            ),
        ],
        replay_alignment="not_replayed",
    )
    summary = build_confidence_summary(rc)
    assert summary["confidence_label"] == "medium"
    assert summary["confidence_score"] == 0.55
    assert summary["replay_alignment"] == "not_replayed"
    assert len(summary["finding_confidence_summary"]) == 2
    assert len(summary["low_confidence_findings"]) == 1
    assert summary["low_confidence_findings"][0]["finding_id"] == "f2"


def test_compute_comparison_confidence():
    left = {"confidence_score": 0.7, "confidence_label": "medium"}
    right = {"confidence_score": 0.8, "confidence_label": "high"}
    result = compute_comparison_confidence(left, right)
    assert result["comparison_label"] == "strongly_supported"
    assert result["confidence_delta"] == 0.1
    assert result["left_confidence_label"] == "medium"
    assert result["right_confidence_label"] == "high"


def test_compute_comparison_confidence_weak():
    left = {"confidence_score": 0.3, "confidence_label": "low"}
    right = {"confidence_score": 0.4, "confidence_label": "low"}
    result = compute_comparison_confidence(left, right)
    assert result["comparison_label"] == "weakly_supported"
    assert result["confidence_delta"] == 0.1


def test_compute_comparison_confidence_mixed():
    left = {"confidence_score": 0.6, "confidence_label": "medium"}
    right = {"confidence_score": 0.3, "confidence_label": "low"}
    result = compute_comparison_confidence(left, right)
    assert result["comparison_label"] == "mixed_support"


def test_compute_comparison_confidence_none_inputs():
    result = compute_comparison_confidence(None, None)
    assert result["comparison_label"] == "weakly_supported"
    assert result["left_confidence_score"] == 0.0
    assert result["right_confidence_score"] == 0.0
