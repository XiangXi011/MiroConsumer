"""Rule-first consumer profile generator with MiroFish profile enrichment."""

from __future__ import annotations

import copy
import random
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Mapping, Sequence

from .mirofish_profile_adapter import CHANNEL_LABELS, MiroFishProfileAdapter


PROFILE_VERSION = "phase7g_v1"
ALLOWED_SOURCES = {"mirofish_adapter", "rule_fallback", "hybrid"}
ENGLISH_DEFAULT_LABELS = {
    "Care-driven urban mom",
    "Social proof explorer",
    "Traditional value caretaker",
    "Busy urban filterer",
    "Ingredient-first analyst",
    "Feature-seeking livestream buyer",
    "Evidence-maximizing planner",
    "Budget-safe minimalist",
}


@dataclass
class ConsumerProfile:
    persona_id: str
    name: str
    age_range: str
    city_tier: str
    income_level: str
    family_structure: str
    purchase_channel: List[str]
    category_usage_frequency: str
    price_sensitivity: float
    evidence_sensitivity: float
    risk_sensitivities: List[str]
    expression_style: str
    bio: str
    persona: str
    age: int
    gender: str = "unknown"
    mbti: str = "ISFJ"
    country: str = "China"
    profession: str = "消费者"
    interested_topics: List[str] = field(default_factory=list)
    source: str = "rule_fallback"
    zep_context_status: str = "unavailable"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ConsumerProfileSnapshot:
    product_category: str
    task_type: str
    profiles: List[Dict[str, Any]]
    profile_version: str = PROFILE_VERSION
    generator_mode: str = "rule_first"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class CategoryRuleProfileBuilder:
    """Build stable Chinese consumer profile blueprints from BusinessBrief."""

    CATEGORY_RULES: Dict[str, Dict[str, Any]] = {
        "kitchenware": {
            "names": ["一线城市精致妈妈", "价格比较型宝妈", "成分证据型家庭主理人", "直播尝鲜型年轻家庭"],
            "risks": ["材质安全", "营销夸大", "孩子是否愿意用", "价格虚高"],
            "drivers": ["安全材质", "易清洗", "家庭场景", "耐用"],
            "frequency": "每周多次",
        },
        "mother_baby": {
            "names": ["新手妈妈", "成分谨慎型妈妈", "妈妈群意见领袖", "高敏感安全守门人"],
            "risks": ["过敏", "功效夸大", "宝宝是否适用", "安全背书不足"],
            "drivers": ["温和安全", "专业背书", "真实口碑", "使用便利"],
            "frequency": "每天",
        },
        "food_beverage": {
            "names": ["控糖成分党", "口味优先尝鲜者", "健身营养型消费者", "价格敏感囤货者"],
            "risks": ["口味", "配料", "糖分", "热量"],
            "drivers": ["健康", "好喝", "低负担", "性价比"],
            "frequency": "每周多次",
        },
        "oral_care": {
            "names": ["功效怀疑型白领", "口腔护理成分党", "家庭囤货决策者", "社媒种草尝鲜者"],
            "risks": ["功效证据", "刺激性", "医生背书", "价格比较"],
            "drivers": ["专业感", "温和", "清洁效果", "口碑"],
            "frequency": "每天",
        },
        "beauty_personal_care": {
            "names": ["成分功效党", "敏感肌谨慎用户", "小红书种草用户", "价格比较型护理用户"],
            "risks": ["成分刺激", "功效夸大", "肤质不匹配", "价格虚高"],
            "drivers": ["成分", "肤感", "真实测评", "品牌信任"],
            "frequency": "每周多次",
        },
        "generic": {
            "names": ["理性比较型消费者", "社交种草型消费者", "价格敏感型消费者", "证据敏感型消费者"],
            "risks": ["可信度", "价格", "使用效果", "口碑不足"],
            "drivers": ["清晰卖点", "真实证据", "口碑", "性价比"],
            "frequency": "按需购买",
        },
    }

    TASK_RULES = {
        "price_test": {"price_delta": 0.18, "evidence_delta": 0.02},
        "copy_feedback": {"price_delta": 0.02, "evidence_delta": 0.08},
        "ab_test": {"price_delta": 0.06, "evidence_delta": 0.06},
        "concept_test": {"price_delta": 0.04, "evidence_delta": 0.1},
    }

    def __init__(self, seed: int = 0) -> None:
        self.seed = int(seed or 0)

    def build(
        self,
        brief: Mapping[str, Any],
        enabled_channels: Sequence[str] | None = None,
        count: int = 8,
    ) -> List[Dict[str, Any]]:
        category = normalize_category(brief.get("product_category") or brief.get("category"))
        task_type = str(brief.get("task_type") or "concept_test")
        rules = self.CATEGORY_RULES.get(category, self.CATEGORY_RULES["generic"])
        task = self.TASK_RULES.get(task_type, self.TASK_RULES["concept_test"])
        price_band = _price_band(brief.get("price_context") or brief.get("price_points"))
        channel_labels = _channel_labels(enabled_channels)
        rng = random.Random(f"{self.seed}:{category}:{task_type}:{price_band}:{channel_labels}")
        blueprints: List[Dict[str, Any]] = []
        for index in range(count):
            base_name = rules["names"][index % len(rules["names"])]
            channel_pair = _rotate_channels(channel_labels, index)
            price = _clamp(0.35 + task["price_delta"] + _price_delta(price_band) + rng.uniform(-0.08, 0.08))
            evidence = _clamp(0.55 + task["evidence_delta"] + rng.uniform(-0.08, 0.08))
            risks = list(dict.fromkeys(list(rules["risks"][:2]) + _as_text_list(brief.get("risk_flags"))))[:4]
            if not risks:
                risks = list(rules["risks"][:2])
            blueprints.append(
                {
                    "persona_id": f"M{index + 1:02d}",
                    "name": base_name,
                    "age_range": _age_range_for(index, category),
                    "city_tier": _city_tier_for(index),
                    "income_level": _income_for(index, price_band),
                    "family_structure": _family_for(index, category),
                    "purchase_channel": channel_pair,
                    "category_usage_frequency": rules["frequency"],
                    "price_sensitivity": price,
                    "evidence_sensitivity": evidence,
                    "risk_sensitivities": risks,
                    "expression_style": _expression_for(index),
                }
            )
        return blueprints


