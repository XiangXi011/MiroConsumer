"""Three-layer cognition architecture for consumer agents.

Layers:
    Perception  — processes social and media inputs
    Decision    — evaluates options and makes decisions
    Expression  — generates opinions and social content
"""

from .decision import DecisionEngine
from .engine import ConsumerCognitionEngine
from .expression import ExpressionEngine
from .perception import PerceptionEngine

__all__ = [
    "PerceptionEngine",
    "DecisionEngine",
    "ExpressionEngine",
    "ConsumerCognitionEngine",
]
