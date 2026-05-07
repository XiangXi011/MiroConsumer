"""Extended tests for social graph (batch B) + runtime control: influencer-follower,
channel-separated, path-finding, topology comparison, partial retry, early stop
enhancements, branch diff, intervention replay."""

import sys
import time
from unittest.mock import MagicMock

for mod_name in [
    "zep_cloud", "zep_cloud.client", "zep_cloud.types",
    "zep_cloud.types.graph", "zep_cloud.types.node",
    "oasis", "oasis.oasis", "oasis.oasis.Oasis",
]:
    if mod_name not in sys.modules:
        sys.modules[mod_name] = MagicMock()

from app.services.consumer.social.graph import SocialEdge, SocialGraph, SocialGraphGenerator
from app.services.consumer.runtime.control import (
    EarlyStopConfig, RuntimeControlLayer, RoundCheckpoint,
)


# ──────────────────────────────────────────────
# B1: Influencer-Follower Graph
# ──────────────────────────────────────────────

class TestInfluencerFollowerGraph:
    def test_has_hub_nodes(self):
        """Influencer nodes should have significantly more edges than followers."""
        gen = SocialGraphGenerator(seed=42)
        ids = [f"n{i}" for i in range(50)]
        g = gen.generate_influencer_follower(ids, n_influencers=5, seed=42)

        assert g.node_count == 50
        influencers = ids[:5]
        # Each influencer connects to 45 followers (bidirectional) + 4 peer links (bidirectional)
        for inf in influencers:
            out_degree = len(g.edges.get(inf, []))
            # 45 follower edges + 4 peer edges = 49
            assert out_degree >= 45, f"Influencer {inf} has only {out_degree} outgoing edges"

        # Followers should have fewer outgoing edges
        followers = ids[5:]
        for fol in followers[:5]:
            out_degree = len(g.edges.get(fol, []))
            # 1 follower->influencer edge per influencer = 5
            assert out_degree <= 10, f"Follower {fol} has {out_degree} outgoing edges"

    def test_default_influencer_count(self):
        """Default n_influencers = n // 10."""
        gen = SocialGraphGenerator(seed=42)
        ids = [f"n{i}" for i in range(100)]
        g = gen.generate_influencer_follower(ids, seed=42)
        assert g.node_count == 100
        assert g.edge_count > 0

    def test_influencers_interconnected(self):
        """Influencer nodes should be connected to each other."""
        gen = SocialGraphGenerator(seed=42)
        ids = [f"n{i}" for i in range(20)]
        g = gen.generate_influencer_follower(ids, n_influencers=4, seed=42)
        influencers = ids[:4]
        # Each influencer should have peer edges to other influencers
        for inf in influencers:
            peer_edges = [e for e in g.edges.get(inf, []) if e.edge_type == "peer"]
            assert len(peer_edges) == 3, f"Influencer {inf} should have 3 peer edges"

    def test_deterministic_with_seed(self):
        ids = [f"n{i}" for i in range(30)]
        g1 = SocialGraphGenerator(seed=42).generate_influencer_follower(ids, seed=99)
        g2 = SocialGraphGenerator(seed=42).generate_influencer_follower(ids, seed=99)
        assert g1.edge_count == g2.edge_count


# ──────────────────────────────────────────────
# B2: Channel-Separated Graph
# ──────────────────────────────────────────────

class TestChannelSeparatedGraph:
    def test_each_channel_has_connections(self):
        """Each channel group should have internal connections."""
        gen = SocialGraphGenerator(seed=42)
        ids = [f"n{i}" for i in range(40)]
        g = gen.generate_channel_separated(ids, seed=42)

        assert g.node_count == 40
        assert g.edge_count > 0

        # Check that edges with channel-specific types exist
        all_edge_types = set()
        for edges_list in g.edges.values():
            for e in edges_list:
                all_edge_types.add(e.edge_type)

        # At least some of the default channels should appear
        assert len(all_edge_types) > 1

    def test_deterministic_with_seed(self):
        ids = [f"n{i}" for i in range(30)]
        g1 = SocialGraphGenerator(seed=42).generate_channel_separated(ids, seed=77)
        g2 = SocialGraphGenerator(seed=42).generate_channel_separated(ids, seed=77)
        assert g1.edge_count == g2.edge_count

    def test_custom_channels(self):
        ids = [f"n{i}" for i in range(20)]
        g = SocialGraphGenerator(seed=42).generate_channel_separated(
            ids, channels=["ch1", "ch2"], seed=42
        )
        assert g.node_count == 20
        assert g.edge_count > 0

    def test_channel_edges_have_channel_field(self):
        """Channel-separated edges should have channel metadata."""
        gen = SocialGraphGenerator(seed=42)
        ids = [f"n{i}" for i in range(20)]
        g = gen.generate_channel_separated(ids, seed=42)
        channels_seen = set()
        for edges_list in g.edges.values():
            for e in edges_list:
                channels_seen.add(e.channel)
        # Should have at least one channel
        assert len(channels_seen) >= 1


