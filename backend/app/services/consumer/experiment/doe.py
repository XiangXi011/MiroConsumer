"""Experiment design helpers for consumer testing."""

from __future__ import annotations

import itertools
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ExperimentVariant:
    variant_id: str
    name: str
    description: str
    modifications: Dict


@dataclass
class ExperimentDesign:
    experiment_id: str
    name: str
    hypothesis: str
    variants: List[ExperimentVariant]
    control_variant_id: str
    independent_variables: List[str]
    dependent_metrics: List[str]
    random_seed: Optional[int] = None
    stratify_by: List[str] = field(default_factory=list)
    control_variables: Dict = field(default_factory=dict)
    metadata: Dict = field(default_factory=dict)


class ExperimentDesigner:
    """Factory for A/B, ladder, factorial, and sequential experiment designs."""

    def create_ab_test(
        self,
        name: str,
        hypothesis: str,
        control_config: Dict,
        treatment_config: Dict,
    ) -> ExperimentDesign:
        return ExperimentDesign(
            experiment_id=f"exp_{random.randint(10000, 99999)}",
            name=name,
            hypothesis=hypothesis,
            variants=[
                ExperimentVariant("control", "Control", "Control group", control_config),
                ExperimentVariant("treatment", "Treatment", "Treatment group", treatment_config),
            ],
            control_variant_id="control",
            independent_variables=["treatment"],
            dependent_metrics=["acceptance_rate", "purchase_intent", "credibility"],
        )

    def create_price_ladder(self, name: str, prices: List[float]) -> ExperimentDesign:
        variants = [
            ExperimentVariant(f"price_{index}", f"Price {price}", f"Price point {price}", {"price": price})
            for index, price in enumerate(prices)
        ]
        return ExperimentDesign(
            experiment_id=f"exp_{random.randint(10000, 99999)}",
            name=name,
            hypothesis=f"Price sensitivity test across {len(prices)} price points",
            variants=variants,
            control_variant_id="price_0",
            independent_variables=["price"],
            dependent_metrics=["purchase_intent", "price_perception", "value_score"],
        )

    def create_message_variant(self, name: str, messages: List[str]) -> ExperimentDesign:
        variants = [
            ExperimentVariant(f"msg_{index}", f"Message {index}", message, {"message": message})
            for index, message in enumerate(messages)
        ]
        if not variants:
            variants.append(ExperimentVariant("msg_0", "Empty", "", {"message": ""}))
        return ExperimentDesign(
            experiment_id=f"exp_{random.randint(10000, 99999)}",
            name=name,
            hypothesis=f"Message variant test across {len(messages)} messages",
            variants=variants,
            control_variant_id="msg_0",
            independent_variables=["message"],
            dependent_metrics=["acceptance_rate", "purchase_intent", "credibility"],
        )

    def create_claim_variant(self, name: str, claims: List[str]) -> ExperimentDesign:
        variants = [
            ExperimentVariant(f"claim_{index}", f"Claim {index}", claim, {"claim": claim})
            for index, claim in enumerate(claims)
        ]
        if not variants:
            variants.append(ExperimentVariant("claim_0", "Empty", "", {"claim": ""}))
        return ExperimentDesign(
            experiment_id=f"exp_{random.randint(10000, 99999)}",
            name=name,
            hypothesis=f"Claim variant test across {len(claims)} claims",
            variants=variants,
            control_variant_id="claim_0",
            independent_variables=["claim"],
            dependent_metrics=["acceptance_rate", "purchase_intent", "credibility"],
        )

    def create_sequential_design(
        self,
        name: str,
        prior_results: List[Dict],
        candidate_parameters: List[Dict],
        objective_metric: str = "acceptance_rate",
    ) -> ExperimentDesign:
        if not candidate_parameters:
            candidate_parameters = [{}]

        def score_candidate(candidate: Dict) -> float:
            if not prior_results:
                return 0.0
            scored = []
            for result in prior_results:
                params = result.get("parameters", {}) or {}
                overlap = sum(1 for key, value in candidate.items() if params.get(key) == value)
                try:
                    score = float(result.get(objective_metric, 0.0))
                except (TypeError, ValueError):
                    score = 0.0
                scored.append(score - overlap * 0.01)
            return max(scored) if scored else 0.0

        next_candidate = min(candidate_parameters, key=score_candidate)
        variants = [
            ExperimentVariant(
                variant_id=f"seq_{index}",
                name=f"Sequential {index + 1}",
                description=", ".join(f"{key}={value}" for key, value in candidate.items()),
                modifications=dict(candidate),
            )
            for index, candidate in enumerate(candidate_parameters)
        ]
        return ExperimentDesign(
            experiment_id=f"exp_{random.randint(10000, 99999)}",
            name=name,
            hypothesis=f"Sequential optimization for {objective_metric}",
            variants=variants,
            control_variant_id=variants[0].variant_id,
            independent_variables=sorted({key for candidate in candidate_parameters for key in candidate}),
            dependent_metrics=[objective_metric],
            metadata={
                "sequential": True,
                "objective_metric": objective_metric,
                "prior_result_count": len(prior_results),
                "next_candidate": dict(next_candidate),
            },
        )

    def assign_agents_to_variants(
        self,
        agent_ids: List[str],
        design: ExperimentDesign,
        seed: int = None,
    ) -> Dict[str, str]:
        rng = random.Random(seed)
        variant_ids = [variant.variant_id for variant in design.variants]
        return {agent_id: rng.choice(variant_ids) for agent_id in agent_ids}

    def assign_agents_stratified(
        self,
        agents: List[Dict],
        design: ExperimentDesign,
        stratify_key: str = "segment",
        seed: int = None,
    ) -> Dict[str, str]:
        rng = random.Random(seed)
        variant_ids = [variant.variant_id for variant in design.variants]
        assignment: Dict[str, str] = {}
        strata: Dict[str, List[Dict]] = {}
        for agent in agents:
            key = agent.get(stratify_key, "default")
            strata.setdefault(key, []).append(agent)
        for group in strata.values():
            rng.shuffle(group)
            for index, agent in enumerate(group):
                assignment[agent.get("agent_id", "")] = variant_ids[index % len(variant_ids)]
        return assignment

    def create_pack_variant(self, name: str, packs: List[dict]) -> ExperimentDesign:
        variants = [
            ExperimentVariant(
                f"pack_{index}",
                pack.get("name", f"Pack {index}"),
                pack.get("description", ""),
                pack,
            )
            for index, pack in enumerate(packs)
        ]
        return ExperimentDesign(
            experiment_id=f"exp_{random.randint(10000, 99999)}",
            name=name,
            hypothesis=f"Packaging variant test across {len(packs)} packs",
            variants=variants,
            control_variant_id="pack_0",
            independent_variables=["packaging"],
            dependent_metrics=["purchase_intent", "credibility", "appeal"],
        )

    def create_channel_variant(self, name: str, channels: List[str]) -> ExperimentDesign:
        variants = [
            ExperimentVariant(f"channel_{index}", channel, f"Channel: {channel}", {"channel": channel})
            for index, channel in enumerate(channels)
        ]
        return ExperimentDesign(
            experiment_id=f"exp_{random.randint(10000, 99999)}",
            name=name,
            hypothesis=f"Channel effectiveness test across {len(channels)} channels",
            variants=variants,
            control_variant_id="channel_0",
            independent_variables=["channel"],
            dependent_metrics=["reach", "engagement", "conversion"],
        )

    def create_factorial(self, name: str, factors: dict) -> ExperimentDesign:
        factor_names = list(factors.keys())
        combinations = list(itertools.product(*factors.values()))
        variants = []
        for index, combo in enumerate(combinations):
            description = ", ".join(f"{key}={value}" for key, value in zip(factor_names, combo))
            variants.append(
                ExperimentVariant(
                    f"factorial_{index}",
                    f"Combo {index}",
                    description,
                    dict(zip(factor_names, combo)),
                )
            )
        return ExperimentDesign(
            experiment_id=f"exp_{random.randint(10000, 99999)}",
            name=name,
            hypothesis=f"Factorial design with factors: {', '.join(factor_names)}",
            variants=variants,
            control_variant_id="factorial_0",
            independent_variables=factor_names,
            dependent_metrics=["purchase_intent", "credibility"],
        )
