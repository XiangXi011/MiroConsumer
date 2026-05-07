"""Deterministic social network topology for consumer society runtime."""

from __future__ import annotations

import hashlib
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Mapping, Sequence

from .population_models import ConsumerSocietyAgent


TOPOLOGY_VERSION = "phase7g_p2_v1"
GRAPH_KEYS = (
    "family_graph",
    "workplace_graph",
    "friend_graph",
    "social_media_graph",
    "channel_graph",
)


def build_consumer_network_topology(
    population: Iterable[ConsumerSocietyAgent],
    channel_assignments: Mapping[str, Sequence[str]] | None = None,
    seed: int = 0,
) -> Dict[str, Any]:
    """Build bounded, deterministic topology edges for propagation analysis."""
    agents = list(population)
    agent_by_id = {agent.agent_id: agent for agent in agents}
    nodes = [
        {
            "agent_id": agent.agent_id,
            "segment": agent.segment,
            "role": agent.role.value,
            "layer": agent.layer,
            "family_structure": str(agent.traits.get("family_structure", "")),
            "city_tier": str(agent.traits.get("city_tier", "")),
        }
        for agent in agents
    ]

    groups: Dict[str, Dict[str, List[str]]] = {key: defaultdict(list) for key in GRAPH_KEYS}
    for agent in agents:
        traits = agent.traits or {}
        groups["family_graph"][str(traits.get("family_structure") or agent.segment)].append(agent.agent_id)
        groups["workplace_graph"][str(traits.get("city_tier") or agent.layer)].append(agent.agent_id)
        groups["friend_graph"][agent.segment].append(agent.agent_id)
        groups["social_media_graph"][agent.role.value].append(agent.agent_id)
    for channel_id, agent_ids in (channel_assignments or {}).items():
        groups["channel_graph"][str(channel_id)].extend(str(agent_id) for agent_id in agent_ids)

    edges: List[Dict[str, Any]] = []
    graph_edge_ids: Dict[str, List[str]] = {key: [] for key in GRAPH_KEYS}
    seen = set()
    for graph_key, buckets in groups.items():
        for bucket, agent_ids in buckets.items():
            unique_ids = [agent_id for agent_id in dict.fromkeys(agent_ids) if agent_id in agent_by_id]
            edges_for_bucket = _bounded_neighbor_edges(
                graph_key=graph_key,
                bucket=str(bucket),
                agent_ids=unique_ids,
                agent_by_id=agent_by_id,
                seed=seed,
                seen=seen,
            )
            for edge in edges_for_bucket:
                graph_edge_ids[graph_key].append(edge["edge_id"])
                edges.append(edge)

    return {
        "topology_version": TOPOLOGY_VERSION,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "nodes": nodes,
        "edges": edges,
        "graphs": graph_edge_ids,
    }


def _bounded_neighbor_edges(
    *,
    graph_key: str,
    bucket: str,
    agent_ids: Sequence[str],
    agent_by_id: Mapping[str, ConsumerSocietyAgent],
    seed: int,
    seen: set,
) -> List[Dict[str, Any]]:
    if len(agent_ids) < 2:
        return []
    edges: List[Dict[str, Any]] = []
    sorted_ids = sorted(agent_ids)
    fanout = 2 if graph_key in {"social_media_graph", "channel_graph"} else 1
    for index, source_id in enumerate(sorted_ids):
        for offset in range(1, min(fanout + 1, len(sorted_ids))):
            target_id = sorted_ids[(index + offset) % len(sorted_ids)]
            if source_id == target_id:
                continue
            edge_key = (graph_key, source_id, target_id)
            if edge_key in seen:
                continue
            seen.add(edge_key)
            source = agent_by_id[source_id]
            target = agent_by_id[target_id]
            trust_weight = _score(seed, graph_key, source_id, target_id, "trust")
            influence_weight = round((source.share_propensity + target.share_propensity) / 2, 4)
            exposure_frequency = _exposure_frequency(graph_key, trust_weight, influence_weight)
            misread_probability = _misread_probability(source, target, graph_key)
            edge_id = hashlib.sha1(
                f"{seed}:{graph_key}:{source_id}:{target_id}".encode("utf-8")
            ).hexdigest()[:14]
            edges.append(
                {
                    "edge_id": f"{graph_key}:{edge_id}",
                    "source_agent_id": source_id,
                    "target_agent_id": target_id,
                    "graph_type": graph_key,
                    "bucket": bucket,
                    "trust_weight": trust_weight,
                    "influence_weight": round(influence_weight, 4),
                    "exposure_frequency": exposure_frequency,
                    "misread_probability": misread_probability,
                }
            )
    return edges


def _score(seed: int, *parts: str) -> float:
    digest = hashlib.sha1(":".join([str(seed), *parts]).encode("utf-8")).hexdigest()
    raw = int(digest[:8], 16) / 0xFFFFFFFF
    return round(0.25 + raw * 0.7, 4)


def _exposure_frequency(graph_key: str, trust_weight: float, influence_weight: float) -> float:
    multiplier = {
        "family_graph": 0.9,
        "workplace_graph": 0.55,
        "friend_graph": 0.7,
        "social_media_graph": 0.8,
        "channel_graph": 0.75,
    }.get(graph_key, 0.5)
    return round(max(0.0, min(1.0, multiplier * ((trust_weight + influence_weight) / 2))), 4)


def _misread_probability(
    source: ConsumerSocietyAgent,
    target: ConsumerSocietyAgent,
    graph_key: str,
) -> float:
    base = (source.skepticism + target.skepticism) / 2
    if graph_key == "social_media_graph":
        base += 0.12
    if graph_key == "family_graph":
        base -= 0.08
    return round(max(0.0, min(1.0, base)), 4)


__all__ = ["GRAPH_KEYS", "TOPOLOGY_VERSION", "build_consumer_network_topology"]
