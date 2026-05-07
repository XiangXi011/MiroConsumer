"""Phase 6J calibration report generator.

Aggregates evidence-gatekeeping, reasoning-backend, and golden-flow
metrics into a single readiness gate for Phase 7 entry.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional

from ...utils.atomic_json import atomic_write_json, safe_read_json


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
    artifact_build_inputs: Dict[str, Any] = field(default_factory=dict)

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
            "artifact_build_inputs": self.artifact_build_inputs,
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

        # Reasoning backend coverage. Phase 7H report gating counts only
        # society_runtime traces. Older direct unit inputs do not carry a source,
        # so missing source is treated as society_runtime for compatibility.
        scoped_reasoning_events = [
            e
            for e in reasoning_events
            if (
                (e.get("source", "society_runtime") if isinstance(e, dict) else getattr(e, "source", "society_runtime"))
                == "society_runtime"
            )
        ]
        total_reasoning = len(scoped_reasoning_events)
        llm_reasoning = 0
        for e in scoped_reasoning_events:
            backend = e.get("reasoning_backend", "") if isinstance(e, dict) else getattr(e, "reasoning_backend", "")
            llm_invoked = e.get("llm_invoked") if isinstance(e, dict) else getattr(e, "llm_invoked", None)
            fallback_reason = (
                e.get("fallback_reason", "") if isinstance(e, dict) else getattr(e, "fallback_reason", "")
            )
            if llm_invoked is None:
                llm_invoked = backend == "llm"
            if bool(llm_invoked) and not fallback_reason:
                llm_reasoning += 1
        template_fallback = sum(
            1
            for e in scoped_reasoning_events
            if (
                (e.get("reasoning_backend", "") if isinstance(e, dict) else getattr(e, "reasoning_backend", ""))
                in {"template", "template_fallback", "mock"}
            )
            or bool(e.get("fallback_reason", "") if isinstance(e, dict) else getattr(e, "fallback_reason", ""))
        )

        reasoning_backend_coverage = (
            round(llm_reasoning / total_reasoning, 4) if total_reasoning > 0 else 0.0
        )
        template_fallback_coverage = (
            round(template_fallback / total_reasoning, 4) if total_reasoning > 0 else 0.0
        )

        # Unknown recommendation count: count reasoning events with empty/unknown summary
        unknown_count = 0
        for e in scoped_reasoning_events:
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
                "total_raw_reasoning_traces": len(reasoning_events),
                "llm_reasoning_events": llm_reasoning,
                "template_fallback_events": template_fallback,
                "golden_flow_check_count": len(golden_flow_checks),
                "failed_golden_flow_checks": failed_golden,
                "blocked_gatekeeping_count": blocked_gatekeeping,
                "gatekeeping_artifact_present": gatekeeping_artifact_present,
            },
        )


CALIBRATION_ARTIFACT_FILE_NAME = "phase6j_calibration_artifact.json"


def write_phase6j_calibration_artifact(
    simulation_dir: str,
    report: Phase6JCalibrationReport,
) -> str:
    """Persist a Phase 6J calibration artifact to the simulation workspace."""
    path = os.path.join(simulation_dir, CALIBRATION_ARTIFACT_FILE_NAME)
    atomic_write_json(path, report.to_dict())
    return path


def read_phase6j_calibration_artifact(simulation_dir: str) -> dict | None:
    """Read a Phase 6J calibration artifact if present."""
    path = os.path.join(simulation_dir, CALIBRATION_ARTIFACT_FILE_NAME)
    if not os.path.exists(path):
        return None
    payload = safe_read_json(path, default={})
    return payload if isinstance(payload, dict) else None


def _determine_next_action(artifact: dict | None) -> str:
    """Determine the recommended next action from artifact state."""
    if artifact is None:
        return "run_calibration"
    decision = artifact.get("phase7_entry_decision", "BLOCKED")
    if decision == "PASS":
        return "regenerate_report"
    golden = artifact.get("golden_flow_result", "BLOCKED")
    gatekeeping = artifact.get("evidence_gatekeeping_result", "BLOCKED")
    if golden == "BLOCKED":
        return "inspect_failed_checks"
    if gatekeeping == "BLOCKED":
        return "inspect_failed_checks"
    coverage = artifact.get("reasoning_backend_coverage", 0.0)
    fallback = artifact.get("template_fallback_coverage", 0.0)
    if coverage < 0.5 or fallback > 0.3:
        return "run_calibration"
    return "inspect_failed_checks"


def check_phase6j_gate(simulation_dir: str) -> dict:
    """Check whether a Phase 6J calibration hard gate blocks entry.

    Returns a dict with structured diagnostics:
        - blocked: bool — True when an artifact exists and phase7_entry_decision != PASS
        - reason: str — human-readable reason when blocked
        - details: dict — artifact summary when present
        - error_code: str — PHASE6J_ARTIFACT_MISSING or PHASE6J_BLOCKED
        - blocking_stage: str — "calibration"
        - recoverable: bool — True
        - next_action: str — run_calibration | inspect_failed_checks | regenerate_report
        - suggested_action: str — alias for next_action
    """
    artifact = read_phase6j_calibration_artifact(simulation_dir)
    if artifact is None:
        details = {"artifact_present": False}
        return {
            "blocked": True,
            "reason": "Phase 6J calibration blocks entry: calibration artifact is missing",
            "details": details,
            "error_code": "PHASE6J_ARTIFACT_MISSING",
            "blocking_stage": "calibration",
            "recoverable": True,
            "next_action": "run_calibration",
            "suggested_action": "run_calibration",
        }
    decision = artifact.get("phase7_entry_decision", "BLOCKED")
    artifact_inputs = artifact.get("artifact_build_inputs") or artifact.get("details", {}).get("artifact_build_inputs")
    details = {
        "artifact_present": True,
        "phase7_entry_decision": decision,
        "golden_flow_result": artifact.get("golden_flow_result", "BLOCKED"),
        "evidence_gatekeeping_result": artifact.get("evidence_gatekeeping_result", "BLOCKED"),
        "reasoning_backend_coverage": artifact.get("reasoning_backend_coverage", 0.0),
        "template_fallback_coverage": artifact.get("template_fallback_coverage", 0.0),
    }
    # Include artifact_build_inputs when available
    if artifact_inputs:
        details["artifact_build_inputs"] = artifact_inputs
    if decision == "PASS":
        return {
            "blocked": False,
            "reason": "",
            "details": details,
            "error_code": "",
            "blocking_stage": "",
            "recoverable": True,
            "next_action": "regenerate_report",
            "suggested_action": "regenerate_report",
        }
    next_action = _determine_next_action(artifact)
    return {
        "blocked": True,
        "reason": f"Phase 6J calibration blocks entry: phase7_entry_decision={decision}",
        "details": details,
        "error_code": "PHASE6J_BLOCKED",
        "blocking_stage": "calibration",
        "recoverable": True,
        "next_action": next_action,
        "suggested_action": next_action,
    }


__all__ = [
    "Phase6JCalibrationReport",
    "Phase6JCalibrationService",
    "write_phase6j_calibration_artifact",
    "read_phase6j_calibration_artifact",
    "check_phase6j_gate",
]
