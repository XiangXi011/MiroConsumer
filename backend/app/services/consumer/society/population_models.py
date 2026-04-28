"""Data models for the Phase 6G consumer society runtime."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List

from .consumer_roles import ConsumerRole


VALID_LAYERS = {"core", "expanded", "shadow", "audit_sample"}
VALID_MODES = {"quick", "standard", "large_society"}


@dataclass
class ConsumerSocietyAgent:
    agent_id: str
    parent_persona_id: str
    layer: str
    segment: str
    role: ConsumerRole
    traits: Dict[str, Any] = field(default_factory=dict)
    channel_affinity: Dict[str, float] = field(default_factory=dict)
    evidence_sensitivity: float = 0.5
    price_sensitivity: float = 0.5
    trust_baseline: float = 0.5
    share_propensity: float = 0.5
    skepticism: float = 0.5
    state: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if isinstance(self.role, str):
            self.role = ConsumerRole(self.role)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["role"] = self.role.value
        return data


@dataclass
class ConsumerSocietyRunConfig:
    mode: str = "quick"
    core_persona_count: int = 8
    expanded_persona_count: int = 0
    shadow_agent_count: int = 0
    max_rounds: int = 1
    random_seed: int = 0
    llm_budget_limit: int = 0
    audit_sample_size: int = 0

    def __post_init__(self) -> None:
        self.mode = str(self.mode or "quick")
        if self.mode not in VALID_MODES:
            raise ValueError(f"Unsupported society mode: {self.mode}")

    @property
    def target_population_size(self) -> int:
        return self.core_persona_count + self.expanded_persona_count + self.shadow_agent_count

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ConsumerSocietySnapshot:
    simulation_id: str
    run_id: str
    round_index: int
    agents_count: int
    events: List[Dict[str, Any]] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    representative_agent_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


__all__ = [
    "ConsumerSocietyAgent",
    "ConsumerSocietyRunConfig",
    "ConsumerSocietySnapshot",
    "VALID_LAYERS",
    "VALID_MODES",
]
