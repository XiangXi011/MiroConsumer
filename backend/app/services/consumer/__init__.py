"""Consumer brief contract and adapter."""

from .models import ConsumerBusinessBrief, GraphVisibility
from .brief_adapter import ConsumerBriefAdapter
from .graph_builder import ConsumerGraphBuilder
from .orchestrator import ConsumerSimulationOrchestrator
from .report_context import ConsumerReportContextBuilder
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

__all__ = [
    "ConsumerBusinessBrief",
    "ConsumerBriefAdapter",
    "ConsumerGraphBuilder",
    "ConsumerReportContextBuilder",
    "ConsumerSimulationOrchestrator",
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
]
