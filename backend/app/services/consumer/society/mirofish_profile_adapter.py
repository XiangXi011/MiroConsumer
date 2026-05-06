"""MiroFish native profile capability adapter for consumer society profiles."""

from __future__ import annotations

import csv
import json
import random
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence

from ....services.oasis_profile_generator import OasisAgentProfile


CHANNEL_LABELS = {
    "xiaohongshu": "小红书",
    "douyin": "抖音",
    "tmall": "天猫",
    "ecommerce_review": "电商评论区",
    "wechat_group": "宝妈群",
    "offline_supermarket": "线下商超",
    "livestream": "直播间",
    "zhihu": "知乎",
}


class MiroFishProfileAdapter:
    """Adapt MiroFish/OASIS rich profile ideas into consumer profiles.

    The adapter intentionally does not start or depend on the OASIS runtime.
    It reuses the rich profile field contract and export shape while keeping
    MiroConsumer's BusinessBrief-driven semantics.
    """

    def __init__(
        self,
        seed: int = 0,
        enable_llm_enrichment: bool = False,
        llm_client: Any | None = None,
    ) -> None:
        self.seed = int(seed or 0)
        self.enable_llm_enrichment = enable_llm_enrichment
        self.llm_client = llm_client

    def build_entity_context(
        self,
        brief: Mapping[str, Any],
        enabled_channels: Sequence[str] | None = None,
        research_findings: Iterable[Any] | None = None,
    ) -> Dict[str, Any]:
        return {
            "product_category": brief.get("product_category") or brief.get("category") or "generic",
            "target_consumer": brief.get("target_consumer") or brief.get("target_segments") or "",
            "price_context": brief.get("price_context") or brief.get("price_points") or {},
            "claims": list(_as_list(brief.get("claims"))),
            "risk_flags": list(_as_list(brief.get("risk_flags") or brief.get("anxieties"))),
            "enabled_channels": list(enabled_channels or []),
            "research_findings": [_finding_summary(item) for item in list(research_findings or [])],
        }

    def generate_profiles(
        self,
        *,
        brief: Mapping[str, Any],
        blueprints: Sequence[Mapping[str, Any]],
        enabled_channels: Sequence[str] | None = None,
        research_findings: Iterable[Any] | None = None,
        graph_id: str | None = None,
    ) -> List[Dict[str, Any]]:
        context = self.build_entity_context(brief, enabled_channels, research_findings)
        zep_status = "available" if graph_id else "unavailable"
        profiles: List[Dict[str, Any]] = []
        for index, blueprint in enumerate(blueprints):
            profile = dict(blueprint)
            profile.setdefault("persona_id", f"M{index + 1:02d}")
            profile.setdefault("name", f"消费者{index + 1:02d}")
            rich = self._rule_rich_profile(profile, context, index)
            if self.enable_llm_enrichment and self.llm_client is not None:
                rich = self._merge_llm_enrichment(rich, profile, context)
            profile.update(rich)
            profile["zep_context_status"] = zep_status
            profile["source"] = "hybrid" if zep_status == "available" else "rule_fallback"
            profiles.append(profile)
        return profiles

    def export_oasis_profiles(
        self,
        profiles: Sequence[Mapping[str, Any]],
        export_dir: str | Path,
    ) -> Dict[str, str]:
        export_path = Path(export_dir)
        export_path.mkdir(parents=True, exist_ok=True)
        reddit_path = export_path / "reddit_profiles.json"
        twitter_path = export_path / "twitter_profiles.csv"

        oasis_profiles = [
            self._to_oasis_profile(profile, index).to_dict()
            for index, profile in enumerate(profiles)
        ]
        reddit_payload = [
            self._to_oasis_profile(profile, index).to_reddit_format()
            for index, profile in enumerate(profiles)
        ]
        reddit_path.write_text(
            json.dumps(reddit_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        fieldnames = [
            "user_id",
            "user_name",
            "name",
            "bio",
            "persona",
            "friend_count",
            "follower_count",
            "statuses_count",
            "age",
            "gender",
            "mbti",
            "country",
            "profession",
            "interested_topics",
        ]
        with twitter_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for item in oasis_profiles:
                row = {key: item.get(key, "") for key in fieldnames}
                row["interested_topics"] = "|".join(item.get("interested_topics") or [])
                writer.writerow(row)

        return {
            "reddit_profiles_path": str(reddit_path),
            "twitter_profiles_path": str(twitter_path),
        }

    def _rule_rich_profile(
        self,
        profile: Mapping[str, Any],
        context: Mapping[str, Any],
        index: int,
    ) -> Dict[str, Any]:
        rng = random.Random(f"{self.seed}:{profile.get('persona_id')}:{index}")
        age_range = str(profile.get("age_range") or "28-35")
        age = _age_from_range(age_range, rng)
        name = str(profile.get("name") or f"消费者{index + 1:02d}")
        channels = list(profile.get("purchase_channel") or [])
        risks = list(profile.get("risk_sensitivities") or context.get("risk_flags") or [])
        claims = list(context.get("claims") or [])
        claim_text = "、".join(claims[:2]) if claims else "核心卖点"
        channel_text = "、".join(channels[:2]) if channels else "常用渠道"
        risk_text = "、".join(risks[:2]) if risks else "可信度"
        bio = (
            f"{name}关注{claim_text}，常在{channel_text}比较信息，"
            f"会重点核对{risk_text}。"
        )
        persona = (
            f"{name}是一类{profile.get('city_tier', '城市')}消费者，"
            f"{profile.get('expression_style', '表达直接')}，购买前会结合证据和价格判断。"
        )
        topics = list(dict.fromkeys(claims + risks + channels))[:8]
        if not topics:
            topics = ["产品体验", "价格", "口碑"]
        return {
            "bio": bio[:299],
            "persona": persona[:299],
            "age": age,
            "gender": "female" if "妈" in name or "母婴" in str(context.get("product_category")) else "unknown",
            "mbti": _pick_mbti(rng),
            "country": "China",
            "profession": _profession_for(profile),
            "interested_topics": topics,
        }

    def _merge_llm_enrichment(
        self,
        rich: Mapping[str, Any],
        profile: Mapping[str, Any],
        context: Mapping[str, Any],
    ) -> Dict[str, Any]:
        try:
            payload = self.llm_client.chat_json(
                messages=[
                    {
                        "role": "system",
                        "content": "Return JSON for Chinese consumer profile enrichment only.",
                    },
                    {
                        "role": "user",
                        "content": json.dumps(
                            {"profile": dict(profile), "context": dict(context)},
                            ensure_ascii=False,
                        ),
                    },
                ],
                temperature=0.2,
                max_tokens=500,
            )
        except Exception:
            return dict(rich)

        enriched = dict(rich)
        for key in ("bio", "persona", "expression_style", "interested_topics"):
            if key in payload and payload[key]:
                enriched[key] = payload[key]
        return enriched

    def _to_oasis_profile(self, profile: Mapping[str, Any], index: int) -> OasisAgentProfile:
        user_id = index + 1
        user_name = str(profile.get("persona_id") or f"M{user_id:02d}")
        topics = profile.get("interested_topics") or []
        if not isinstance(topics, list):
            topics = [str(topics)]
        return OasisAgentProfile(
            user_id=user_id,
            user_name=user_name,
            name=str(profile.get("name") or user_name),
            bio=str(profile.get("bio") or ""),
            persona=str(profile.get("persona") or profile.get("bio") or ""),
            age=int(profile.get("age") or _age_from_range(str(profile.get("age_range") or "30-39"))),
            gender=str(profile.get("gender") or "unknown"),
            mbti=str(profile.get("mbti") or "ISFJ"),
            country=str(profile.get("country") or "China"),
            profession=str(profile.get("profession") or "消费者"),
            interested_topics=[str(item) for item in topics],
            source_entity_uuid=str(profile.get("persona_id") or user_name),
            source_entity_type="consumer_profile",
        )


def _as_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _finding_summary(item: Any) -> str:
    if isinstance(item, Mapping):
        return str(item.get("summary") or item.get("claim") or item.get("finding_id") or "")
    return str(getattr(item, "summary", "") or getattr(item, "claim", "") or item)


def _age_from_range(age_range: str, rng: random.Random | None = None) -> int:
    rng = rng or random.Random(0)
    parts = [part for part in age_range.replace("岁", "").split("-") if part.strip().isdigit()]
    if len(parts) >= 2:
        return rng.randint(int(parts[0]), int(parts[1]))
    if len(parts) == 1:
        return int(parts[0])
    return rng.randint(28, 42)


def _pick_mbti(rng: random.Random) -> str:
    return ["ISFJ", "ESFJ", "INFJ", "ENFJ", "ISTJ", "ENFP"][rng.randrange(6)]


def _profession_for(profile: Mapping[str, Any]) -> str:
    text = f"{profile.get('name', '')}{profile.get('family_structure', '')}"
    if "妈" in text or "孩子" in text:
        return "家庭消费决策者"
    if float(profile.get("price_sensitivity") or 0.5) >= 0.7:
        return "价格比较型消费者"
    return "城市消费人群"


__all__ = ["MiroFishProfileAdapter", "CHANNEL_LABELS"]
