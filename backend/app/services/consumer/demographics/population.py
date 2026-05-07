"""人群生成器 — 生成多样化的消费者群体"""

from .persona import ConsumerPersona
import random
import uuid

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
        """从模板生成消费者"""
        template = PERSONA_TEMPLATES[template_name]
        return ConsumerPersona(
            persona_id=str(uuid.uuid4())[:8],
            **template
        )

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
