"""Validation for generated consumer society populations."""

from __future__ import annotations

from typing import Iterable

from .consumer_roles import ConsumerRole
from .population_models import ConsumerSocietyAgent, ConsumerSocietyRunConfig, VALID_LAYERS


NUMERIC_FIELDS = (
    "evidence_sensitivity",
    "price_sensitivity",
    "trust_baseline",
    "share_propensity",
    "skepticism",
)


class PersonaQualityChecker:
    """Enforce deterministic population contract before runtime execution."""

    def validate(
        self,
        population: Iterable[ConsumerSocietyAgent],
        config: ConsumerSocietyRunConfig,
    ) -> None:
        agents = list(population)
        ids = [agent.agent_id for agent in agents]
        if len(ids) != len(set(ids)):
            raise ValueError("agent_id must be globally unique")

        segments = set()
        has_shadow = False
        for agent in agents:
            if not agent.parent_persona_id:
                raise ValueError("parent_persona_id must be non-empty")
            if agent.layer not in VALID_LAYERS:
                raise ValueError(f"invalid layer: {agent.layer}")
            if agent.layer == "shadow":
                has_shadow = True
            if not isinstance(agent.role, ConsumerRole):
                raise ValueError(f"invalid role: {agent.role}")
            if agent.segment:
                segments.add(agent.segment)
            for field_name in NUMERIC_FIELDS:
                value = getattr(agent, field_name)
                if not 0.0 <= float(value) <= 1.0:
                    raise ValueError(f"{field_name} must be between 0.0 and 1.0")
            for trait_name in ("category_familiarity", "risk_memory", "social_influence_weight"):
                value = agent.traits.get(trait_name)
                if value is not None and not 0.0 <= float(value) <= 1.0:
                    raise ValueError(f"{trait_name} must be between 0.0 and 1.0")

        if len(segments) <= 1 and len(agents) > 1:
            raise ValueError("segment distribution cannot be concentrated in one segment")
        if config.mode in {"standard", "large_society"} and not has_shadow:
            raise ValueError("standard and large_society populations require shadow agents")
        if len(agents) != config.target_population_size:
            raise ValueError("population total does not match config target")


__all__ = ["PersonaQualityChecker"]
