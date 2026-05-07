"""Channel policy definitions for Phase 6H consumer propagation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, Iterable, List, Sequence

from ..event_ontology import ConsumerEventType
from .channel_models import CHANNEL_IDS, CHANNEL_LABELS


DEFAULT_CHANNEL_IDS = ("xiaohongshu", "wechat_group", "ecommerce_review")
MODE_CHANNEL_LIMITS = {
    "quick": 3,
    "standard": 5,
    "standard_plus": 6,
    "large_society": 8,
}
MODE_CHANNEL_MINIMUMS = {
    "quick": 1,
    "standard": 3,
    "standard_plus": 4,
    "large_society": 6,
}


@dataclass
class ConsumerChannelPolicy:
    channel_id: str
    amplification_factor: float
    misread_factor: float
    evidence_demand_factor: float
    price_sensitivity_factor: float
    trust_repair_factor: float
    purchase_intent_factor: float
    cross_channel_spread_factor: float
    allowed_event_types: List[str]

    def validate(self) -> "ConsumerChannelPolicy":
        if self.channel_id not in CHANNEL_IDS:
            raise ValueError(f"Unsupported channel id: {self.channel_id}")
        for name in (
            "amplification_factor",
            "misread_factor",
            "evidence_demand_factor",
            "price_sensitivity_factor",
            "trust_repair_factor",
            "purchase_intent_factor",
            "cross_channel_spread_factor",
        ):
            value = float(getattr(self, name))
            if value < 0.0 or value > 1.0:
                raise ValueError(f"{name} must be between 0.0 and 1.0")
        ontology = {event.value for event in ConsumerEventType}
        if not self.allowed_event_types or any(event_type not in ontology for event_type in self.allowed_event_types):
            raise ValueError("allowed_event_types must use Phase 6F consumer event ontology")
        return self

    def to_dict(self) -> dict:
        return asdict(self)


def _all_events() -> List[str]:
    return [event.value for event in ConsumerEventType]


def _policy(
    channel_id: str,
    amplification: float,
    misread: float,
    evidence: float,
    price: float,
    trust: float,
    purchase: float,
    cross: float,
) -> ConsumerChannelPolicy:
    return ConsumerChannelPolicy(
        channel_id=channel_id,
        amplification_factor=amplification,
        misread_factor=misread,
        evidence_demand_factor=evidence,
        price_sensitivity_factor=price,
        trust_repair_factor=trust,
        purchase_intent_factor=purchase,
        cross_channel_spread_factor=cross,
        allowed_event_types=_all_events(),
    ).validate()


DEFAULT_CHANNEL_POLICIES: Dict[str, ConsumerChannelPolicy] = {
    "xiaohongshu": _policy("xiaohongshu", 0.72, 0.34, 0.46, 0.28, 0.58, 0.62, 0.44),
    "douyin": _policy("douyin", 0.86, 0.72, 0.28, 0.32, 0.36, 0.66, 0.78),
    "wechat_group": _policy("wechat_group", 0.42, 0.48, 0.52, 0.38, 0.72, 0.44, 0.36),
    "ecommerce_review": _policy("ecommerce_review", 0.38, 0.42, 0.50, 0.78, 0.44, 0.52, 0.30),
    "zhihu_qa": _policy("zhihu_qa", 0.34, 0.30, 0.82, 0.32, 0.70, 0.38, 0.34),
    "offline_word_of_mouth": _policy("offline_word_of_mouth", 0.36, 0.36, 0.40, 0.34, 0.64, 0.40, 0.28),
    "livestream": _policy("livestream", 0.78, 0.46, 0.34, 0.70, 0.46, 0.84, 0.50),
    "sales_assistant": _policy("sales_assistant", 0.48, 0.28, 0.56, 0.46, 0.76, 0.58, 0.24),
}


def validate_enabled_channels(
    enabled_channels: Sequence[str] | None,
    mode: str,
) -> List[str]:
    if mode not in MODE_CHANNEL_LIMITS:
        raise ValueError(f"Unsupported society mode: {mode}")
    channels = list(DEFAULT_CHANNEL_IDS if not enabled_channels else enabled_channels)
    deduped: List[str] = []
    for channel_id in channels:
        cid = str(channel_id).strip()
        if cid not in CHANNEL_IDS:
            raise ValueError(f"Unsupported channel id: {cid}")
        if cid not in deduped:
            deduped.append(cid)
    limit = MODE_CHANNEL_LIMITS[mode]
    if len(deduped) > limit:
        raise ValueError(f"{mode} mode supports at most {limit} channels")
    return deduped


def resolve_runtime_channels(enabled_channels: Sequence[str] | None, mode: str) -> List[str]:
    channels = validate_enabled_channels(enabled_channels, mode)
    minimum = MODE_CHANNEL_MINIMUMS[mode]
    for channel_id in CHANNEL_IDS:
        if len(channels) >= minimum:
            break
        if channel_id not in channels:
            channels.append(channel_id)
    return channels


def get_channel_policies(channel_ids: Iterable[str]) -> Dict[str, ConsumerChannelPolicy]:
    policies: Dict[str, ConsumerChannelPolicy] = {}
    for channel_id in channel_ids:
        cid = str(channel_id)
        if cid not in DEFAULT_CHANNEL_POLICIES:
            raise ValueError(f"Unsupported channel id: {cid}")
        policies[cid] = DEFAULT_CHANNEL_POLICIES[cid]
    return policies


__all__ = [
    "CHANNEL_IDS",
    "CHANNEL_LABELS",
    "DEFAULT_CHANNEL_IDS",
    "DEFAULT_CHANNEL_POLICIES",
    "MODE_CHANNEL_LIMITS",
    "MODE_CHANNEL_MINIMUMS",
    "ConsumerChannelPolicy",
    "get_channel_policies",
    "resolve_runtime_channels",
    "validate_enabled_channels",
]