class ProfileValidator:
    """Validate and repair consumer profile schema."""

    def validate(self, profile: Mapping[str, Any], research_goal: str = "") -> Dict[str, Any]:
        data = dict(profile)
        for label in ENGLISH_DEFAULT_LABELS:
            for field_name in ("name", "bio", "persona"):
                data[field_name] = str(data.get(field_name) or "").replace(label, "").strip()
        if not data.get("name"):
            data["name"] = "中文消费者画像"
        if not data.get("bio"):
            data["bio"] = f"{data['name']}关注产品证据、价格和真实体验。"
        if research_goal:
            data["bio"] = str(data["bio"]).replace(research_goal, "").strip()
        if not data.get("persona"):
            data["persona"] = f"{data['name']}会结合家庭场景、证据和价格判断是否购买。"
        data["bio"] = str(data["bio"])[:299]
        data["source"] = data.get("source") if data.get("source") in ALLOWED_SOURCES else "rule_fallback"
        data["purchase_channel"] = _as_text_list(data.get("purchase_channel")) or ["小红书"]
        data["risk_sensitivities"] = _as_text_list(data.get("risk_sensitivities")) or ["可信度"]
        data["interested_topics"] = _as_text_list(data.get("interested_topics")) or list(data["risk_sensitivities"])
        data["price_sensitivity"] = _clamp(data.get("price_sensitivity", 0.5))
        data["evidence_sensitivity"] = _clamp(data.get("evidence_sensitivity", 0.5))
        data.setdefault("profile_source", "rule")
        data.setdefault("supporting_evidence_ids", [])
        if "unsupported_fields" not in data:
            data["unsupported_fields"] = ["evidence_enrichment"] if data.get("profile_source") == "rule" else []
        data.setdefault("research_findings", [])
        defaults = {
            "persona_id": "M01",
            "age_range": "28-35",
            "city_tier": "一线/新一线",
            "income_level": "中等",
            "family_structure": "家庭自用",
            "category_usage_frequency": "按需购买",
            "expression_style": "理性直接",
            "age": 32,
            "gender": "unknown",
            "mbti": "ISFJ",
            "country": "China",
            "profession": "消费者",
            "zep_context_status": "unavailable",
        }
        for key, value in defaults.items():
            data.setdefault(key, value)
        return data


