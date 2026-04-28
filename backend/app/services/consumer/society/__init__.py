"""Consumer society runtime bridge for Phase 6G."""

from .consumer_roles import ConsumerRole
from .population_models import (
    ConsumerSocietyAgent,
    ConsumerSocietyRunConfig,
    ConsumerSocietySnapshot,
)

__all__ = [
    "ConsumerRole",
    "ConsumerSocietyAgent",
    "ConsumerSocietyRunConfig",
    "ConsumerSocietySnapshot",
]
