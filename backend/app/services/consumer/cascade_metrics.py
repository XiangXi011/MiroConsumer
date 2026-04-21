"""Cascade metrics for consumer propagation events."""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Mapping, Optional

from .social_topology import SocialTopology, build_social_topology


def compute_cascade_metrics(
    events: List[Mapping[str, Any]],
    topology: Optional[SocialTopology] = None,
) -> Dict[str, Any]:
    """Compute deterministic cascade metrics from propagation events.

    Args:
        events: PropagationEvent dicts with optional topology metadata.
        topology: Social topology for community-aware metrics. Built from
            default persona pack if not provided.

    Returns:
        Dict of cascade metrics.
    """
    if topology is None:
        topology = build_social_topology()

    total_events = len(events)
    if total_events == 0:
        return {
            "community_count": len(topology.communities),
            "active_community_count": 0,
            "community_coverage": 0.0,
            "cross_community_event_count": 0,
            "bridge_event_count": 0,
            "dominant_event_type": "",
            "narrative_takeover_score": 0.0,
            "blocked_event_count": 0,
            "reversal_event_count": 0,
            "lurker_event_count": 0,
            "amplifier_event_count": 0,
            "avg_reach": 0.0,
        }

    event_types: Counter[str] = Counter()
    active_communities: set[str] = set()
    cross_community_count = 0
    bridge_event_count = 0
    blocked_count = 0
    reversal_count = 0
    lurker_event_count = 0
    amplifier_event_count = 0
    total_reach = 0

    for event in events:
        event_type = str(event.get("event_type", ""))
        actor_id = str(event.get("actor_id", ""))
        target_ids = event.get("target_ids", [])
        if isinstance(target_ids, list):
            total_reach += len(target_ids)

        event_types[event_type] += 1

        actor_community = event.get("actor_community") or topology.persona_community.get(actor_id, "")
        if actor_community:
            active_communities.add(actor_community)

        if event.get("cross_community"):
            cross_community_count += 1

        actor_role = event.get("actor_role") or topology.persona_role.get(actor_id, "")
        if actor_role == "bridge":
            bridge_event_count += 1
        elif actor_role == "lurker":
            lurker_event_count += 1
        elif actor_role == "amplifier":
            amplifier_event_count += 1

        if event_type in {"skeptical_challenge", "clarification_recovery"}:
            blocked_count += 1
        if event_type in {"misread_amplification", "clarification_recovery", "risk_discovery"}:
            reversal_count += 1

    dominant_event_type = event_types.most_common(1)[0][0] if event_types else ""
    positive_count = event_types.get("positive_relay", 0)
    narrative_takeover_score = round(positive_count / total_events, 4) if total_events else 0.0

    community_count = len(topology.communities)
    active_community_count = len(active_communities)
    community_coverage = round(active_community_count / community_count, 4) if community_count else 0.0

    avg_reach = round(total_reach / total_events, 4) if total_events else 0.0

    return {
        "community_count": community_count,
        "active_community_count": active_community_count,
        "community_coverage": community_coverage,
        "cross_community_event_count": cross_community_count,
        "bridge_event_count": bridge_event_count,
        "dominant_event_type": dominant_event_type,
        "narrative_takeover_score": narrative_takeover_score,
        "blocked_event_count": blocked_count,
        "reversal_event_count": reversal_count,
        "lurker_event_count": lurker_event_count,
        "amplifier_event_count": amplifier_event_count,
        "avg_reach": avg_reach,
    }


__all__ = ["compute_cascade_metrics"]
