"""实验设计 DOE"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import random


@dataclass
class ExperimentVariant:
    variant_id: str
    name: str
    description: str
    modifications: Dict  # 对 BusinessBrief 的修改


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
    stratify_by: List[str] = field(default_factory=list)  # age/income/city_tier
    control_variables: Dict = field(default_factory=dict)


class ExperimentDesigner:
    """实验设计器"""

    def create_ab_test(
        self,
        name: str,
        hypothesis: str,
        control_config: Dict,
        treatment_config: Dict,
    ) -> ExperimentDesign:
        """创建 A/B 测试"""
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
        """创建价格阶梯实验"""
        variants = []
        for i, price in enumerate(prices):
            vid = f"price_{i}"
            variants.append(
                ExperimentVariant(vid, f"Price {price}", f"Price point {price}", {"price": price})
            )

        return ExperimentDesign(
            experiment_id=f"exp_{random.randint(10000, 99999)}",
            name=name,
            hypothesis=f"Price sensitivity test across {len(prices)} price points",
            variants=variants,
            control_variant_id="price_0",
            independent_variables=["price"],
            dependent_metrics=["purchase_intent", "price_perception", "value_score"],
        )

    def create_message_variant(
        self, name: str, messages: List[str],
    ) -> ExperimentDesign:
        """创建消息变体实验"""
        variants = []
        for i, msg in enumerate(messages):
            vid = f"msg_{i}"
            variants.append(
                ExperimentVariant(vid, f"Message {i}", msg, {"message": msg})
            )
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

    def create_claim_variant(
        self, name: str, claims: List[str],
    ) -> ExperimentDesign:
        """创建 claim 变体实验"""
        variants = []
        for i, claim in enumerate(claims):
            vid = f"claim_{i}"
            variants.append(
                ExperimentVariant(vid, f"Claim {i}", claim, {"claim": claim})
            )
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

    def assign_agents_to_variants(
        self,
        agent_ids: List[str],
        design: ExperimentDesign,
        seed: int = None,
    ) -> Dict[str, str]:
        """随机分配 Agent 到实验组"""
        rng = random.Random(seed)
        assignment = {}
        variant_ids = [v.variant_id for v in design.variants]
        for agent_id in agent_ids:
            assignment[agent_id] = rng.choice(variant_ids)
        return assignment

    def assign_agents_stratified(
        self,
        agents: List[Dict],
        design: ExperimentDesign,
        stratify_key: str = "segment",
        seed: int = None,
    ) -> Dict[str, str]:
        """分层分配 Agent 到实验组（按 persona 属性分层）"""
        rng = random.Random(seed)
        variant_ids = [v.variant_id for v in design.variants]
        assignment: Dict[str, str] = {}

        # Group agents by stratify key
        strata: Dict[str, List[Dict]] = {}
        for agent in agents:
            agent_id = agent.get("agent_id", "")
            key = agent.get(stratify_key, "default")
            strata.setdefault(key, []).append(agent)

        # Within each stratum, assign round-robin (shuffled)
        for _key, group in strata.items():
            rng.shuffle(group)
            for i, agent in enumerate(group):
                agent_id = agent.get("agent_id", "")
                assignment[agent_id] = variant_ids[i % len(variant_ids)]

        return assignment
