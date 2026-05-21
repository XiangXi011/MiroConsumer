"""Social topology builder for consumer simulation sandbox."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Set

from .persona_pack import load_default_persona_pack


@dataclass
class SocialTopology:
    communities: Dict[str, List[str]] = field(default_factory=dict)
    persona_community: Dict[str, str] = field(default_factory=dict)
    persona_role: Dict[str, str] = field(default_factory=dict)
    bridges: Set[str] = field(default_factory=set)
    amplifiers: Set[str] = field(default_factory=set)
    skeptics: Set[str] = field(default_factory=set)
    lurkers: Set[str] = field(default_factory=set)


def _community_key_from_attention_drivers(attention_drivers: List[str]) -> str:
    """Derive a community hint from attention driver keywords."""
    keywords = {d.lower().strip() for d in attention_drivers}
    if keywords & {
        "nutrition",
        "trust",
        "premium_brand",
        "familiar_brand",
        "daily_value",
        "safety",
        "price",
        "ease",
    }:
        return "caregivers"
    if keywords & {
        "ingredients",
        "evidence",
        "value",
        "data",
        "professional_endorsement",
        "system_fit",
    }:
        return "analysts"
    if keywords & {
        "novelty",
        "peer_review",
        "visual_appeal",
        "expert_recommendation",
        "low_effort_choice",
        "trusted_brand",
        "deal",
        "feature_count",
        "social_status",
    }:
        return "social_shoppers"
    return "general"


def _derive_communities(personas: List[Mapping[str, Any]]) -> Dict[str, List[str]]:
    """Group personas into communities based on shared attention-driver themes."""
    communities: Dict[str, List[str]] = {}
    for persona in personas:
        pid = str(persona.get("persona_id", ""))
        drivers = persona.get("attention_drivers", [])
        key = _community_key_from_attention_drivers(drivers)
        communities.setdefault(key, []).append(pid)

    sorted_keys = sorted(
        communities.keys(),
        key=lambda k: min(communities[k]) if communities[k] else k,
    )
    named_communities: Dict[str, List[str]] = {}
    for idx, key in enumerate(sorted_keys, start=1):
        members = sorted(communities[key])
        named_communities[f"community_{idx}"] = members
    return named_communities


def _derive_role(persona: Mapping[str, Any]) -> str:
    """Derive a single primary social role from persona traits."""
    influence = float(persona.get("influence_weight", 0.5))
    herd = str(persona.get("herd_tendency", "medium")).strip().lower()
    cognition = str(persona.get("cognition_level", "medium")).strip().lower()
    search = str(persona.get("search_propensity", "medium")).strip().lower()
    drivers = {d.lower().strip() for d in persona.get("attention_drivers", [])}
    # P1-6: Extract additional persona dimensions for richer role mapping
    involvement = str(persona.get("category_involvement", "medium")).strip().lower()
    brand_rel = str(persona.get("brand_relationship", "neutral")).strip().lower()

    # P1-6: Low category involvement + low influence = lurker
    if involvement == "low" and influence < 0.5:
        return "lurker"

    if influence < 0.6 or (search == "low" and cognition == "low"):
        return "lurker"

    if cognition == "high" and herd in {"low", "medium"}:
        if drivers & {
            "ingredients",
            "evidence",
            "data",
            "professional_endorsement",
            "system_fit",
        }:
            return "skeptic"

    if influence > 0.7 and herd in {"low", "medium"} and cognition == "high":
        return "bridge"

    if influence > 0.7 and herd == "high":
        return "amplifier"

    return "regular"


def build_social_topology(
    personas: Optional[List[Mapping[str, Any]]] = None,
) -> SocialTopology:
    """Build a deterministic social topology from persona traits."""
    if personas is None:
        personas = load_default_persona_pack()

    communities = _derive_communities(personas)
    persona_community: Dict[str, str] = {}
    for comm_name, members in communities.items():
        for pid in members:
            persona_community[pid] = comm_name

    persona_role: Dict[str, str] = {}
    bridges: Set[str] = set()
    amplifiers: Set[str] = set()
    skeptics: Set[str] = set()
    lurkers: Set[str] = set()

    for persona in personas:
        pid = str(persona.get("persona_id", ""))
        role = _derive_role(persona)
        persona_role[pid] = role
        if role == "bridge":
            bridges.add(pid)
        elif role == "amplifier":
            amplifiers.add(pid)
        elif role == "skeptic":
            skeptics.add(pid)
        elif role == "lurker":
            lurkers.add(pid)

    return SocialTopology(
        communities=communities,
        persona_community=persona_community,
        persona_role=persona_role,
        bridges=bridges,
        amplifiers=amplifiers,
        skeptics=skeptics,
        lurkers=lurkers,
    )


def _deterministic_choice(
    population: List[str],
    count: int,
    seed_str: str,
) -> List[str]:
    """Select up to count items from population deterministically using a seed."""
    if not population or count <= 0:
        return []
    shuffled = sorted(
        population,
        key=lambda x: hashlib.sha256(f"{seed_str}:{x}".encode("utf-8")).hexdigest(),
    )
    return shuffled[:count]


def select_topology_aware_targets(
    actor_id: str,
    event_type: str,
    topology: SocialTopology,
    all_persona_ids: List[str],
    round_index: int,
) -> List[str]:
    """Select propagation targets based on actor role and community topology."""
    role = topology.persona_role.get(actor_id, "regular")
    community = topology.persona_community.get(actor_id, "")

    if role == "lurker":
        max_targets = 1
    elif role == "amplifier":
        max_targets = 3
    elif role == "bridge":
        max_targets = 2
    else:
        max_targets = 2

    if role == "skeptic":
        max_targets = 1

    own_community = topology.communities.get(community, [])
    own_pool = [pid for pid in own_community if pid != actor_id]

    cross_pool: List[str] = []
    if role == "bridge":
        cross_pool = [
            pid
            for pid in all_persona_ids
            if pid != actor_id and topology.persona_community.get(pid) != community
        ]

    seed = f"{actor_id}_{event_type}_r{round_index}"

    targets: List[str] = []
    if role == "bridge" and cross_pool:
        cross_targets = _deterministic_choice(cross_pool, max_targets, seed + "_cross")
        targets.extend(cross_targets)
        if len(targets) < max_targets and own_pool:
            remaining = max_targets - len(targets)
            own_targets = _deterministic_choice(own_pool, remaining, seed + "_own")
            targets.extend(own_targets)
    else:
        targets = _deterministic_choice(own_pool, max_targets, seed + "_own")

    seen: Set[str] = set()
    unique_targets: List[str] = []
    for t in targets:
        if t not in seen:
            seen.add(t)
            unique_targets.append(t)

    return unique_targets


def reevaluate_roles_after_round(
    topology: SocialTopology,
    round_snapshots: List[Mapping[str, Any]],
    round_index: int,
) -> SocialTopology:
    """Re-evaluate social roles after each propagation round.

    Roles can shift based on observed engagement patterns:
    - Agents with consistently high engagement and cross-community events
      may become bridges
    - Agents with declining engagement may become lurkers
    - Agents challenging consensus may become skeptics

    Args:
        topology: Current social topology (mutated in place)
        round_snapshots: Snapshots from the just-completed round
        round_index: Current round number (0-indexed)

    Returns:
        The updated topology with re-evaluated roles.
    """
    # P1-5: Skip re-evaluation for round 0 — no prior engagement history
    if round_index < 1:
        return topology

    # Compute engagement scores per agent from this round
    engagement_by_agent: Dict[str, int] = {}
    for snapshot in round_snapshots:
        aid = str(snapshot.get("agent_id", ""))
        events = snapshot.get("propagation_events", [])
        if isinstance(events, list):
            engagement_by_agent[aid] = engagement_by_agent.get(aid, 0) + len(events)

    # Re-evaluate roles based on cumulative behavior
    for persona_id in topology.persona_role:
        current_role = topology.persona_role[persona_id]
        engagement = engagement_by_agent.get(persona_id, 0)

        # High engagement agents that were lurkers may become regular
        if current_role == "lurker" and engagement >= 2:
            topology.persona_role[persona_id] = "regular"
            topology.lurkers.discard(persona_id)

        # Consistently low engagement regular agents may become lurkers
        elif current_role == "regular" and engagement == 0 and round_index >= 2:
            topology.persona_role[persona_id] = "lurker"
            topology.lurkers.add(persona_id)

    return topology


__all__ = [
    "SocialTopology",
    "build_social_topology",
    "select_topology_aware_targets",
    "reevaluate_roles_after_round",
]
