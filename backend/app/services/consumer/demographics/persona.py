"""消费者人群画像模型"""
from dataclasses import dataclass, field
from typing import Optional
import random


@dataclass
class ConsumerPersona:
    """消费者画像"""
    persona_id: str
    name: str

    # 人口统计学
    age_range: tuple = (18, 65)
    gender: str = "any"  # male/female/any
    income_level: str = "middle"  # low/middle/high
    education: str = "college"  # high_school/college/graduate
    city_tier: int = 2  # 1-5线城市
    region: str = "east"  # east/south/west/north/central
    family_structure: str = "single"  # single/couple/family/empty_nest
    occupation: str = "white_collar"  # white_collar/blue_collar/student/retired/freelance

    # 消费特征
    price_sensitivity: float = 0.5  # 0-1, 越高越敏感
    brand_loyalty: float = 0.5  # 0-1
    innovation_adoption: float = 0.5  # 0-1, 越高越愿意尝试新品
    social_influence_weight: float = 0.5  # 0-1, 受社交影响程度
    purchase_channel: str = "online"  # online/offline/omni
    category_usage_frequency: str = "weekly"  # daily/weekly/monthly/rarely

    # 心理特征
    claim_skepticism: float = 0.5  # 对宣传的怀疑度
    evidence_sensitivity: float = 0.5  # 对证据的敏感度
    novelty_seeking: float = 0.5  # 追新倾向
    risk_aversion: float = 0.5  # 风险规避
    risk_tolerance: float = 0.5
    conformity_tendency: float = 0.5  # 从众倾向

    # 行为特征
    sharing_propensity: float = 0.5  # 分享倾向
    social_platforms: list = field(default_factory=lambda: ["weixin", "douyin"])
    daily_screen_hours: float = 4.0
    shopping_frequency: str = "weekly"  # daily/weekly/monthly

    # 表达风格
    expression_style: str = "moderate"  # conservative/moderate/outspoken
    channel_preference: str = "weixin"

    # 痛点和启发
    category_pain_points: list = field(default_factory=list)
    decision_heuristics: list = field(default_factory=list)
    forbidden_assumptions: list = field(default_factory=list)

    # 来源和质量
    source_basis: str = "template"  # template/brief/data_calibrated/manual
    quality_score: float = 0.5  # 画像质量评分

    def to_prompt_description(self) -> str:
        """生成用于LLM prompt的人物描述"""
        return (
            f"这是一位{self.age_range[0]}-{self.age_range[1]}岁的{self.income_level}收入{self.occupation}消费者，"
            f"居住在{self.city_tier}线城市{self.region}地区，{self.education}学历，{self.family_structure}家庭。"
            f"价格敏感度{self.price_sensitivity:.0%}，品牌忠诚度{self.brand_loyalty:.0%}，"
            f"怀疑度{self.claim_skepticism:.0%}，证据敏感度{self.evidence_sensitivity:.0%}。"
            f"表达风格: {self.expression_style}，渠道偏好: {self.channel_preference}。"
        )
