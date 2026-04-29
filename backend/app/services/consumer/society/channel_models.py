"""Consumer channel models for Phase 6H propagation runtime."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List

from ..event_ontology import ConsumerEventType


CHANNEL_LABELS: Dict[str, str] = {
    "xiaohongshu": "小红书",
    "douyin": "抖音",
    "wechat_group": "微信群",
    "ecommerce_review": "电商评论区",
    "zhihu_qa": "知乎/问答社区",
    "offline_word_of_mouth": "线下口碑",
    "livestream": "直播间",
    "sales_assistant": "导购场景",
}

CHANNEL_IDS = tuple(CHANNEL_LABELS.keys())


def channel_label(channel_id: str) -> str:
    return CHANNEL_LABELS.get(channel_id, channel_id)


@dataclass
class ConsumerChannelEvent:
    event_id: str
    consumer_event_type: str
    channel_id: str
    round_index: int
    actor_id: str
    target_ids: List[str] = field(default_factory=list)
    claim_id: str = ""
    finding_ids: List[str] = field(default_factory=list)
    quote: str = ""
    strength: float = 0.0
    cross_channel: bool = False
    source_channel_id: str = ""
    target_channel_id: str = ""
    channel_label: str = ""

    def __post_init__(self) -> None:
        if self.channel_id not in CHANNEL_IDS:
            raise ValueError(f"Unsupported channel id: {self.channel_id}")
        if self.consumer_event_type not in {event.value for event in ConsumerEventType}:
            raise ValueError(f"Unsupported consumer_event_type: {self.consumer_event_type}")
        self.strength = max(0.0, min(1.0, float(self.strength)))
        if not self.channel_label:
            self.channel_label = channel_label(self.channel_id)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


__all__ = [
    "CHANNEL_IDS",
    "CHANNEL_LABELS",
    "ConsumerChannelEvent",
    "channel_label",
]
