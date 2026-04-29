"""Build representative consumer cards from Phase 6G/6H state."""

from typing import Any, Dict, List

from ..society.consumer_roles import ConsumerRole
from .representative_sampler import RepresentativeSampler


class RepresentativeCardBuilder:
    """Merge sampler output with channel and society metrics to produce cards."""

    def __init__(self, base_dir=None):
        self.sampler = RepresentativeSampler(base_dir=base_dir)
        self.store = self.sampler.store

    def build_cards(self, simulation_id: str, roles: List[str], limit: int) -> List[Dict[str, Any]]:
        rows = self.sampler.sample(simulation_id, roles=roles, limit=limit)
        society_metrics = self.store.read_metrics(simulation_id)
        channel_metrics = self.store.read_channel_metrics(simulation_id).get("channels", {})
        cards = []
        for row in rows:
            state = row.get("state", {})
            attitude_start = state.get("attitude_start", "neutral")
            attitude_latest = state.get("attitude_latest", "neutral")

            purchase_intent_start = float(state.get("purchase_intent_start", 0.5))
            purchase_intent_latest = float(state.get("purchase_intent_latest", 0.5))
            if attitude_start == "positive":
                purchase_intent_start = 0.7
            elif attitude_start == "skeptical":
                purchase_intent_start = 0.3

            if attitude_latest == "positive":
                purchase_intent_latest = 0.8
            elif attitude_latest == "skeptical":
                purchase_intent_latest = 0.2

            role_val = row.get("role", "")
            influence_score = 0.5
            if role_val == ConsumerRole.Advocate.value:
                influence_score = 0.75
            elif role_val == ConsumerRole.Amplifier.value:
                influence_score = 0.85
            elif role_val == ConsumerRole.Lurker.value:
                influence_score = 0.25
            elif role_val == ConsumerRole.Skeptic.value:
                influence_score = 0.45
            elif role_val == ConsumerRole.Misreader.value:
                influence_score = 0.35
            elif role_val == ConsumerRole.PriceSensitive.value:
                influence_score = 0.4
            elif role_val == ConsumerRole.TrustRepairable.value:
                influence_score = 0.55
            elif role_val == ConsumerRole.Blocker.value:
                influence_score = 0.3
            channel_id = row.get("channel_id", "")
            channel_fit = float(channel_metrics.get(channel_id, {}).get("fit_score", 0.0) or 0.0)
            reach_rate = float(society_metrics.get("reach_rate", 0.0) or 0.0)
            influence_score = max(0.0, min(1.0, (influence_score * 0.7) + (channel_fit * 0.2) + (reach_rate * 0.1)))

            cards.append({
                "agent_id": row["agent_id"],
                "display_name": f"Consumer {row['agent_id']}",
                "role": role_val,
                "segment": row.get("segment", ""),
                "channel_id": channel_id,
                "attitude_start": attitude_start,
                "attitude_latest": attitude_latest,
                "purchase_intent_start": purchase_intent_start,
                "purchase_intent_latest": purchase_intent_latest,
                "key_quote": row.get("key_quote", ""),
                "influence_score": round(influence_score, 4),
                "evidence_ids": row.get("finding_ids", []),
                "event_ids": row.get("event_ids", []),
            })

        return cards
