"""Enhanced consumer demographics and persona modeling."""

from .persona import ConsumerPersona
from .population import PERSONA_TEMPLATES, PopulationGenerator

__all__ = [
    "ConsumerPersona",
    "PopulationGenerator",
    "PERSONA_TEMPLATES",
]
