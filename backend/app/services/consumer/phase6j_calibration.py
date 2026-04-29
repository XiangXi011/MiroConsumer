"""Phase 6J calibration report generator.

Aggregates evidence-gatekeeping, reasoning-backend, and golden-flow
metrics into a single readiness gate for Phase 7 entry.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional


@dataclass
class Phase6JCalibrationReport:
    """Calibration report output with all required Phase 6J fields."""

    golden_flow_result: Literal["PASS", "BLOCKED"] = "BLOCKED"
    evidence_gatekeeping_result: Literal["PASS", "BLOCKED"] = "BLOCKED"
    reasoning_backend_coverage: float = 0.0
    template_fallback_coverage: float = 0.0
    weak_support_finding_count: int = 0
    insufficient_support_finding_count: int = 0
    unknown_recommendation_count: int = 0
    phase7_entry_decision: Literal["PASS", "BLOCKED"] = "BLOCKED"
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "golden_flow_result": self.golden_flow_result,
            "evidence_gatekeeping_result": self.evidence_gatekeeping_result,
            "reasoning_backend_coverage": self.reasoning_backend_coverage,
            "template_fallback_coverage": self.template_fallback_coverage,
            "weak_support_finding_count": self.weak_support_finding_count,
            "insufficient_support_finding_count": self.insufficient_support_finding_count,
            "unknown_recommendation_count": self.unknown_recommendation_count,
            "phase7_entry_decision": self.phase7_entry_decision,
            "details": self.details,
        }


class Phase6JCalibrationService:
    """Build Phase 6J calibration reports from simulation artifacts."""

    def build_report(
        self,
        *,
        gatekeeping_results: Optional[List[Any]] = None,
        validation_results: Optional[List[Any]] = None,
        reasoning_events: Optional[List[Dict[str, Any]]] = None,
        golden_flow_checks: Optional[List[Dict[str, Any]]] = None,
    ) -> Phase6JCalibrationReport:
        """Build a calibration report from available simulation artifacts.

        Args:
            gatekeeping_results: List of EvidenceGatekeepingResult objects/dicts.
            validation_results: List of EvidenceValidationResult objects/dicts.
            reasoning_events: List of reasoning event dicts with 'reasoning_backend' key.
            golden_flow_checks: List of check dicts with 'status' key.
        """
        gatekeeping_results = gatekeeping_results or []
        validation_results = validation_results or []
        reasoning_events = reasoning_events or []
        golden_flow_checks = golden_flow_checks or []

        # Evidence gatekeeping counts
        weak_support_count = 0
        insufficient_support_count = 0
        for v in validation_results:
            status = (
                v.validation_status
                if hasattr(v, "validation_status")
                else v.get("validation_status", "")
            )
            if status == "weak_support":
                weak_support_count += 1
            elif status == "insufficient_support":
                insufficient_support_count += 1

        # Gatekeeping result
        blocked_gatekeeping = sum(
            1
            for g in gatekeeping_results
            if (
                g.gatekeeping_status if hasattr(g, "gatekeeping_status") else g.get("gatekeeping_status", "")
            )
            == "blocked"
        )
        gatekeeping_artifact_present = bool(gatekeeping_results)
        evidence_gatekeeping_result: Literal["PASS", "BLOCKED"] = (
            "PASS" if gatekeeping_artifact_present and not blocked_gatekeeping else "BLOCKED"
        )

        # Reasoning backend coverage
        total_reasoning = len(reasoning_events)
        llm_reasoning = sum(
            1
            for e in reasoning_events
            if (e.get("reasoning_backend", "") if isinstance(e, dict) else getattr(e, "reasoning_backend", ""))
            == "llm"
        )
        template_fallback = sum(
            1
            for e in reasoning_events
            if (e.get("reasoning_backend", "") if isinstance(e, dict) else getattr(e, "reasoning_backend", ""))
            in {"template", "template_fallback", "mock"}
        )

        reasoning_backend_coverage = (
            round(llm_reasoning / total_reasoning, 4) if total_reasoning > 0 else 0.0
        )
        template_fallback_coverage = (
            round(template_fallback / total_reasoning, 4) if total_reasoning > 0 else 0.0
        )

        # Unknown recommendation count: count reasoning events with empty/unknown summary
        unknown_count = 0
        for e in reasoning_events:
            summary = (
                e.get("reasoning_summary", "") if isinstance(e, dict) else getattr(e, "reasoning_summary", "")
            )
            if not summary or str(summary).strip().lower() in {"unknown", "", "n/a"}:
                unknown_count += 1

        # Golden flow result
        failed_golden = sum(
            1
            for c in golden_flow_checks
            if (c.get("status", "") if isinstance(c, dict) else getattr(c, "status", ""))
            == "failed"
        )
        golden_flow_result: Literal["PASS", "BLOCKED"] = (
            "PASS" if not failed_golden and golden_flow_checks else "BLOCKED"
        )
        if not golden_flow_checks:
            golden_flow_result = "BLOCKED"

        # Phase 7 entry decision: tightened P0 gates
        phase7_entry_decision: Literal["PASS", "BLOCKED"] = "PASS"
        if golden_flow_result == "BLOCKED":
            phase7_entry_decision = "BLOCKED"
        elif evidence_gatekeeping_result == "BLOCKED":
            phase7_entry_decision = "BLOCKED"
        elif total_reasoning == 0:
            phase7_entry_decision = "BLOCKED"
        elif reasoning_backend_coverage < 0.5:
            phase7_entry_decision = "BLOCKED"
        elif template_fallback_coverage > 0.3:
            phase7_entry_decision = "BLOCKED"
        elif total_reasoning > 0 and (unknown_count / total_reasoning) > 0.05:
            phase7_entry_decision = "BLOCKED"

        return Phase6JCalibrationReport(
            golden_flow_result=golden_flow_result,
            evidence_gatekeeping_result=evidence_gatekeeping_result,
            reasoning_backend_coverage=reasoning_backend_coverage,
            template_fallback_coverage=template_fallback_coverage,
            weak_support_finding_count=weak_support_count,
            insufficient_support_finding_count=insufficient_support_count,
            unknown_recommendation_count=unknown_count,
            phase7_entry_decision=phase7_entry_decision,
            details={
                "total_gatekept_findings": len(gatekeeping_results),
                "total_validation_results": len(validation_results),
                "total_reasoning_events": total_reasoning,
                "llm_reasoning_events": llm_reasoning,
                "template_fallback_events": template_fallback,
                "golden_flow_check_count": len(golden_flow_checks),
                "failed_golden_flow_checks": failed_golden,
                "blocked_gatekeeping_count": blocked_gatekeeping,
                "gatekeeping_artifact_present": gatekeeping_artifact_present,
            },
        )


__all__ = [
    "Phase6JCalibrationReport",
    "Phase6JCalibrationService",
]
