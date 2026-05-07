"""Tests for social graph model."""

import sys
from unittest.mock import MagicMock

# Mock missing external dependencies before importing app.services
for mod_name in [
    "zep_cloud", "zep_cloud.client", "zep_cloud.types",
    "zep_cloud.types.graph", "zep_cloud.types.node",
    "oasis", "oasis.oasis", "oasis.oasis.Oasis",
]:
    if mod_name not in sys.modules:
        sys.modules[mod_name] = MagicMock()

from app.services.consumer.social.graph import SocialEdge, SocialGraph, SocialGraphGenerator


class TestSocialGraphBasic:
    def test_add_node(self):
        g = SocialGraph()
        g.add_node("a")
        assert g.node_count == 1
        assert "a" in g.nodes

    def test_add_edge_creates_nodes(self):
        g = SocialGraph()
        g.add_edge(SocialEdge("a", "b", 0.8, "friend", 0.6))
        assert g.node_count == 2
        assert g.edge_count == 1

    def test_get_neighbors(self):
        g = SocialGraph()
        g.add_edge(SocialEdge("a", "b", 0.8, "friend", 0.6))
        g.add_edge(SocialEdge("a", "c", 0.5, "colleague", 0.4))
        neighbors = g.get_neighbors("a")
        assert len(neighbors) == 2
        target_ids = {e.target_id for e in neighbors}
        assert target_ids == {"b", "c"}

    def test_get_influencers(self):
        g = SocialGraph()
        g.add_edge(SocialEdge("a", "b", 0.8, "friend", 0.6))
        g.add_edge(SocialEdge("c", "b", 0.5, "colleague", 0.4))
        influencers = g.get_influencers("b")
        assert len(influencers) == 2
        source_ids = {e.source_id for e in influencers}
        assert source_ids == {"a", "c"}

    def test_empty_graph(self):
        g = SocialGraph()
        assert g.node_count == 0
        assert g.edge_count == 0
        assert g.get_neighbors("nonexistent") == []
        assert g.get_influencers("nonexistent") == []

    def test_single_node_graph(self):
        g = SocialGraph()
        g.add_node("solo")
        assert g.node_count == 1
        assert g.edge_count == 0
        assert g.get_neighbors("solo") == []
        assert g.get_community("solo") == {"solo"}


class TestGetCommunity:
    def test_depth_1(self):
        g = SocialGraph()
        g.add_edge(SocialEdge("a", "b", 0.5, "friend", 0.4))
        g.add_edge(SocialEdge("a", "c", 0.5, "friend", 0.4))
        g.add_edge(SocialEdge("b", "d", 0.5, "friend", 0.4))
        # depth=1: only direct neighbors of "a"
        community = g.get_community("a", depth=1)
        assert "a" in community
        assert "b" in community
        assert "c" in community
        assert "d" not in community

    def test_depth_2(self):
        g = SocialGraph()
        g.add_edge(SocialEdge("a", "b", 0.5, "friend", 0.4))
        g.add_edge(SocialEdge("b", "d", 0.5, "friend", 0.4))
        # depth=2: a -> b -> d
        community = g.get_community("a", depth=2)
        assert community == {"a", "b", "d"}

    def test_depth_2_with_incoming(self):
        g = SocialGraph()
        g.add_edge(SocialEdge("x", "a", 0.5, "friend", 0.4))
        g.add_edge(SocialEdge("a", "b", 0.5, "friend", 0.4))
        community = g.get_community("a", depth=1)
        assert community == {"a", "x", "b"}


class TestSmallWorldGenerator:
    def test_node_count_preserved(self):
        gen = SocialGraphGenerator(seed=42)
        ids = [f"p{i}" for i in range(20)]
        g = gen.generate_small_world(ids, k_neighbors=4)
        assert g.node_count == 20

    def test_has_edges(self):
        gen = SocialGraphGenerator(seed=42)
        ids = [f"p{i}" for i in range(20)]
        g = gen.generate_small_world(ids, k_neighbors=4)
        assert g.edge_count > 0

    def test_reasonable_edge_count(self):
        """k_neighbors=4 on 20 nodes → at most ~80 directed edges (20*4),
        rewiring doesn't change count."""
        gen = SocialGraphGenerator(seed=42)
        ids = [f"p{i}" for i in range(20)]
        g = gen.generate_small_world(ids, k_neighbors=4)
        assert 20 <= g.edge_count <= 120

    def test_deterministic_with_seed(self):
        ids = [f"p{i}" for i in range(10)]
        g1 = SocialGraphGenerator(seed=99).generate_small_world(ids)
        g2 = SocialGraphGenerator(seed=99).generate_small_world(ids)
        assert g1.edge_count == g2.edge_count


class TestCommunityStructureGenerator:
    def test_node_count_preserved(self):
        gen = SocialGraphGenerator(seed=42)
        ids = [f"p{i}" for i in range(40)]
        g = gen.generate_community_structure(ids, n_communities=4)
        assert g.node_count == 40

    def test_intra_community_dominates(self):
        """Intra-community edges should far exceed inter-community edges."""
        gen = SocialGraphGenerator(seed=42)
        ids = [f"p{i}" for i in range(40)]
        g = gen.generate_community_structure(
            ids, n_communities=4, intra_density=0.8, inter_density=0.05,
        )

        # Split into communities same way the generator does
        chunk = 40 // 4
        communities = [
            ids[0:chunk], ids[chunk:2*chunk], ids[2*chunk:3*chunk], ids[3*chunk:],
        ]
        community_sets = [set(c) for c in communities]

        intra_count = 0
        inter_count = 0
        for edge_list in g.edges.values():
            for e in edge_list:
                src_comm = next(i for i, s in enumerate(community_sets) if e.source_id in s)
                dst_comm = next(i for i, s in enumerate(community_sets) if e.target_id in s)
                if src_comm == dst_comm:
                    intra_count += 1
                else:
                    inter_count += 1

        assert intra_count > inter_count * 5, (
            f"Expected intra >> inter, got intra={intra_count}, inter={inter_count}"
        )

    def test_every_node_has_edges(self):
        gen = SocialGraphGenerator(seed=42)
        ids = [f"p{i}" for i in range(20)]
        g = gen.generate_community_structure(ids, n_communities=4, intra_density=1.0)
        for nid in ids:
            assert len(g.get_neighbors(nid)) > 0, f"Node {nid} is isolated"
