"""Influencer-follower topology utilities for consumer social graphs."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any, Dict, List, Sequence


@dataclass(frozen=True)
class InfluencerGraphConfig:
    influencer_ratio: float = 0.05
    fanout: int = 40
    exposure_multiplier: float = 1.35
    seed: int = 0


def build_influencer_graph(
    node_ids: Sequence[str],
    config: InfluencerGraphConfig | None = None,
) -> Dict[str, Any]:
    """Build a deterministic power-law-like influencer graph."""
    cfg = config or InfluencerGraphConfig()
    ids = [str(node_id) for node_id in node_ids]
    if not ids:
        return {
            "topology_type": "influencer_graph",
            "nodes": {},
            "edges": [],
            "degree_distribution": {},
        }

    influencer_count = max(1, int(round(len(ids) * cfg.influencer_ratio)))
    influencer_count = min(influencer_count, len(ids))
    influencers = ids[:influencer_count]
    followers = ids[influencer_count:]
    rng = random.Random(cfg.seed)

    nodes = {
        node_id: {
            "role": "influencer" if node_id in influencers else "follower",
            "exposure_multiplier": cfg.exposure_multiplier if node_id in influencers else 1.0,
        }
        for node_id in ids
    }
    edges: List[Dict[str, Any]] = []
    out_degree = {node_id: 0 for node_id in ids}

    for rank, influencer in enumerate(influencers):
        if not followers:
            continue
        effective_fanout = min(len(followers), max(1, int(cfg.fanout)))
        offset = (rank * max(1, effective_fanout // 2)) % len(followers)
        targets = [followers[(offset + idx) % len(followers)] for idx in range(effective_fanout)]
        for target in targets:
            trust_weight = round(0.55 + rng.random() * 0.4, 4)
            influence_weight = round(min(1.0, trust_weight * cfg.exposure_multiplier), 4)
            edges.append(
                {
                    "source_id": influencer,
                    "target_id": target,
                    "edge_type": "influencer_follower",
                    "trust_weight": trust_weight,
                    "influence_weight": influence_weight,
                    "exposure_multiplier": cfg.exposure_multiplier,
                }
            )
            out_degree[influencer] += 1

    for follower in followers:
        if influencers:
            target = influencers[rng.randrange(len(influencers))]
            edges.append(
                {
                    "source_id": follower,
                    "target_id": target,
                    "edge_type": "follower_feedback",
                    "trust_weight": 0.25,
                    "influence_weight": 0.15,
                    "exposure_multiplier": 1.0,
                }
            )
            out_degree[follower] += 1

    return {
        "topology_type": "influencer_graph",
        "config": {
            "influencer_ratio": cfg.influencer_ratio,
            "fanout": cfg.fanout,
            "exposure_multiplier": cfg.exposure_multiplier,
            "seed": cfg.seed,
        },
        "nodes": nodes,
        "edges": edges,
        "degree_distribution": out_degree,
    }


class InfluencerSubgraphGenerator:
    """Generate influencer-follower subgraphs for larger social graphs."""

    def __init__(self, config: InfluencerGraphConfig | None = None) -> None:
        self.config = config or InfluencerGraphConfig()

    def generate(self, node_ids: Sequence[str]) -> Dict[str, Any]:
        return build_influencer_graph(node_ids, self.config)


__all__ = [
    "InfluencerGraphConfig",
    "InfluencerSubgraphGenerator",
    "build_influencer_graph",
]
