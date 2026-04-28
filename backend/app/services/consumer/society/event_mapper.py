"""Map society agent state into Phase 6F consumer event ontology."""

from __future__ import annotations

from typing import Any, Dict, Iterable, Mapping

from ..event_ontology import ConsumerEventType
from .consumer_roles import ConsumerRole
from .population_models import ConsumerSocietyAgent


ROLE_TO_EVENT = {
    ConsumerRole.Advocate: ConsumerEventType.PURCHASE_INTENT_UP,
    ConsumerRole.Skeptic: ConsumerEventType.ASK_PROOF,
    ConsumerRole.Misreader: ConsumerEventType.MISREAD_CLAIM,
    ConsumerRole.Amplifier: ConsumerEventType.AMPLIFY_CLAIM,
    ConsumerRole.Lurker: ConsumerEventType.FIRST_IMPRESSION,
    ConsumerRole.PriceSensitive: ConsumerEventType.PRICE_RESISTANCE,
    ConsumerRole.TrustRepairable: ConsumerEventType.TRUST_RECOVERY,
    ConsumerRole.Blocker: ConsumerEventType.BLOCK_PROPAGATION,
}


class ConsumerSocietyEventMapper:
    """Produce schema-stable consumer events from agent state."""

    def map_agent_event(
        self,
        agent: ConsumerSocietyAgent,
        round_index: int,
        visible_claims: Iterable[str],
        previous_events: Iterable[Mapping[str, Any]],
        brief_context: Mapping[str, Any],
        research_findings: Iterable[Any],
    ) -> Dict[str, Any]:
        event_type = ROLE_TO_EVENT.get(agent.role, ConsumerEventType.FIRST_IMPRESSION)
        previous = list(previous_events)
        if round_index == 0 and event_type not in {
            ConsumerEventType.MISREAD_CLAIM,
            ConsumerEventType.ASK_PROOF,
            ConsumerEventType.PRICE_RESISTANCE,
        }:
            event_type = ConsumerEventType.FIRST_IMPRESSION

        if (
            event_type == ConsumerEventType.ASK_PROOF
            and agent.trust_baseline < 0.25
            and len(previous) > 0
        ):
            event_type = ConsumerEventType.TRUST_DECAY
        if event_type == ConsumerEventType.AMPLIFY_CLAIM and agent.share_propensity > 0.75:
            event_type = ConsumerEventType.SHARE_TO_CHANNEL

        claim = next(iter(visible_claims), "") if visible_claims else ""
        if not claim:
            claims = brief_context.get("claims") if isinstance(brief_context, Mapping) else []
            if isinstance(claims, list) and claims:
                claim = str(claims[0])
        if not claim:
            claim = "consumer claim"

        trust = max(0.0, min(1.0, float(agent.state.get("trust", agent.trust_baseline))))
        purchase_intent = max(0.0, min(1.0, float(agent.state.get("purchase_intent", 0.5))))

        return {
            "event_id": f"{agent.agent_id}:r{round_index}:{event_type.value}",
            "round_index": round_index,
            "agent_id": agent.agent_id,
            "segment": agent.segment,
            "role": agent.role.value,
            "layer": agent.layer,
            "consumer_event_type": event_type.value,
            "claim": claim,
            "trust": round(trust, 4),
            "purchase_intent": round(purchase_intent, 4),
            "quote": self._quote_for_event(event_type, claim),
        }

    def _quote_for_event(self, event_type: ConsumerEventType, claim: str) -> str:
        templates = {
            ConsumerEventType.FIRST_IMPRESSION: f"我先注意到的是{claim}。",
            ConsumerEventType.ASK_PROOF: f"{claim}需要更直接的证据。",
            ConsumerEventType.AMPLIFY_CLAIM: f"{claim}这个点值得转给朋友看。",
            ConsumerEventType.MISREAD_CLAIM: f"我可能会把{claim}理解成另一个承诺。",
            ConsumerEventType.PRICE_RESISTANCE: f"看到{claim}后我会先比较价格。",
            ConsumerEventType.TRUST_DECAY: f"{claim}让我开始担心可信度。",
            ConsumerEventType.TRUST_RECOVERY: f"如果证据补足，{claim}能恢复信任。",
            ConsumerEventType.PURCHASE_INTENT_UP: f"{claim}提升了尝试意愿。",
            ConsumerEventType.PURCHASE_INTENT_DOWN: f"{claim}没有说服我购买。",
            ConsumerEventType.NEGATIVE_CASCADE: f"{claim}容易带来负面连锁反应。",
            ConsumerEventType.SHARE_TO_CHANNEL: f"{claim}适合被继续分享。",
            ConsumerEventType.BLOCK_PROPAGATION: f"{claim}在我这里会停止传播。",
        }
        return templates.get(event_type, f"我注意到了{claim}。")


__all__ = ["ConsumerSocietyEventMapper"]