# ──────────────────────────────────────────────
# B4: Path Finding
# ──────────────────────────────────────────────

class TestPathFinding:
    def test_find_path_direct(self):
        """Direct edge should be found."""
        g = SocialGraph()
        g.add_edge(SocialEdge("a", "b", 0.5, "friend", 0.4))
        paths = g.find_path("a", "b")
        assert len(paths) >= 1
        assert paths[0] == ["a", "b"]

    def test_find_path_multi_hop(self):
        """Should find multi-hop paths."""
        g = SocialGraph()
        g.add_edge(SocialEdge("a", "b", 0.5, "friend", 0.4))
        g.add_edge(SocialEdge("b", "c", 0.5, "friend", 0.4))
        paths = g.find_path("a", "c")
        assert len(paths) >= 1
        assert ["a", "b", "c"] in paths

    def test_find_path_no_path(self):
        """Should return empty if no path exists."""
        g = SocialGraph()
        g.add_edge(SocialEdge("a", "b", 0.5, "friend", 0.4))
        g.add_edge(SocialEdge("c", "d", 0.5, "friend", 0.4))
        paths = g.find_path("a", "c")
        assert paths == []

    def test_find_path_avoids_cycles(self):
        """Should not revisit nodes in path."""
        g = SocialGraph()
        g.add_edge(SocialEdge("a", "b", 0.5, "friend", 0.4))
        g.add_edge(SocialEdge("b", "a", 0.5, "friend", 0.4))
        g.add_edge(SocialEdge("b", "c", 0.5, "friend", 0.4))
        paths = g.find_path("a", "c")
        assert len(paths) >= 1
        for p in paths:
            assert len(p) == len(set(p)), f"Path {p} contains cycle"

    def test_find_path_max_depth(self):
        """Paths longer than max_depth should be excluded."""
        g = SocialGraph()
        g.add_edge(SocialEdge("a", "b", 0.5, "f", 0.4))
        g.add_edge(SocialEdge("b", "c", 0.5, "f", 0.4))
        g.add_edge(SocialEdge("c", "d", 0.5, "f", 0.4))
        g.add_edge(SocialEdge("d", "e", 0.5, "f", 0.4))
        # max_depth=2 means path length <= 3 (source + 2 hops)
        paths = g.find_path("a", "e", max_depth=2)
        assert paths == []

    def test_find_path_same_source_target(self):
        """Source == target should return [[source]]."""
        g = SocialGraph()
        g.add_edge(SocialEdge("a", "b", 0.5, "f", 0.4))
        paths = g.find_path("a", "a")
        assert len(paths) == 1
        assert paths[0] == ["a"]


class TestInfluencePath:
    def test_basic_structure(self):
        """get_influence_path should return list of dicts with node/depth/path."""
        g = SocialGraph()
        g.add_edge(SocialEdge("a", "b", 0.5, "f", 0.4))
        g.add_edge(SocialEdge("a", "c", 0.5, "f", 0.4))
        g.add_edge(SocialEdge("b", "d", 0.5, "f", 0.4))

        result = g.get_influence_path("a", max_depth=2)
        assert len(result) >= 3  # at least a, b, c (and d)

        for entry in result:
            assert "node" in entry
            assert "depth" in entry
            assert "path" in entry

        # Source node should be at depth 0
        source_entry = [e for e in result if e["node"] == "a"][0]
        assert source_entry["depth"] == 0
        assert source_entry["path"] == ["a"]

    def test_max_depth_limits_output(self):
        g = SocialGraph()
        g.add_edge(SocialEdge("a", "b", 0.5, "f", 0.4))
        g.add_edge(SocialEdge("b", "c", 0.5, "f", 0.4))
        g.add_edge(SocialEdge("c", "d", 0.5, "f", 0.4))

        result = g.get_influence_path("a", max_depth=1)
        nodes_found = {e["node"] for e in result}
        assert "a" in nodes_found
        assert "b" in nodes_found
        # c and d should be excluded (depth > 1)
        assert "d" not in nodes_found

    def test_empty_graph(self):
        g = SocialGraph()
        g.add_node("a")
        result = g.get_influence_path("a")
        assert len(result) == 1
        assert result[0]["node"] == "a"


# ──────────────────────────────────────────────
# B5: Topology A/B Comparison
# ──────────────────────────────────────────────

