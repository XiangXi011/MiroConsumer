"""Kernel adapter ABC for consumer simulation.

Defines the contract that any simulation kernel must satisfy, along with
the validated result dataclass returned by ``generate_response``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, List, Mapping, Optional


VALID_ATTITUDE_LABELS = frozenset({"positive", "neutral", "negative"})
VALID_BUCKETS = frozenset({"resonance", "risk", "question", "misread"})


@dataclass(frozen=True, slots=True)
class SimulationKernelResult:
    """Validated output of ``SimulationKernelAdapter.generate_response``."""

    attitude_label: str
    bucket: str
    quote: str
    engagement: int

    def __post_init__(self) -> None:
        if self.attitude_label not in VALID_ATTITUDE_LABELS:
            raise ValueError(
                f"attitude_label must be one of {sorted(VALID_ATTITUDE_LABELS)}, "
                f"got {self.attitude_label!r}"
            )
        if self.bucket not in VALID_BUCKETS:
            raise ValueError(
                f"bucket must be one of {sorted(VALID_BUCKETS)}, "
                f"got {self.bucket!r}"
            )
        if not (1 <= self.engagement <= 10):
            raise ValueError(
                f"engagement must be between 1 and 10 inclusive, got {self.engagement!r}"
            )


class SimulationKernelAdapter(ABC):
    """Abstract base class for consumer simulation kernels.

    Concrete implementations (legacy deterministic, LLM-backed, etc.)
    must implement ``generate_response`` and ``compute_engagement``.
    """

    @abstractmethod
    def generate_response(
        self,
        round_num: int,
        agent_traits: Mapping[str, Any],
        visible_nodes: List[Mapping[str, Any]],
        prior_state: Optional[Mapping[str, Any]] = None,
    ) -> SimulationKernelResult:
        """Return the attitude, bucket, and quote for one agent in one round."""
        ...

    @abstractmethod
    def compute_engagement(
        self,
        influence_weight: float,
        round_num: int,
        prior_state: Optional[Mapping[str, Any]] = None,
    ) -> int:
        """Return an engagement score in [1, 10]."""
        ...