class ConsumerProfileGenerator:
    """Rule-first profile generator with optional MiroFish adapter enrichment."""

    def __init__(
        self,
        seed: int = 0,
        enable_llm_enrichment: bool = False,
        adapter: MiroFishProfileAdapter | None = None,
    ) -> None:
        self.seed = int(seed or 0)
        self.builder = CategoryRuleProfileBuilder(seed=self.seed)
        self.adapter = adapter or MiroFishProfileAdapter(
            seed=self.seed,
            enable_llm_enrichment=enable_llm_enrichment,
        )
        self.validator = ProfileValidator()

    def generate_profiles(
        self,
        *,
        brief: Mapping[str, Any],
        enabled_channels: Sequence[str] | None = None,
        count: int = 8,
        research_findings: Sequence[Any] | None = None,
        graph_id: str | None = None,
    ) -> List[Dict[str, Any]]:
        blueprints = self.builder.build(brief, enabled_channels=enabled_channels, count=count)
        rule_first = [copy.deepcopy(item) for item in blueprints]
        enriched = self.adapter.generate_profiles(
            brief=brief,
            blueprints=blueprints,
            enabled_channels=enabled_channels,
            research_findings=research_findings,
            graph_id=graph_id,
        )
        validated: List[Dict[str, Any]] = []
        research_goal = str(brief.get("research_goal") or "")
        for original, profile in zip(rule_first, enriched):
            data = dict(profile)
            # Enrichment cannot overwrite rule-first fields.
            for key in (
                "age_range",
                "city_tier",
                "income_level",
                "family_structure",
                "purchase_channel",
                "category_usage_frequency",
                "price_sensitivity",
                "evidence_sensitivity",
                "risk_sensitivities",
            ):
                data[key] = original[key]
            data["source"] = "hybrid" if data.get("source") == "rule_fallback" else data.get("source", "hybrid")
            validated.append(self.validator.validate(data, research_goal=research_goal))
        return validated

    def build_snapshot(
        self,
        *,
        brief: Mapping[str, Any],
        enabled_channels: Sequence[str] | None = None,
        count: int = 8,
        research_findings: Sequence[Any] | None = None,
        graph_id: str | None = None,
    ) -> Dict[str, Any]:
        category = normalize_category(brief.get("product_category") or brief.get("category"))
        task_type = str(brief.get("task_type") or "concept_test")
        profiles = self.generate_profiles(
            brief=brief,
            enabled_channels=enabled_channels,
            count=count,
            research_findings=research_findings,
            graph_id=graph_id,
        )
        return ConsumerProfileSnapshot(
            product_category=f"{category}_zh" if not category.endswith("_zh") else category,
            task_type=task_type,
            profiles=profiles,
        ).to_dict()


def normalize_category(value: Any) -> str:
    text = str(value or "generic").strip().lower().replace("_zh", "")
    aliases = {
        "kitchen": "kitchenware",
        "kitchenware": "kitchenware",
        "餐厨": "kitchenware",
        "mother_baby": "mother_baby",
        "mom_baby": "mother_baby",
        "母婴": "mother_baby",
        "food": "food_beverage",
        "food_beverage": "food_beverage",
        "食品饮料": "food_beverage",
        "oral": "oral_care",
        "oral_care": "oral_care",
        "口腔护理": "oral_care",
        "beauty": "beauty_personal_care",
        "beauty_personal_care": "beauty_personal_care",
        "美妆个护": "beauty_personal_care",
    }
    return aliases.get(text, "generic")


def _channel_labels(enabled_channels: Sequence[str] | None) -> List[str]:
    labels = [CHANNEL_LABELS.get(str(channel), str(channel)) for channel in (enabled_channels or [])]
    return labels or ["小红书", "天猫", "抖音"]


def _rotate_channels(channels: Sequence[str], index: int) -> List[str]:
    if not channels:
        return ["小红书"]
    first = channels[index % len(channels)]
    second = channels[(index + 1) % len(channels)] if len(channels) > 1 else first
    return list(dict.fromkeys([first, second]))


def _price_band(value: Any) -> str:
    if isinstance(value, Mapping):
        return str(value.get("price_band") or value.get("band") or "mid").lower()
    return "mid"


def _price_delta(price_band: str) -> float:
    if price_band in {"premium", "mid_premium", "high"}:
        return 0.12
    if price_band in {"low", "budget"}:
        return 0.18
    return 0.04


def _age_range_for(index: int, category: str) -> str:
    if category == "mother_baby":
        return ["25-32", "28-35", "30-39", "24-30"][index % 4]
    return ["28-35", "30-39", "24-30", "35-45"][index % 4]


def _city_tier_for(index: int) -> str:
    return ["一线/新一线", "二线", "三线", "一线/新一线"][index % 4]


def _income_for(index: int, price_band: str) -> str:
    if price_band in {"premium", "mid_premium", "high"}:
        return ["中高", "中等", "中高", "高"][index % 4]
    return ["中等", "中低", "中等", "中高"][index % 4]


def _family_for(index: int, category: str) -> str:
    if category in {"mother_baby", "kitchenware"}:
        return ["有1个3-8岁孩子", "两代同住", "有低龄孩子", "年轻小家庭"][index % 4]
    return ["单身/情侣", "年轻小家庭", "家庭自用", "朋友聚会场景"][index % 4]


def _expression_for(index: int) -> str:
    return ["谨慎但愿意尝新", "直接比较", "重视证据", "冲动尝鲜"][index % 4]


def _as_text_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    return [str(value)]


def _clamp(value: Any) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = 0.5
    return round(max(0.0, min(1.0, numeric)), 4)


__all__ = [
    "CategoryRuleProfileBuilder",
    "ConsumerProfile",
    "ConsumerProfileGenerator",
    "ConsumerProfileSnapshot",
    "PROFILE_VERSION",
    "ProfileValidator",
    "normalize_category",
]
