"""Consumer brief contract and adapter."""

from .models import ConsumerBusinessBrief, GraphVisibility
from .brief_adapter import ConsumerBriefAdapter

__all__ = [
    "ConsumerBusinessBrief",
    "ConsumerBriefAdapter",
    "GraphVisibility",
]