class TestCompareTopologies:
    def test_basic_comparison(self):
        gen = SocialGraphGenerator(seed=42)
        ids = [f"n{i}" for i in range(30)]
        g1 = gen.generate_random(ids, edge_probability=0.3, seed=42)
        g2 = gen.generate_random(ids, edge_probability=0.7, seed=42)

        result = SocialGraph.compare_topologies(g1, g2)
        assert "graph_a" in result
        assert "graph_b" in result
        assert "density_diff" in result
        assert result["graph_a"]["nodes"] == 30
        assert result["graph_b"]["nodes"] == 30
        # g2 with higher probability should have more edges
        assert result["density_diff"] > 0

    def test_identical_graphs(self):
        gen = SocialGraphGenerator(seed=42)
        ids = [f"n{i}" for i in range(20)]
        g1 = gen.generate_random(ids, edge_probability=0.3, seed=42)
        g2 = gen.generate_random(ids, edge_probability=0.3, seed=42)

        result = SocialGraph.compare_topologies(g1, g2)
        assert result["density_diff"] == 0

    def test_empty_graphs(self):
        g1 = SocialGraph()
        g2 = SocialGraph()
        result = SocialGraph.compare_topologies(g1, g2)
        assert result["graph_a"]["nodes"] == 0
        assert result["density_diff"] == 0


# ──────────────────────────────────────────────
# B6: Partial Retry
# ──────────────────────────────────────────────

class TestPartialRetry:
    def test_should_retry_when_few_events(self):
        config = EarlyStopConfig(enable_partial_retry=True, event_threshold=5)
        ctrl = RuntimeControlLayer(config)
        # 3 events > 0 and < 5 threshold → should retry
        assert ctrl.should_partial_retry({"new_events": 3}) is True

    def test_no_retry_when_disabled(self):
        config = EarlyStopConfig(enable_partial_retry=False, event_threshold=5)
        ctrl = RuntimeControlLayer(config)
        assert ctrl.should_partial_retry({"new_events": 3}) is False

    def test_no_retry_when_zero_events(self):
        config = EarlyStopConfig(enable_partial_retry=True, event_threshold=5)
        ctrl = RuntimeControlLayer(config)
        # 0 events → fully converged, no retry
        assert ctrl.should_partial_retry({"new_events": 0}) is False

    def test_no_retry_when_enough_events(self):
        config = EarlyStopConfig(enable_partial_retry=True, event_threshold=5)
        ctrl = RuntimeControlLayer(config)
        # 10 events >= threshold → no retry needed
        assert ctrl.should_partial_retry({"new_events": 10}) is False


# ──────────────────────────────────────────────
# B7: Early Stop with New Risks
# ──────────────────────────────────────────────

class TestEarlyStopRisks:
    def test_no_convergence_when_risks_present(self):
        """When new_risks >= risk_threshold, should not converge."""
        config = EarlyStopConfig(
            enabled=True, patience=1, min_rounds=0,
            event_threshold=5, attitude_change_threshold=0.01,
            risk_threshold=1,
        )
        ctrl = RuntimeControlLayer(config)

        # Save a checkpoint first
        ctrl.save_checkpoint(0, {"state": "v1"}, {"avg_attitude": 0.5, "new_events": 0})

        # Round with new risks — should not converge
        stop, reason = ctrl.should_early_stop(1, {
            "avg_attitude": 0.5, "new_events": 0, "new_risks": 3,
        })
        assert stop is False

    def test_convergence_when_no_risks(self):
        """When risk_threshold=0 (default), risks don't prevent convergence."""
        config = EarlyStopConfig(
            enabled=True, patience=1, min_rounds=0,
            event_threshold=5, attitude_change_threshold=0.01,
            risk_threshold=0,
        )
        ctrl = RuntimeControlLayer(config)
        ctrl.save_checkpoint(0, {"state": "v1"}, {"avg_attitude": 0.5, "new_events": 0})

        stop, reason = ctrl.should_early_stop(1, {
            "avg_attitude": 0.5, "new_events": 0, "new_risks": 3,
        })
        # With risk_threshold=0, condition new_risks >= 0 is always true,
        # but we check > 0 for the reset logic
        # Since risk_threshold is 0, the check doesn't trigger a reset
        assert stop is True  # should converge since stagnant


# ──────────────────────────────────────────────
# B8: Early Stop with Network Activation
# ──────────────────────────────────────────────

