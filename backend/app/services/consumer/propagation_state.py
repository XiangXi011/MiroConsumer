"""Round-to-round propagation state for a single consumer agent."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping


@dataclass
class PropagationState:
    """Tracks cumulative state across simulation rounds for one agent."""

    agent_id: str
    attitude_history: List[str] = field(default_factory=list)
    engagement_history: List[int] = field(default_factory=list)
    cumulative_risk_exposure: int = 0
    social_reinforcement_count: int = 0
    last_bucket: str = ""
    rounds_seen_propagation_only: int = 0

    def update(
        self,
        attitude_label: str,
        engagement: int,
        bucket: str,
        visible_nodes: List[Mapping[str, Any]],
    ) -> None:
        """Record one round's results into the cumulative state."""
        self.attitude_history.append(attitude_label)
        self.engagement_history.append(engagement)
        self.last_bucket = bucket

        risk_count = sum(
            1 for node in visible_nodes if node.get("type") == "RiskPoint"
        )
        self.cumulative_risk_exposure += risk_count

        if (
            visible_nodes
            and all(
                node.get("visibility") == "Propagation_Only"
                for node in visible_nodes
            )
        ):
            self.rounds_seen_propagation_only += 1

        if bucket == "resonance":
            self.social_reinforcement_count += 1

    def to_prior_state_dict(self) -> Dict[str, Any]:
        """Serialize all fields to plain dicts/lists."""
        return {
            "agent_id": self.agent_id,
            "attitude_history": list(self.attitude_history),
            "engagement_history": list(self.engagement_history),
            "cumulative_risk_exposure": self.cumulative_risk_exposure,
            "social_reinforcement_count": self.social_reinforcement_count,
            "last_bucket": self.last_bucket,
            "rounds_seen_propagation_only": self.rounds_seen_propagation_only,
        }


def create_initial_state(agent_id: str) -> PropagationState:
    """Factory for a fresh propagation state with zero counters."""
    return PropagationState(agent_id=agent_id)
