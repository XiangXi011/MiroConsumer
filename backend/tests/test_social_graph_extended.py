"""Extended tests for social graph: random graph, scale-free, custom import, edge fields."""

import sys
from unittest.mock import MagicMock

for mod_name in [
    "zep_cloud", "zep_cloud.client", "zep_cloud.types",
    "zep_cloud.types.graph", "zep_cloud.types.node",
    "oasis", "oasis.oasis", "oasis.oasis.Oasis",
]:
    if mod_name not in sys.modules:
        sys.modules[mod_name] = MagicMock()

from app.services.consumer.social.graph import SocialEdge, SocialGraph, SocialGraphGenerator


class TestRandomGraph:
    def test_node_count(self):
        gen = SocialGraphGenerator(seed=42)
        ids = [f"n{i}" for i in range(30)]
        g = gen.generate_random(ids, edge_probability=0.3, seed=42)
        assert g.node_count == 30

    def test_reasonable_edge_count(self):
        """With p=0.3 on 30 nodes, expect roughly C(30,2)*0.3*2 ≈ 261 directed edges."""
        gen = SocialGraphGenerator(seed=42)
        ids = [f"n{i}" for i in range(30)]
        g = gen.generate_random(ids, edge_probability=0.3, seed=42)
        # Each undirected pair produces 0 or 2 directed edges
        assert g.edge_count > 0
        # With 30 nodes and p=0.3, expect a reasonable number
        assert 50 <= g.edge_count <= 500

    def test_deterministic_with_seed(self):
        ids = [f"n{i}" for i in range(20)]
        g1 = SocialGraphGenerator(seed=42).generate_random(ids, edge_probability=0.2, seed=99)
        g2 = SocialGraphGenerator(seed=42).generate_random(ids, edge_probability=0.2, seed=99)
        assert g1.edge_count == g2.edge_count

    def test_low_probability_sparse(self):
        ids = [f"n{i}" for i in range(20)]
        g = SocialGraphGenerator(seed=42).generate_random(ids, edge_probability=0.01, seed=42)
        assert g.node_count == 20
        # Very low probability → few edges
        assert g.edge_count < 40

    def test_high_probability_dense(self):
        ids = [f"n{i}" for i in range(10)]
        g = SocialGraphGenerator(seed=42).generate_random(ids, edge_probability=1.0, seed=42)
        # Complete graph: C(10,2)*2 = 90 directed edges
        assert g.edge_count == 90


class TestScaleFreeGraph:
    def test_node_count(self):
        gen = SocialGraphGenerator(seed=42)
        ids = [f"n{i}" for i in range(50)]
        g = gen.generate_scale_free(ids, m_edges=3, seed=42)
        assert g.node_count == 50

    def test_has_hub_node(self):
        """The highest-degree node should have degree > 2 * average degree."""
        gen = SocialGraphGenerator(seed=42)
        ids = [f"n{i}" for i in range(100)]
        g = gen.generate_scale_free(ids, m_edges=3, seed=42)

        # Calculate degrees (outgoing edges)
        degrees = {nid: len(g.edges.get(nid, [])) for nid in g.nodes}
        max_degree = max(degrees.values())
        avg_degree = sum(degrees.values()) / len(degrees) if degrees else 0

        assert max_degree > avg_degree * 2, (
            f"Expected hub node: max_degree={max_degree}, avg_degree={avg_degree}"
        )

    def test_deterministic_with_seed(self):
        ids = [f"n{i}" for i in range(30)]
        g1 = SocialGraphGenerator(seed=42).generate_scale_free(ids, m_edges=2, seed=77)
        g2 = SocialGraphGenerator(seed=42).generate_scale_free(ids, m_edges=2, seed=77)
        assert g1.edge_count == g2.edge_count

    def test_empty_input(self):
        g = SocialGraphGenerator(seed=42).generate_scale_free([], m_edges=3)
        assert g.node_count == 0
        assert g.edge_count == 0

    def test_small_graph(self):
        """Graph with fewer nodes than m_edges+1 should still work."""
        ids = [f"n{i}" for i in range(3)]
        g = SocialGraphGenerator(seed=42).generate_scale_free(ids, m_edges=5, seed=42)
        assert g.node_count == 3
        assert g.edge_count > 0


class TestFromAdjacencyList:
    def test_basic_import(self):
        adj = {
            "a": ["b", "c"],
            "b": ["c"],
            "c": [],
        }
        g = SocialGraph.from_adjacency_list(adj, edge_type="custom")
        assert g.node_count == 3
        assert g.edge_count == 3  # a->b, a->c, b->c
        assert "a" in g.nodes
        assert "b" in g.nodes

    def test_dict_targets_with_weight(self):
        adj = {
            "a": [{"id": "b", "weight": 0.9}, {"id": "c", "weight": 0.3}],
        }
        g = SocialGraph.from_adjacency_list(adj)
        assert g.node_count == 3
        assert g.edge_count == 2
        edges_a = g.get_neighbors("a")
        weights = {e.target_id: e.weight for e in edges_a}
        assert weights["b"] == 0.9
        assert weights["c"] == 0.3

    def test_mixed_targets(self):
        adj = {
            "x": ["y", {"id": "z", "weight": 0.7}],
        }
        g = SocialGraph.from_adjacency_list(adj)
        assert g.node_count == 3
        edges_x = g.get_neighbors("x")
        assert len(edges_x) == 2

    def test_empty_adjacency_list(self):
        g = SocialGraph.from_adjacency_list({})
        assert g.node_count == 0
        assert g.edge_count == 0

    def test_edge_type_propagates(self):
        adj = {"a": ["b"]}
        g = SocialGraph.from_adjacency_list(adj, edge_type="influence")
        edge = g.get_neighbors("a")[0]
        assert edge.edge_type == "influence"


class TestSocialEdgeNewFields:
    def test_default_channel(self):
        e = SocialEdge("a", "b", 0.5, "friend", 0.4)
        assert e.channel == "general"

    def test_default_visibility_level(self):
        e = SocialEdge("a", "b", 0.5, "friend", 0.4)
        assert e.visibility_level == "public"

    def test_default_interaction_frequency(self):
        e = SocialEdge("a", "b", 0.5, "friend", 0.4)
        assert e.interaction_frequency == 0.5

    def test_custom_values(self):
        e = SocialEdge("a", "b", 0.8, "family", 0.6,
                       channel="wechat", visibility_level="friends",
                       interaction_frequency=0.9)
        assert e.channel == "wechat"
        assert e.visibility_level == "friends"
        assert e.interaction_frequency == 0.9

    def test_graph_generators_set_defaults(self):
        gen = SocialGraphGenerator(seed=42)
        ids = [f"n{i}" for i in range(10)]
        g = gen.generate_small_world(ids, k_neighbors=4)
        for edges in g.edges.values():
            for e in edges:
                assert e.channel == "general"
                assert e.visibility_level == "public"
