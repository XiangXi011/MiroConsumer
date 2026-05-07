"""Phase6JCalibrationArtifactBuilder.

Builds calibration artifacts with a fixed input contract:
- required: society/reasoning_traces.jsonl, golden_flow_checks.json
- conditional required: evidence_gatekeeping_results.json, evidence_validation_results.json
- optional: society/runtime_events.jsonl, society/rounds/round_*.json,
  society/society_metrics.json, society/channel_events.jsonl,
  society/propagation_paths.json, society/network_topology.json

Coverage counts only traces where source == society_runtime
AND llm_invoked is true AND fallback_reason is empty.
Missing required inputs produce BLOCKED artifact.
Quick runs may generate artifacts but cannot automatically PASS.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

from .phase6j_calibration import (
    Phase6JCalibrationReport,
    Phase6JCalibrationService,
    write_phase6j_calibration_artifact,
)
from .reasoning_trace import read_reasoning_traces, ReasoningTrace
from .evidence_validator import EvidenceValidationResult, EvidenceGatekeepingResult


class Phase6JCalibrationArtifactBuilder:
    """Build Phase 6J calibration artifacts from simulation workspace."""

    # Fixed input paths relative to simulation_dir
    REASONING_TRACES_PATH = "society/reasoning_traces.jsonl"
    GOLDEN_FLOW_CHECKS_PATH = "golden_flow_checks.json"
    EVIDENCE_GATEKEEPING_PATH = "evidence_gatekeeping_results.json"
    EVIDENCE_VALIDATION_PATH = "evidence_validation_results.json"

    OPTIONAL_PATHS = [
        "society/runtime_events.jsonl",
        "society/society_metrics.json",
        "society/channel_events.jsonl",
        "society/propagation_paths.json",
        "society/network_topology.json",
    ]

    def __init__(self, simulation_dir: str):
        self.simulation_dir = simulation_dir

    def build(self) -> Dict[str, Any]:
        """Build a calibration artifact dict from the simulation workspace.

        Returns a dict that can be persisted as phase6j_calibration_artifact.json.
        The dict includes artifact_build_inputs with present/missing status.
        """
        inputs_status: Dict[str, Dict[str, Any]] = {}

        # --- Required inputs ---
        reasoning_traces = self._read_reasoning_traces()
        inputs_status["reasoning_traces"] = {
            "present": reasoning_traces is not None,
            "missing": reasoning_traces is None,
        }

        golden_flow_checks = self._read_golden_flow_checks()
        inputs_status["golden_flow_checks"] = {
            "present": golden_flow_checks is not None,
            "missing": golden_flow_checks is None,
        }

        # --- Conditional required inputs ---
        gatekeeping_results = self._read_evidence_gatekeeping()
        inputs_status["evidence_gatekeeping_results"] = {
            "present": gatekeeping_results is not None,
            "missing": gatekeeping_results is None,
        }

        validation_results = self._read_evidence_validation()
        inputs_status["evidence_validation_results"] = {
            "present": validation_results is not None,
            "missing": validation_results is None,
        }

        # --- Optional inputs (for tracking, not required) ---
        for opt_path in self.OPTIONAL_PATHS:
            full = os.path.join(self.simulation_dir, opt_path)
            inputs_status[opt_path] = {
                "present": os.path.exists(full),
                "missing": not os.path.exists(full),
            }

        # Check for round files
        rounds_dir = os.path.join(self.simulation_dir, "society", "rounds")
        round_files = []
        if os.path.isdir(rounds_dir):
            round_files = [
                f for f in os.listdir(rounds_dir)
                if f.startswith("round_") and f.endswith(".json")
            ]
        inputs_status["society_rounds"] = {
            "present": len(round_files) > 0,
            "missing": len(round_files) == 0,
            "count": len(round_files),
        }

        required_missing = reasoning_traces is None or golden_flow_checks is None
        conditional_missing = gatekeeping_results is None or validation_results is None

        reasoning_events = [t.to_dict() for t in (reasoning_traces or [])]

        # Build the calibration report
        service = Phase6JCalibrationService()
        report = service.build_report(
            gatekeeping_results=gatekeeping_results or [],
            validation_results=validation_results or [],
            reasoning_events=reasoning_events,
            golden_flow_checks=golden_flow_checks or [],
        )

        # Required or conditional-required input gaps produce a BLOCKED artifact.
        if required_missing or conditional_missing:
            report.phase7_entry_decision = "BLOCKED"
            report.details["missing_required_inputs"] = [
                key
                for key in ("reasoning_traces", "golden_flow_checks")
                if inputs_status[key]["missing"]
            ]
            report.details["missing_conditional_inputs"] = [
                key
                for key in ("evidence_gatekeeping_results", "evidence_validation_results")
                if inputs_status[key]["missing"]
            ]

        # No evidence = UNKNOWN = FAIL (BLOCKED)
        # If gatekeeping_results are missing, evidence_gatekeeping_result is already BLOCKED
        # from the service. If validation_results are missing but gatekeeping is present,
        # we still need validation for a complete picture. The service already handles
        # empty gatekeeping as BLOCKED.

        result = report.to_dict()
        result["artifact_build_inputs"] = inputs_status

        # Include additional details about trace filtering
        result["details"]["total_reasoning_traces"] = len(reasoning_traces) if reasoning_traces else 0
        result["details"]["coverage_eligible_traces"] = report.details.get("total_reasoning_events", 0)
        result["details"]["excluded_traces"] = (
            len(reasoning_traces) - report.details.get("total_reasoning_events", 0)
        ) if reasoning_traces else 0

        return result

    def _read_reasoning_traces(self) -> Optional[List[ReasoningTrace]]:
        path = os.path.join(self.simulation_dir, self.REASONING_TRACES_PATH)
        if not os.path.exists(path):
            return None
        traces = read_reasoning_traces(self.simulation_dir)
        return traces if traces else []

    def _read_golden_flow_checks(self) -> Optional[List[Dict[str, Any]]]:
        path = os.path.join(self.simulation_dir, self.GOLDEN_FLOW_CHECKS_PATH)
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else None
        except (json.JSONDecodeError, OSError):
            return None

    def _read_evidence_gatekeeping(self) -> Optional[List[EvidenceGatekeepingResult]]:
        path = os.path.join(self.simulation_dir, self.EVIDENCE_GATEKEEPING_PATH)
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, list):
                return None
            results: List[EvidenceGatekeepingResult] = []
            for item in data:
                if isinstance(item, dict):
                    results.append(EvidenceGatekeepingResult(**item))
                elif isinstance(item, EvidenceGatekeepingResult):
                    results.append(item)
            return results
        except (json.JSONDecodeError, OSError, TypeError):
            return None

    def _read_evidence_validation(self) -> Optional[List[EvidenceValidationResult]]:
        path = os.path.join(self.simulation_dir, self.EVIDENCE_VALIDATION_PATH)
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, list):
                return None
            results: List[EvidenceValidationResult] = []
            for item in data:
                if isinstance(item, dict):
                    results.append(EvidenceValidationResult(**item))
                elif isinstance(item, EvidenceValidationResult):
                    results.append(item)
            return results
        except (json.JSONDecodeError, OSError, TypeError):
            return None


def build_phase6j_calibration_artifact(simulation_dir: str) -> str:
    """Build and persist a Phase 6J calibration artifact.

    Returns the path to the written artifact file.
    """
    builder = Phase6JCalibrationArtifactBuilder(simulation_dir)
    artifact_dict = builder.build()

    # Convert dict back to Phase6JCalibrationReport for persistence
    report = Phase6JCalibrationReport(
        golden_flow_result=artifact_dict.get("golden_flow_result", "BLOCKED"),
        evidence_gatekeeping_result=artifact_dict.get("evidence_gatekeeping_result", "BLOCKED"),
        reasoning_backend_coverage=artifact_dict.get("reasoning_backend_coverage", 0.0),
        template_fallback_coverage=artifact_dict.get("template_fallback_coverage", 0.0),
        weak_support_finding_count=artifact_dict.get("weak_support_finding_count", 0),
        insufficient_support_finding_count=artifact_dict.get("insufficient_support_finding_count", 0),
        unknown_recommendation_count=artifact_dict.get("unknown_recommendation_count", 0),
        phase7_entry_decision=artifact_dict.get("phase7_entry_decision", "BLOCKED"),
        details=artifact_dict.get("details", {}),
        artifact_build_inputs=artifact_dict.get("artifact_build_inputs", {}),
    )
    # Keep the legacy details mirror for callers that already inspect details.
    report.details["artifact_build_inputs"] = artifact_dict.get("artifact_build_inputs", {})

    return write_phase6j_calibration_artifact(simulation_dir, report)


__all__ = [
    "Phase6JCalibrationArtifactBuilder",
    "build_phase6j_calibration_artifact",
]
