"""Build layered consumer society populations from persona packs."""

from __future__ import annotations

import hashlib
from typing import Any, Iterable, List, Mapping

from .consumer_roles import ConsumerRole
from .persona_variation_generator import PersonaVariationGenerator
from .population_models import ConsumerSocietyAgent, ConsumerSocietyRunConfig


class PopulationFactory:
    """Create deterministic core, expanded, and shadow consumer society agents."""

    def build_population(
        self,
        persona_pack: Iterable[Mapping[str, Any]],
        config: ConsumerSocietyRunConfig,
    ) -> List[ConsumerSocietyAgent]:
        personas = list(persona_pack)
        if not personas:
            raise ValueError("persona_pack must not be empty")

        generator = PersonaVariationGenerator(seed=config.random_seed)
        population: List[ConsumerSocietyAgent] = []
        role_cycle = list(ConsumerRole)

        core_count = config.core_persona_count
        for index in range(core_count):
            persona = personas[index % len(personas)]
            variation = generator.generate(persona, index=index, layer="core")
            role = role_cycle[index % len(role_cycle)] if config.mode != "quick" else variation["role"]
            population.append(
                self._agent_from_variation(
                    persona=persona,
                    variation={**variation, "role": role},
                    layer="core",
                    index=index,
                    seed=config.random_seed,
                )
            )

        for index in range(config.expanded_persona_count):
            persona = personas[index % len(personas)]
            variation = generator.generate(persona, index=index + core_count, layer="expanded")
            role = role_cycle[(index + core_count) % len(role_cycle)] if config.mode != "quick" else variation["role"]
            population.append(
                self._agent_from_variation(
                    persona=persona,
                    variation={**variation, "role": role},
                    layer="expanded",
                    index=index,
                    seed=config.random_seed,
                )
            )

        for index in range(config.shadow_agent_count):
            persona = personas[index % len(personas)]
            variation = generator.generate(
                persona,
                index=index + core_count + config.expanded_persona_count,
                layer="shadow",
            )
            role = role_cycle[(index + core_count + config.expanded_persona_count) % len(role_cycle)]
            population.append(
                self._agent_from_variation(
                    persona=persona,
                    variation={**variation, "role": role},
                    layer="shadow",
                    index=index,
                    seed=config.random_seed,
                )
            )

        return population

    def _agent_from_variation(
        self,
        persona: Mapping[str, Any],
        variation: Mapping[str, Any],
        layer: str,
        index: int,
        seed: int,
    ) -> ConsumerSocietyAgent:
        persona_id = str(persona.get("persona_id", "persona")).strip() or "persona"
        agent_hash = hashlib.sha1(f"{seed}:{layer}:{persona_id}:{index}".encode("utf-8")).hexdigest()[:10]
        role = variation["role"]
        if isinstance(role, str):
            role = ConsumerRole(role)

        trust = float(variation["trust_baseline"])
        purchase_intent = round((trust + float(variation["share_propensity"])) / 2, 4)
        return ConsumerSocietyAgent(
            agent_id=f"{layer}_{persona_id}_{index}_{agent_hash}",
            parent_persona_id=persona_id,
            layer=layer,
            segment=str(variation["segment"]),
            role=role,
            traits=dict(variation["traits"]),
            channel_affinity=dict(variation["channel_affinity"]),
            evidence_sensitivity=float(variation["evidence_sensitivity"]),
            price_sensitivity=float(variation["price_sensitivity"]),
            trust_baseline=trust,
            share_propensity=float(variation["share_propensity"]),
            skepticism=float(variation["skepticism"]),
            state={
                "trust": trust,
                "purchase_intent": purchase_intent,
                "awareness": 0.0,
            },
        )


__all__ = ["PopulationFactory"]
