"""人群生成器 — 生成多样化的消费者群体"""

from dataclasses import dataclass
from .persona import ConsumerPersona
import random
import uuid


@dataclass
class ShadowPersona:
    """影子Agent — 动态概率参与"""
    base_persona: ConsumerPersona
    activation_probability: float = 0.3  # 基础参与概率

    def should_activate(
        self,
        rng: random.Random,
        round_index: int = 0,
        agent_state: dict = None,
        social_pressure: float = 0.0,
    ) -> bool:
        """动态参与概率：基于轮次、Agent状态、社交压力调整。"""
        prob = self.activation_probability

        # 轮次效应：后期轮次参与度递减（疲劳）
        fatigue = max(0.0, 1.0 - round_index * 0.02)
        prob *= fatigue

        # 社交压力效应：高压下参与概率提升
        if social_pressure > 0.5:
            prob = min(1.0, prob * (1.0 + social_pressure))

        # Agent 状态效应：高关注度更易参与
        if agent_state:
            awareness = agent_state.get("awareness", 0.5)
            prob = min(1.0, prob * (0.5 + awareness))

        return rng.random() < max(0.01, min(1.0, prob))

# 预设人群模板
PERSONA_TEMPLATES = {
    "price_sensitive_student": {
        "name": "价格敏感学生",
        "age_range": (18, 24),
        "income_level": "low",
        "education": "college",
        "city_tier": 2,
        "price_sensitivity": 0.9,
        "brand_loyalty": 0.2,
        "innovation_adoption": 0.7,
        "social_influence_weight": 0.8,
        "daily_screen_hours": 6.0,
        "social_platforms": ["bilibili", "xiaohongshu", "douyin"],
        "shopping_frequency": "weekly",
        "risk_tolerance": 0.6,
        "conformity_tendency": 0.7,
    },
    "urban_professional": {
        "name": "城市白领",
        "age_range": (25, 35),
        "income_level": "high",
        "education": "graduate",
        "city_tier": 1,
        "price_sensitivity": 0.3,
        "brand_loyalty": 0.7,
        "innovation_adoption": 0.6,
        "social_influence_weight": 0.4,
        "daily_screen_hours": 5.0,
        "social_platforms": ["weixin", "zhihu", "xiaohongshu"],
        "shopping_frequency": "weekly",
        "risk_tolerance": 0.5,
        "conformity_tendency": 0.3,
    },
    "middle_aged_parent": {
        "name": "中年家长",
        "age_range": (35, 50),
        "income_level": "middle",
        "education": "college",
        "city_tier": 3,
        "price_sensitivity": 0.7,
        "brand_loyalty": 0.6,
        "innovation_adoption": 0.3,
        "social_influence_weight": 0.5,
        "daily_screen_hours": 3.0,
        "social_platforms": ["weixin", "douyin"],
        "shopping_frequency": "monthly",
        "risk_tolerance": 0.3,
        "conformity_tendency": 0.6,
    },
    "elderly_conservative": {
        "name": "保守老年人",
        "age_range": (55, 70),
        "income_level": "middle",
        "education": "high_school",
        "city_tier": 3,
        "price_sensitivity": 0.8,
        "brand_loyalty": 0.8,
        "innovation_adoption": 0.1,
        "social_influence_weight": 0.6,
        "daily_screen_hours": 2.0,
        "social_platforms": ["weixin"],
        "shopping_frequency": "monthly",
        "risk_tolerance": 0.2,
        "conformity_tendency": 0.7,
    },
}


