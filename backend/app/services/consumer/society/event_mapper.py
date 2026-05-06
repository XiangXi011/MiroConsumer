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

        if event_type == ConsumerEventType.ASK_PROOF and agent.trust_baseline < 0.25 and previous:
            event_type = ConsumerEventType.TRUST_DECAY
        if event_type == ConsumerEventType.AMPLIFY_CLAIM and agent.share_propensity > 0.75:
            event_type = ConsumerEventType.SHARE_TO_CHANNEL

        claim = next(iter(visible_claims), "") if visible_claims else ""
        if not claim:
            claims = brief_context.get("claims") if isinstance(brief_context, Mapping) else []
            if isinstance(claims, list) and claims:
                claim = str(claims[0])
        if not claim:
            claim = "核心卖点"

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
            "quote": self._quote_for_event(event_type, claim, agent),
        }

    def _quote_for_event(
        self,
        event_type: ConsumerEventType,
        claim: str,
        agent: ConsumerSocietyAgent,
    ) -> str:
        traits = agent.traits or {}
        name = str(traits.get("name") or agent.segment or "这类消费者")
        family = str(traits.get("family_structure") or "")
        style = str(traits.get("expression_style") or "")
        risks = [str(item) for item in traits.get("risk_sensitivities", [])]
        risk_text = "、".join(risks[:2]) if risks else "真实体验"

        if event_type == ConsumerEventType.PRICE_RESISTANCE or agent.price_sensitivity >= 0.75:
            return f"{name}: {claim}我认可，但如果贵太多，我会先和同类产品仔细比价格。"

        if event_type == ConsumerEventType.ASK_PROOF or agent.evidence_sensitivity >= 0.8:
            return f"{name}: 我想看到{claim}的检测证明，尤其要解释清楚{risk_text}。"

        if (
            event_type == ConsumerEventType.TRUST_RECOVERY
            or "孩子" in family
            or any("孩子" in risk or "安全" in risk for risk in risks)
        ):
            return f"{name}: 如果是家里孩子会用的东西，{claim}会让我更安心，但证明要说清楚。"

        if (
            event_type in {ConsumerEventType.AMPLIFY_CLAIM, ConsumerEventType.SHARE_TO_CHANNEL}
            or "冲动" in style
            or "直播" in name
        ):
            return f"{name}: {claim}听起来很种草，直播里如果能看到对比，我会想试一下。"

        templates = {
            ConsumerEventType.FIRST_IMPRESSION: f"{name}: 我第一眼会注意到{claim}，但还要看场景是否真实。",
            ConsumerEventType.MISREAD_CLAIM: f"{name}: {claim}如果说得太满，我可能会误以为是全场景承诺。",
            ConsumerEventType.TRUST_DECAY: f"{name}: {claim}缺少来源时，我会开始担心可信度。",
            ConsumerEventType.PURCHASE_INTENT_UP: f"{name}: {claim}如果和我的使用场景匹配，会提升尝试意愿。",
            ConsumerEventType.PURCHASE_INTENT_DOWN: f"{name}: {claim}还没有说服我马上购买。",
            ConsumerEventType.NEGATIVE_CASCADE: f"{name}: {claim}被质疑后，很容易带出更多负面讨论。",
            ConsumerEventType.BLOCK_PROPAGATION: f"{name}: {claim}在我这里会停住，因为疑问还没被回答。",
        }
        return templates.get(event_type, f"{name}: 我注意到了{claim}，还需要更多信息判断。")


__all__ = ["ConsumerSocietyEventMapper", "ROLE_TO_EVENT"]
