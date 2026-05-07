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
    age_range: tuple = (18, 65)  # 年龄范围
    income_level: str = "middle"  # low/middle/high
    education: str = "college"  # high_school/college/graduate
    city_tier: int = 2  # 1-5线城市

    # 消费特征
    price_sensitivity: float = 0.5  # 0-1, 越高越敏感
    brand_loyalty: float = 0.5  # 0-1
    innovation_adoption: float = 0.5  # 0-1, 越高越愿意尝试新品
    social_influence_weight: float = 0.5  # 0-1, 受社交影响程度

    # 数字行为
    daily_screen_hours: float = 4.0
    social_platforms: list = field(default_factory=lambda: ["weixin", "douyin"])
    shopping_frequency: str = "weekly"  # daily/weekly/monthly

    # 心理特征
    risk_tolerance: float = 0.5  # 0-1
    conformity_tendency: float = 0.5  # 0-1, 从众倾向

    def to_prompt_description(self) -> str:
        """生成用于LLM prompt的人物描述"""
        return (
            f"这是一位{self.age_range[0]}-{self.age_range[1]}岁的{self.income_level}收入消费者，"
            f"居住在{self.city_tier}线城市，{self.education}学历。"
            f"价格敏感度{self.price_sensitivity:.0%}，品牌忠诚度{self.brand_loyalty:.0%}，"
            f"愿意尝试新品的程度{self.innovation_adoption:.0%}。"
            f"每天使用手机{self.daily_screen_hours}小时，"
            f"常用平台：{'、'.join(self.social_platforms)}。"
        )
