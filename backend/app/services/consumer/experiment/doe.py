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
