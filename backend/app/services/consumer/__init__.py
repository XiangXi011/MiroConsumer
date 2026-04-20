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
]