class TestEarlyStopActivation:
    def test_no_convergence_when_active(self):
        """High network activation should prevent convergence."""
        config = EarlyStopConfig(
            enabled=True, patience=1, min_rounds=0,
            event_threshold=5, attitude_change_threshold=0.01,
            activation_threshold=0.1,
        )
        ctrl = RuntimeControlLayer(config)
        ctrl.save_checkpoint(0, {"state": "v1"}, {"avg_attitude": 0.5, "new_events": 0})

        # High activation → should NOT converge
        stop, reason = ctrl.should_early_stop(1, {
            "avg_attitude": 0.5, "new_events": 0, "network_activation": 0.5,
        })
        assert stop is False

    def test_convergence_when_inactive(self):
        """Low network activation should allow convergence."""
        config = EarlyStopConfig(
            enabled=True, patience=1, min_rounds=0,
            event_threshold=5, attitude_change_threshold=0.01,
            activation_threshold=0.1,
        )
        ctrl = RuntimeControlLayer(config)
        ctrl.save_checkpoint(0, {"state": "v1"}, {"avg_attitude": 0.5, "new_events": 0})

        # Low activation → should converge
        stop, reason = ctrl.should_early_stop(1, {
            "avg_attitude": 0.5, "new_events": 0, "network_activation": 0.01,
        })
        assert stop is True


# ──────────────────────────────────────────────
# B9: Branch Diff
# ──────────────────────────────────────────────

class TestDiffBranches:
    def test_basic_diff(self):
        config = EarlyStopConfig()
        ctrl = RuntimeControlLayer(config)

        cp_a = [
            RoundCheckpoint(0, "hash1", {"avg_attitude": 0.5, "new_events": 10}, time.time()),
        ]
        cp_b = [
            RoundCheckpoint(0, "hash2", {"avg_attitude": 0.7, "new_events": 15}, time.time()),
        ]

        diff = ctrl.diff_branches(cp_a, cp_b)
        assert "avg_attitude" in diff
        assert diff["avg_attitude"]["a"] == 0.5
        assert diff["avg_attitude"]["b"] == 0.7
        assert abs(diff["avg_attitude"]["delta"] - 0.2) < 1e-9

    def test_empty_branch(self):
        config = EarlyStopConfig()
        ctrl = RuntimeControlLayer(config)
        diff = ctrl.diff_branches([], [RoundCheckpoint(0, "h", {}, time.time())])
        assert diff == {"diff": "empty branch"}

    def test_identical_branches(self):
        config = EarlyStopConfig()
        ctrl = RuntimeControlLayer(config)
        cp = [
            RoundCheckpoint(0, "h1", {"avg_attitude": 0.5}, time.time()),
        ]
        diff = ctrl.diff_branches(cp, cp)
        assert diff == {}  # no differences

    def test_extra_keys(self):
        config = EarlyStopConfig()
        ctrl = RuntimeControlLayer(config)
        cp_a = [RoundCheckpoint(0, "h1", {"a": 1}, time.time())]
        cp_b = [RoundCheckpoint(0, "h2", {"b": 2}, time.time())]
        diff = ctrl.diff_branches(cp_a, cp_b)
        assert "a" in diff
        assert "b" in diff


# ──────────────────────────────────────────────
# B10: Intervention Replay
# ──────────────────────────────────────────────

class TestInterventionReplay:
    def test_basic_replay(self):
        config = EarlyStopConfig()
        ctrl = RuntimeControlLayer(config)

        checkpoints = [
            RoundCheckpoint(0, "h0", {"avg_attitude": 0.5}, time.time()),
            RoundCheckpoint(1, "h1", {"avg_attitude": 0.6}, time.time()),
            RoundCheckpoint(2, "h2", {"avg_attitude": 0.7}, time.time()),
        ]

        replayed = ctrl.replay_intervention(
            checkpoints, intervention_round=2, modified_state={"avg_attitude": 0.3}
        )
        # Should keep rounds 0 and 1, then add intervention at round 2
        assert len(replayed) == 3
        assert replayed[0].round_id == 0
        assert replayed[1].round_id == 1
        assert replayed[2].round_id == 2
        assert replayed[2].state_hash == "intervention"
        assert replayed[2].metrics == {"avg_attitude": 0.3}

    def test_replay_truncates_future(self):
        config = EarlyStopConfig()
        ctrl = RuntimeControlLayer(config)

        checkpoints = [
            RoundCheckpoint(0, "h0", {"avg_attitude": 0.5}, time.time()),
            RoundCheckpoint(1, "h1", {"avg_attitude": 0.6}, time.time()),
            RoundCheckpoint(2, "h2", {"avg_attitude": 0.7}, time.time()),
            RoundCheckpoint(3, "h3", {"avg_attitude": 0.8}, time.time()),
        ]

        replayed = ctrl.replay_intervention(
            checkpoints, intervention_round=1, modified_state={"avg_attitude": 0.1}
        )
        # Should keep round 0, then add intervention at round 1
        # Rounds 2, 3 should be dropped
        assert len(replayed) == 2
        assert replayed[0].round_id == 0
        assert replayed[1].round_id == 1
        assert replayed[1].metrics == {"avg_attitude": 0.1}
