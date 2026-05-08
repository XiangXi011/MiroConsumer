"""Consumer brief contract and adapter."""

from .models import ConsumerBusinessBrief, GraphVisibility
from .brief_adapter import ConsumerBriefAdapter
from .graph_builder import ConsumerGraphBuilder
from .orchestrator import ConsumerSimulationOrchestrator
from .report_context import ConsumerReportContextBuilder
from .kernel_adapter import SimulationKernelAdapter, SimulationKernelResult
from .legacy_kernel import LegacySimulationKernel
from .hybrid_kernel import HybridSimulationKernel
from .persona_pack import (
    can_access_deep_graph,
    load_default_persona_pack,
    map_persona_to_agent_traits,
)
from .scoring import ConsumerAttitudeSummary, ConsumerEvidenceBundle, ConsumerScoringService
from .source_quality import (
    apply_source_quality_to_findings,
    build_source_quality_summary,
    evaluate_source,
    evaluate_sources,
)
from .evidence_validator import (
    EvidenceGatekeepingPolicy,
    EvidenceGatekeepingResult,
    EvidenceValidationResult,
    apply_evidence_gatekeeping,
    apply_evidence_gatekeeping_to_findings,
    build_evidence_validation_summary,
    build_gatekeeping_summary,
    filter_allowed_findings,
    validate_finding,
    validate_findings,
)
from .confidence_scoring import (
    FindingConfidence,
    ReportConfidence,
    build_confidence_summary,
    compute_comparison_confidence,
    compute_finding_confidence,
    compute_report_confidence,
)
from .phase6j_calibration import Phase6JCalibrationReport, Phase6JCalibrationService
from .propagation_state import PropagationState, create_initial_state
from .convergence_detector import ConvergenceConfig, ConvergenceDetector

__all__ = [
    "ConsumerBusinessBrief",
    "ConsumerBriefAdapter",
    "ConsumerGraphBuilder",
    "ConsumerReportContextBuilder",
    "ConsumerSimulationOrchestrator",
    "SimulationKernelAdapter",
    "SimulationKernelResult",
    "LegacySimulationKernel",
    "HybridSimulationKernel",
    "ConsumerAttitudeSummary",
    "ConsumerEvidenceBundle",
    "ConsumerScoringService",
    "GraphVisibility",
    "can_access_deep_graph",
    "load_default_persona_pack",
    "map_persona_to_agent_traits",
    "apply_source_quality_to_findings",
    "build_source_quality_summary",
    "evaluate_source",
    "evaluate_sources",
    "EvidenceGatekeepingPolicy",
    "EvidenceGatekeepingResult",
    "EvidenceValidationResult",
    "apply_evidence_gatekeeping",
    "apply_evidence_gatekeeping_to_findings",
    "build_evidence_validation_summary",
    "build_gatekeeping_summary",
    "filter_allowed_findings",
    "validate_finding",
    "validate_findings",
    "FindingConfidence",
    "ReportConfidence",
    "build_confidence_summary",
    "compute_comparison_confidence",
    "compute_finding_confidence",
    "compute_report_confidence",
    "Phase6JCalibrationReport",
    "Phase6JCalibrationService",
    "PropagationState",
    "create_initial_state",
    "ConvergenceConfig",
    "ConvergenceDetector",
]
