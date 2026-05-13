"""Confidence scoring layer for consumer_test findings and reports.

The P3 confidence formula is intentionally explicit: source quality and
evidence sufficiency carry the largest weights, signal consistency and replay
alignment stabilize simulation-derived claims, and the two calibration terms
(`external_validity`, `expert_consensus`) keep high-confidence labels from
resting only on synthetic agreement.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from .evidence_validator import EvidenceValidationResult
from .models import ResearchSourceLane


CONFIDENCE_WEIGHTS: Dict[str, float] = {
    "source_quality": 0.30,
    "evidence_sufficiency": 0.30,
    "signal_consistency": 0.15,
    "replay_alignment": 0.10,
    "external_validity": 0.10,
    "expert_consensus": 0.05,
}


class FindingConfidence(BaseModel):
    finding_id: str
    confidence_label: str
    confidence_score: float
    confidence_reasons: List[str]
    support_summary: str


class ReportConfidence(BaseModel):
    confidence_label: str
    confidence_score: float
    confidence_reasons: List[str]
    support_summary: str
    finding_confidences: List[FindingConfidence]
    replay_alignment: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "confidence_label": self.confidence_label,
            "confidence_score": self.confidence_score,
            "confidence_reasons": self.confidence_reasons,
            "support_summary": self.support_summary,
            "finding_confidences": [fc.model_dump() for fc in self.finding_confidences],
            "replay_alignment": self.replay_alignment,
        }


def _label_from_score(score: float) -> str:
    """Map score to label. Uses calibrated thresholds if available, else defaults."""
    from .confidence_calibrator import get_thresholds
    t = get_thresholds()
    return t.label_for_score(score)


def _source_quality_score(finding: Any, source: Optional[Any]) -> float:
    """Extract source quality score from a finding and its source."""
    if source is None:
        return 0.3

    source_confidence = (
        source.source_confidence
        if hasattr(source, "source_confidence")
        else source.get("source_confidence", 0.0)
    )
    trust_tier = (
        source.trust_tier if hasattr(source, "trust_tier") else source.get("trust_tier", 2)
    )
    lane = source.lane if hasattr(source, "lane") else source.get("lane", "lane_b")

    lane_boost = 0.1
    if (
        isinstance(lane, ResearchSourceLane) and lane == ResearchSourceLane.LaneA
    ) or str(lane) == "lane_a":
        lane_boost = 0.1
    else:
        lane_boost = 0.0

    tier_penalty = (trust_tier - 1) * 0.1

    return max(0.0, min(1.0, source_confidence + lane_boost - tier_penalty))


def _signal_consistency_score(finding: Any, all_findings: List[Any]) -> float:
    """Compute signal consistency by checking how well a finding aligns with others of the same type."""
    if not all_findings:
        return 0.5

    finding_type = (
        finding.finding_type if hasattr(finding, "finding_type") else finding.get("finding_type", "")
    )
    same_type = [
        f
        for f in all_findings
        if (
            f.finding_type if hasattr(f, "finding_type") else f.get("finding_type", "")
        )
        == finding_type
    ]

    if len(same_type) <= 1:
        return 0.5

    consistency = min(1.0, 0.4 + 0.15 * len(same_type))
    return round(consistency, 4)




def _replay_alignment_score(finding: Any, explicit_score: Optional[float] = None) -> float:
    """Return a bounded replay alignment score from explicit or finding-provided data."""
    candidates: List[Any] = []
    if explicit_score is not None:
        candidates.append(explicit_score)
    if finding is not None:
        getter = finding.get if isinstance(finding, dict) else lambda key, default=None: getattr(finding, key, default)
        candidates.extend(
            [
                getter("replay_score", None),
                getter("replay_alignment_score", None),
                getter("benchmark_replay_score", None),
            ]
        )

    for candidate in candidates:
        if candidate is None:
            continue
        try:
            score = float(candidate)
        except (TypeError, ValueError):
            continue
        return max(0.0, min(1.0, score))
    return 0.5


def _bounded_score(value: Any, fallback: float = 0.5) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        score = fallback
    return max(0.0, min(1.0, score))


def _finding_score_field(finding: Any, key: str, fallback: float = 0.5) -> float:
    if finding is None:
        return fallback
    if isinstance(finding, dict):
        return _bounded_score(finding.get(key), fallback)
    return _bounded_score(getattr(finding, key, None), fallback)


def compute_weighted_confidence_score(
    *,
    source_quality: float,
    evidence_sufficiency: float,
    signal_consistency: float,
    replay_alignment: float,
    external_validity: float = 0.5,
    expert_consensus: float = 0.5,
) -> float:
    """Compute the P3 six-weight confidence formula."""
    weights = CONFIDENCE_WEIGHTS
    return round(
        weights["source_quality"] * _bounded_score(source_quality)
        + weights["evidence_sufficiency"] * _bounded_score(evidence_sufficiency)
        + weights["signal_consistency"] * _bounded_score(signal_consistency)
        + weights["replay_alignment"] * _bounded_score(replay_alignment)
        + weights["external_validity"] * _bounded_score(external_validity)
        + weights["expert_consensus"] * _bounded_score(expert_consensus),
        4,
    )


def compute_finding_confidence(
    finding: Any,
    validation_result: EvidenceValidationResult,
    source: Optional[Any] = None,
    all_findings: Optional[List[Any]] = None,
    replay_score: Optional[float] = None,
    external_validity_score: Optional[float] = None,
    expert_consensus_score: Optional[float] = None,
) -> FindingConfidence:
    """Compute structured confidence for a single finding."""
    finding_id = (
        finding.finding_id if hasattr(finding, "finding_id") else finding.get("finding_id", "")
    )

    src_score = _source_quality_score(finding, source)
    ev_score = validation_result.evidence_sufficiency
    findings_list = all_findings or []
    sig_score = _signal_consistency_score(finding, findings_list)
    replay_score_value = _replay_alignment_score(finding, replay_score)
    external_score = _bounded_score(
        external_validity_score
        if external_validity_score is not None
        else _finding_score_field(finding, "external_validity_score", 0.5)
    )
    expert_score = _bounded_score(
        expert_consensus_score
        if expert_consensus_score is not None
        else _finding_score_field(finding, "expert_consensus_score", 0.5)
    )

    confidence_score = compute_weighted_confidence_score(
        source_quality=src_score,
        evidence_sufficiency=ev_score,
        signal_consistency=sig_score,
        replay_alignment=replay_score_value,
        external_validity=external_score,
        expert_consensus=expert_score,
    )

    label = _label_from_score(confidence_score)

    confidence_reasons: List[str] = []
    confidence_reasons.append(f"source_quality:{round(src_score, 2)}")
    confidence_reasons.append(f"evidence_sufficiency:{round(ev_score, 2)}")
    confidence_reasons.append(f"signal_consistency:{round(sig_score, 2)}")
    confidence_reasons.append(f"replay_alignment:{round(replay_score_value, 4):g}")
    confidence_reasons.append(f"external_validity:{round(external_score, 2):g}")
    confidence_reasons.append(f"expert_consensus:{round(expert_score, 2):g}")

    if validation_result.validation_status == "supported":
        confidence_reasons.append("evidence_validated_supported")
    elif validation_result.validation_status == "weak_support":
        confidence_reasons.append("evidence_validated_weak")
    else:
        confidence_reasons.append("evidence_validated_insufficient")

    if source is not None:
        lane = source.lane if hasattr(source, "lane") else source.get("lane", "")
        lane_val = lane.value if hasattr(lane, "value") else str(lane)
        confidence_reasons.append(f"source_lane:{lane_val}")

    support_summary = (
        f"Validation: {validation_result.validation_status}; "
        f"sufficiency={validation_result.evidence_sufficiency}; "
        f"aligned_snippets={len(validation_result.aligned_snippet_ids)}"
    )

    return FindingConfidence(
        finding_id=finding_id,
        confidence_label=label,
        confidence_score=confidence_score,
        confidence_reasons=confidence_reasons,
        support_summary=support_summary,
    )


def compute_report_confidence(
    findings: List[Any],
    validations: List[EvidenceValidationResult],
    sources: List[Any],
    all_findings: Optional[List[Any]] = None,
) -> ReportConfidence:
    """Compute report-level confidence from findings and validations."""
    source_by_id: Dict[str, Any] = {}
    for s in sources:
        sid = s.source_id if hasattr(s, "source_id") else s.get("source_id", "")
        if sid:
            source_by_id[sid] = s

    validation_by_id = {v.finding_id: v for v in validations}
    findings_list = all_findings or findings

    finding_confidences: List[FindingConfidence] = []
    for finding in findings:
        finding_id = (
            finding.finding_id if hasattr(finding, "finding_id") else finding.get("finding_id", "")
        )
        source_id = (
            finding.source_id if hasattr(finding, "source_id") else finding.get("source_id", "")
        )
        source = source_by_id.get(source_id) if source_id else None
        validation = validation_by_id.get(finding_id)
        if validation is None:
            validation = EvidenceValidationResult(
                finding_id=finding_id,
                validation_status="insufficient_support",
                evidence_sufficiency=0.0,
                aligned_snippet_ids=[],
                missing_support_reasons=["no_validation_performed"],
                validator_notes="Validation not performed for this finding",
            )

        fc = compute_finding_confidence(
            finding, validation, source=source, all_findings=findings_list
        )
        finding_confidences.append(fc)

    if not finding_confidences:
        return ReportConfidence(
            confidence_label="unknown",
            confidence_score=0.0,
            confidence_reasons=["no_findings_to_score"],
            support_summary="No findings available for confidence scoring",
            finding_confidences=[],
            replay_alignment="not_replayed",
        )

    avg_score = sum(fc.confidence_score for fc in finding_confidences) / len(finding_confidences)
    label = _label_from_score(avg_score)

    low_confidence_count = sum(
        1 for fc in finding_confidences if fc.confidence_label in ("low", "unknown")
    )

    confidence_reasons = [
        f"average_finding_confidence:{round(avg_score, 2)}",
        f"finding_count:{len(finding_confidences)}",
        f"low_confidence_findings:{low_confidence_count}",
    ]

    supported_count = sum(
        1 for fc in finding_confidences if "evidence_validated_supported" in fc.confidence_reasons
    )
    weak_count = sum(
        1 for fc in finding_confidences if "evidence_validated_weak" in fc.confidence_reasons
    )
    insufficient_count = sum(
        1 for fc in finding_confidences if "evidence_validated_insufficient" in fc.confidence_reasons
    )
    confidence_reasons.append(f"supported_findings:{supported_count}")
    confidence_reasons.append(f"weak_support_findings:{weak_count}")
    confidence_reasons.append(f"insufficient_findings:{insufficient_count}")

    support_summary = (
        f"Report confidence based on {len(finding_confidences)} findings: "
        f"{supported_count} supported, {weak_count} weak, {insufficient_count} insufficient; "
        f"{low_confidence_count} low-confidence"
    )

    return ReportConfidence(
        confidence_label=label,
        confidence_score=round(avg_score, 4),
        confidence_reasons=confidence_reasons,
        support_summary=support_summary,
        finding_confidences=finding_confidences,
        replay_alignment="not_replayed",
    )


def build_confidence_summary(report_confidence: ReportConfidence) -> Dict[str, Any]:
    """Build a flat summary dict for API responses."""
    low_confidence_findings = [
        fc.model_dump()
        for fc in report_confidence.finding_confidences
        if fc.confidence_label in ("low", "unknown")
    ]

    return {
        "confidence_label": report_confidence.confidence_label,
        "confidence_score": report_confidence.confidence_score,
        "confidence_reasons": report_confidence.confidence_reasons,
        "support_summary": report_confidence.support_summary,
        "replay_alignment": report_confidence.replay_alignment,
        "finding_confidence_summary": [
            {
                "finding_id": fc.finding_id,
                "confidence_label": fc.confidence_label,
                "confidence_score": fc.confidence_score,
            }
            for fc in report_confidence.finding_confidences
        ],
        "low_confidence_findings": low_confidence_findings,
    }


def compute_confidence(
    source_quality: float,
    evidence_sufficiency: float,
    simulation_stability: float,
    cross_run_consistency: float,
    benchmark_alignment: float,
    contradiction_count: int = 0,
    fallback_count: int = 0,
) -> float:
    """Compute weighted confidence score with penalty terms."""
    score = (
        0.25 * source_quality
        + 0.25 * evidence_sufficiency
        + 0.20 * simulation_stability
        + 0.15 * cross_run_consistency
        + 0.15 * benchmark_alignment
    )
    score -= 0.05 * min(contradiction_count, 5)
    score -= 0.03 * min(fallback_count, 10)
    return max(0.0, min(1.0, round(score, 4)))


def compute_comparison_confidence(
    left_confidence: Optional[Dict[str, Any]],
    right_confidence: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Compute comparison-level confidence from two sides."""
    left_score = left_confidence.get("confidence_score", 0.0) if left_confidence else 0.0
    right_score = right_confidence.get("confidence_score", 0.0) if right_confidence else 0.0

    delta = round(right_score - left_score, 4)

    left_label = (
        left_confidence.get("confidence_label", "unknown") if left_confidence else "unknown"
    )
    right_label = (
        right_confidence.get("confidence_label", "unknown") if right_confidence else "unknown"
    )

    if left_score >= 0.5 and right_score >= 0.5:
        comparison_label = "strongly_supported"
    elif left_score >= 0.5 or right_score >= 0.5:
        comparison_label = "mixed_support"
    else:
        comparison_label = "weakly_supported"

    return {
        "comparison_label": comparison_label,
        "confidence_delta": delta,
        "left_confidence_label": left_label,
        "right_confidence_label": right_label,
        "left_confidence_score": left_score,
        "right_confidence_score": right_score,
        "support_summary": f"Comparison confidence: {comparison_label}; delta={delta}",
    }