class PopulationGenerator:
    """人群生成器"""

    def __init__(self, seed=None):
        self.rng = random.Random(seed)

    def generate_from_template(self, template_name: str) -> ConsumerPersona:
        """Template Pack 模式：从模板生成消费者"""
        template = PERSONA_TEMPLATES[template_name]
        return ConsumerPersona(
            persona_id=str(uuid.uuid4())[:8],
            source_basis="template",
            **template
        )

    def generate_from_brief(self, brief: dict, count: int) -> list:
        """Brief-driven Generation 模式：从简报生成消费者"""
        personas = []
        for i in range(count):
            persona = ConsumerPersona(
                persona_id=str(uuid.uuid4())[:8],
                name=f"Brief Agent {i+1}",
                source_basis="brief",
                age_range=brief.get("target_age", (18, 65)),
                gender=brief.get("target_gender", "any"),
                income_level=brief.get("target_income", "middle"),
                education=brief.get("target_education", "college"),
                city_tier=brief.get("target_city_tier", 2),
                region=brief.get("target_region", "east"),
                family_structure=brief.get("target_family_structure", "single"),
                occupation=brief.get("target_occupation", "white_collar"),
                price_sensitivity=brief.get("price_sensitivity", 0.5),
                brand_loyalty=brief.get("brand_loyalty", 0.5),
                innovation_adoption=brief.get("innovation_adoption", 0.5),
                social_influence_weight=brief.get("social_influence_weight", 0.5),
                purchase_channel=brief.get("purchase_channel", "online"),
                category_usage_frequency=brief.get("category_usage_frequency", "weekly"),
                claim_skepticism=brief.get("claim_skepticism", 0.5),
                evidence_sensitivity=brief.get("evidence_sensitivity", 0.5),
                novelty_seeking=brief.get("novelty_seeking", 0.5),
                risk_aversion=brief.get("risk_aversion", 0.5),
                risk_tolerance=brief.get("risk_tolerance", 0.5),
                conformity_tendency=brief.get("conformity_tendency", 0.5),
                sharing_propensity=brief.get("sharing_propensity", 0.5),
                expression_style=brief.get("expression_style", "moderate"),
                channel_preference=brief.get("channel_preference", "weixin"),
                category_pain_points=brief.get("category_pain_points", []),
                decision_heuristics=brief.get("decision_heuristics", []),
                forbidden_assumptions=brief.get("forbidden_assumptions", []),
                quality_score=brief.get("quality_score", 0.6),
            )
            # Add random perturbation for diversity
            persona.price_sensitivity = max(0, min(1, persona.price_sensitivity + self.rng.gauss(0, 0.05)))
            persona.brand_loyalty = max(0, min(1, persona.brand_loyalty + self.rng.gauss(0, 0.05)))
            personas.append(persona)
        return personas

    def generate_calibrated(self, calibration_data: dict, count: int) -> list:
        """Data-calibrated Population 模式：从校准数据生成消费者"""
        personas = []
        for i in range(count):
            sampled = self._sample_from_calibration(calibration_data)
            persona = ConsumerPersona(
                persona_id=str(uuid.uuid4())[:8],
                name=f"Calibrated Agent {i+1}",
                source_basis="data_calibrated",
                **sampled,
            )
            personas.append(persona)
        return personas

    def _sample_from_calibration(self, calibration_data: dict) -> dict:
        """从校准数据中采样一个消费者参数集"""
        result = {}
        # Sample age_range from distribution
        if "age_ranges" in calibration_data:
            ages = calibration_data["age_ranges"]
            result["age_range"] = tuple(self.rng.choice(ages)) if ages else (18, 65)
        # Sample categorical fields from weighted distributions
        for field_name in ["income_level", "education", "region", "family_structure",
                           "occupation", "purchase_channel", "expression_style"]:
            dist_key = f"{field_name}_distribution"
            if dist_key in calibration_data:
                dist = calibration_data[dist_key]
                if isinstance(dist, dict) and dist:
                    choices = list(dist.keys())
                    weights = list(dist.values())
                    result[field_name] = self.rng.choices(choices, weights=weights, k=1)[0]
        # Sample numeric fields from (mean, std) pairs
        for field_name in ["price_sensitivity", "brand_loyalty", "innovation_adoption",
                           "social_influence_weight", "claim_skepticism", "evidence_sensitivity",
                           "novelty_seeking", "risk_aversion", "risk_tolerance",
                           "conformity_tendency", "sharing_propensity"]:
            if field_name in calibration_data:
                mean, std = calibration_data[field_name]
                result[field_name] = max(0, min(1, self.rng.gauss(mean, std)))
        # Sample city_tier
        if "city_tier_distribution" in calibration_data:
            dist = calibration_data["city_tier_distribution"]
            if isinstance(dist, dict) and dist:
                choices = [int(k) for k in dist.keys()]
                weights = list(dist.values())
                result["city_tier"] = self.rng.choices(choices, weights=weights, k=1)[0]
        return result

    def generate_diverse_population(self, n: int) -> list:
        """生成多样化人群（自动分配模板比例）"""
        templates = list(PERSONA_TEMPLATES.keys())
        population = []
        for i in range(n):
            template = templates[i % len(templates)]
            persona = self.generate_from_template(template)
            # 添加随机扰动
            persona.price_sensitivity = max(0, min(1, persona.price_sensitivity + self.rng.gauss(0, 0.1)))
            persona.brand_loyalty = max(0, min(1, persona.brand_loyalty + self.rng.gauss(0, 0.1)))
            population.append(persona)
        return population

    def generate_shadow_population(self, n: int, activation_probability: float = 0.3) -> list:
        """生成影子Agent人群 — 概率参与的低活跃度Agent"""
        templates = list(PERSONA_TEMPLATES.keys())
        shadows = []
        for i in range(n):
            template = templates[i % len(templates)]
            persona = self.generate_from_template(template)
            persona.price_sensitivity = max(0, min(1, persona.price_sensitivity + self.rng.gauss(0, 0.1)))
            persona.brand_loyalty = max(0, min(1, persona.brand_loyalty + self.rng.gauss(0, 0.1)))
            shadow = ShadowPersona(
                base_persona=persona,
                activation_probability=activation_probability,
            )
            shadows.append(shadow)
        return shadows

    def get_population_stats(self, population: list) -> dict:
        """生成人群统计报表"""
        if not population:
            return {"total": 0}

        # 支持 ConsumerPersona 和 ShadowPersona（取 base_persona）
        personas = []
        for p in population:
            if isinstance(p, ShadowPersona):
                personas.append(p.base_persona)
            else:
                personas.append(p)

        total = len(personas)
        template_counts: dict = {}
        for p in personas:
            template_counts[p.name] = template_counts.get(p.name, 0) + 1

        # Population coverage statistics
        source_basis_distribution: dict = {}
        for p in personas:
            basis = p.source_basis
            source_basis_distribution[basis] = source_basis_distribution.get(basis, 0) + 1

        return {
            "total": total,
            "avg_price_sensitivity": sum(p.price_sensitivity for p in personas) / total,
            "avg_brand_loyalty": sum(p.brand_loyalty for p in personas) / total,
            "city_tier_distribution": {t: sum(1 for p in personas if p.city_tier == t) for t in range(1, 6)},
            "income_distribution": {l: sum(1 for p in personas if p.income_level == l) for l in ["low", "middle", "high"]},
            "template_distribution": template_counts,
            "population_coverage": {
                "age_coverage": len(set(p.age_range for p in personas)),
                "income_coverage": len(set(p.income_level for p in personas)),
                "city_tier_coverage": len(set(p.city_tier for p in personas)),
                "source_basis_distribution": source_basis_distribution,
            },
        }
