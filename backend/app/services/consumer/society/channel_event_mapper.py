"""Map society events into consumer channel events."""

from __future__ import annotations

from typing import Any, Mapping

from ..event_ontology import ConsumerEventType
from .channel_models import ConsumerChannelEvent
from .channel_policy import ConsumerChannelPolicy


class ChannelEventMapper:
    """Convert Phase 6G society events to Phase 6H channel events."""

    def map_event(
        self,
        event: Mapping[str, Any],
        channel_id: str,
        policy: ConsumerChannelPolicy,
        sequence: int,
    ) -> dict:
        event_type = str(event.get("consumer_event_type") or ConsumerEventType.FIRST_IMPRESSION.value)
        if event_type not in policy.allowed_event_types:
            event_type = ConsumerEventType.FIRST_IMPRESSION.value
        strength = self._strength_for_event(event_type, policy)
        actor_id = str(event.get("agent_id") or event.get("actor_id") or "")
        claim = event.get("claim_id") or event.get("claim") or "claim-1"
        return ConsumerChannelEvent(
            event_id=f"channel:{channel_id}:{sequence}:{event_type}",
            consumer_event_type=event_type,
            channel_id=channel_id,
            round_index=int(event.get("round_index", 0) or 0),
            actor_id=actor_id,
            segment=str(event.get("segment") or ""),
            target_ids=[str(target) for target in event.get("target_ids", [])],
            claim_id=str(claim),
            finding_ids=[str(fid) for fid in event.get("finding_ids", [])],
            quote=str(event.get("quote") or ""),
            strength=strength,
            cross_channel=False,
            source_channel_id="",
            target_channel_id="",
        ).to_dict()

    def _strength_for_event(self, event_type: str, policy: ConsumerChannelPolicy) -> float:
        base = 0.35
        if event_type in {
            ConsumerEventType.AMPLIFY_CLAIM.value,
            ConsumerEventType.SHARE_TO_CHANNEL.value,
        }:
            base += policy.amplification_factor * 0.45
        if event_type in {
            ConsumerEventType.MISREAD_CLAIM.value,
            ConsumerEventType.NEGATIVE_CASCADE.value,
        }:
            base += policy.misread_factor * 0.45
        if event_type == ConsumerEventType.ASK_PROOF.value:
            base += policy.evidence_demand_factor * 0.45
        if event_type == ConsumerEventType.PRICE_RESISTANCE.value:
            base += policy.price_sensitivity_factor * 0.45
        if event_type == ConsumerEventType.TRUST_RECOVERY.value:
            base += policy.trust_repair_factor * 0.45
        if event_type == ConsumerEventType.PURCHASE_INTENT_UP.value:
            base += policy.purchase_intent_factor * 0.45
        return round(max(0.0, min(1.0, base)), 4)


__all__ = ["ChannelEventMapper"]
