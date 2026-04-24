"""Contract tests for current consumer snapshot schema.

These tests freeze the snapshot shape, valid attitude/bucket/engagement
domain, and persona pack integrity produced by ConsumerSimulationOrchestrator
today.  The bucket contract reflects the *accepted* downstream vocabulary
for consumer scoring, reporting, and event handling — not just values the
orchestrator emits today (which are mostly resonance/risk/question).
"""

from __future__ import annotations

import json

import pytest

from app.services.consumer.models import ConsumerBusinessBrief, GraphVisibility
from app.services.consumer.orchestrator import ConsumerSimulationOrchestrator
from app.services.consumer.kernel_adapter import SimulationKernelResult
from app.services.consumer.legacy_kernel import LegacySimulationKernel
from app.services.consumer.persona_pack import (
    load_default_persona_pack,
    map_persona_to_agent_traits,
)

# ---------------------------------------------------------------------------
# Snapshot key contract
# ---------------------------------------------------------------------------

EXPECTED_SNAPSHOT_KEYS = frozenset({
    "round_num",
    "agent_id",
    "agent_name",
    "prompt",
    "visible_nodes",
    "visible_finding_ids",
    "attitude_label",
    "bucket",
    "quote",
    "engagement",
})


def test_snapshot_keys_match_contract():
    snapshot = ConsumerSimulationOrchestrator().build_round_snapshot(
        round_num=0,
        agent_traits={"search_propensity": "low", "cognition_level": "medium", "influence_weight": 0.5},
        brief_summary="Pinned BusinessBrief Summary: contract key test",
        visible_graph_nodes=[{"type": "ProductConcept", "visibility": "Initial", "text": "yogurt pouch"}],
        agent_id="M03",
        agent_name="Traditional value caretaker",
    )
    assert set(snapshot.keys()) == EXPECTED_SNAPSHOT_KEYS


def test_snapshot_round_num_is_int():
    snapshot = ConsumerSimulationOrchestrator().build_round_snapshot(
        round_num=0,
        agent_traits={"search_propensity": "low", "cognition_level": "medium", "influence_weight": 0.5},
        brief_summary="Pinned BusinessBrief Summary: type check",
        visible_graph_nodes=[],
        agent_id="M08",
        agent_name="Budget-safe minimalist",
    )
    assert isinstance(snapshot["round_num"], int)
    assert isinstance(snapshot["engagement"], int)
    assert isinstance(snapshot["visible_finding_ids"], list)
    assert isinstance(snapshot["visible_nodes"], list)
    assert isinstance(snapshot["prompt"], str)
    assert isinstance(snapshot["quote"], str)


# ---------------------------------------------------------------------------
# Valid attitude labels
# ---------------------------------------------------------------------------

VALID_ATTITUDES = frozenset({"positive", "neutral", "negative"})


def test_attitude_label_always_valid():
    orchestrator = ConsumerSimulationOrchestrator()
    test_cases = [
        {"search_propensity": "high", "cognition_level": "high", "herd_tendency": "medium", "influence_weight": 0.8},
        {"search_propensity": "low", "cognition_level": "low", "herd_tendency": "high", "influence_weight": 0.5},
        {"search_propensity": "medium", "cognition_level": "medium", "herd_tendency": "low", "influence_weight": 0.6},
    ]
    node_sets = [
        [],
        [{"type": "ProductConcept", "visibility": "Initial", "text": "yogurt"}],
        [{"type": "RiskPoint", "visibility": "Initial", "text": "sugar concern"}],
        [{"type": "TalkingPoint", "visibility": "Initial", "text": "breakfast angle"}],
    ]
    for traits in test_cases:
        for nodes in node_sets:
            snap = orchestrator.build_round_snapshot(
                round_num=0, agent_traits=traits,
                brief_summary="Pinned BusinessBrief Summary: attitude check",
                visible_graph_nodes=nodes, agent_id="M01", agent_name="Test",
            )
            assert snap["attitude_label"] in VALID_ATTITUDES, (
                f"Invalid attitude_label {snap['attitude_label']!r} for traits={traits}, nodes={nodes}"
            )


# ---------------------------------------------------------------------------
# Valid bucket values (accepted domain for downstream consumer scoring,
# reporting, and event handling — includes 'misread' even though current
# orchestrator paths mostly emit resonance/risk/question)
# ---------------------------------------------------------------------------

VALID_BUCKETS = frozenset({"resonance", "risk", "question", "misread"})


def test_bucket_always_valid():
    orchestrator = ConsumerSimulationOrchestrator()
    test_cases = [
        {"search_propensity": "high", "cognition_level": "high", "herd_tendency": "high", "influence_weight": 0.8},
        {"search_propensity": "low", "cognition_level": "medium", "herd_tendency": "medium", "influence_weight": 0.5},
    ]
    node_sets = [
        [],
        [{"type": "RiskPoint", "visibility": "Initial", "text": "allergen risk"}],
        [{"type": "TalkingPoint", "visibility": "Initial", "text": "price angle"}],
    ]
    for round_num in (0, 1, 2):
        for traits in test_cases:
            for nodes in node_sets:
                snap = orchestrator.build_round_snapshot(
                    round_num=round_num, agent_traits=traits,
                    brief_summary="Pinned BusinessBrief Summary: bucket check",
                    visible_graph_nodes=nodes, agent_id="M02", agent_name="Test",
                )
                assert snap["bucket"] in VALID_BUCKETS, (
                    f"Invalid bucket {snap['bucket']!r} for round={round_num}, traits={traits}, nodes={nodes}"
                )


# ---------------------------------------------------------------------------
# Engagement bounds
# ---------------------------------------------------------------------------

def test_engagement_within_bounds():
    orchestrator = ConsumerSimulationOrchestrator()
    personas = load_default_persona_pack()
    for round_num in range(4):
        for persona in personas:
            profile = map_persona_to_agent_traits(persona)
            snap = orchestrator.build_round_snapshot(
                round_num=round_num,
                agent_traits={
                    **profile["propagation_profile"],
                    "influence_weight": profile["influence_weight"],
                },
                brief_summary="Pinned BusinessBrief Summary: engagement check",
                visible_graph_nodes=[],
                agent_id=profile["persona_id"],
                agent_name=profile["label"],
            )
            assert 1 <= snap["engagement"] <= 10, (
                f"Engagement {snap['engagement']} out of bounds for {profile['persona_id']} round {round_num}"
            )


def test_engagement_formula_matches_current_code():
    """Verify the engagement formula: max(1, min(10, round(3 + influence_weight * 7 + round_num)))."""
    orchestrator = ConsumerSimulationOrchestrator()
    for influence_weight, round_num, expected_engagement in [
        (0.0, 0, 3),
        (0.5, 0, 6),
        (1.0, 0, 10),
        (0.52, 0, 7),
        (0.8, 0, 9),
        (0.8, 3, 10),
    ]:
        snap = orchestrator.build_round_snapshot(
            round_num=round_num,
            agent_traits={"search_propensity": "low", "cognition_level": "low", "influence_weight": influence_weight},
            brief_summary="Pinned BusinessBrief Summary: engagement formula",
            visible_graph_nodes=[],
            agent_id="M01", agent_name="Test",
        )
        assert snap["engagement"] == expected_engagement, (
            f"Expected engagement {expected_engagement} for w={influence_weight} r={round_num}, got {snap['engagement']}"
        )


# ---------------------------------------------------------------------------
# Persona pack integrity
# ---------------------------------------------------------------------------

EXPECTED_PERSONA_IDS = frozenset({"M01", "M02", "M03", "M04", "M05", "M06", "M07", "M08"})


def test_persona_pack_has_eight_personas():
    personas = load_default_persona_pack()
    assert len(personas) == 8
    ids = {p["persona_id"] for p in personas}
    assert ids == EXPECTED_PERSONA_IDS


def test_persona_trait_levels_valid():
    personas = load_default_persona_pack()
    valid_levels = {"low", "medium", "high"}
    for persona in personas:
        assert persona["search_propensity"] in valid_levels
        assert persona["cognition_level"] in valid_levels
        assert persona["herd_tendency"] in valid_levels
        assert 0.0 <= persona["influence_weight"] <= 1.0


def test_map_persona_to_agent_traits_preserves_ids():
    personas = load_default_persona_pack()
    for persona in personas:
        profile = map_persona_to_agent_traits(persona)
        assert profile["persona_id"] == persona["persona_id"]
        assert "propagation_profile" in profile
        assert "influence_weight" in profile
        assert "can_access_deep_graph" in profile


# ---------------------------------------------------------------------------
# Snapshot visible_nodes normalization
# ---------------------------------------------------------------------------

def test_visible_nodes_normalized_to_type_text_visibility():
    snapshot = ConsumerSimulationOrchestrator().build_round_snapshot(
        round_num=0,
        agent_traits={"search_propensity": "low", "cognition_level": "medium", "influence_weight": 0.5},
        brief_summary="Pinned BusinessBrief Summary: node norm",
        visible_graph_nodes=[
            {"type": "ProductConcept", "visibility": "Initial", "text": "yogurt pouch"},
            {"type": "RiskPoint", "visibility": "Initial", "text": "sugar risk"},
        ],
        agent_id="M03",
        agent_name="Test",
    )
    for node in snapshot["visible_nodes"]:
        assert set(node.keys()) == {"type", "text", "visibility"}
        assert isinstance(node["type"], str)
        assert isinstance(node["text"], str)
        assert node["visibility"] in {GraphVisibility.Initial, GraphVisibility.Propagation_Only, GraphVisibility.Restricted}


# ---------------------------------------------------------------------------
# Snapshot JSONL round-trip
# ---------------------------------------------------------------------------

def test_snapshot_survives_json_roundtrip(tmp_path):
    orchestrator = ConsumerSimulationOrchestrator()
    snapshot = orchestrator.build_round_snapshot(
        round_num=1,
        agent_traits={"search_propensity": "high", "cognition_level": "high", "herd_tendency": "low", "influence_weight": 0.76},
        brief_summary="Pinned BusinessBrief Summary: json roundtrip",
        visible_graph_nodes=[{"type": "ProductConcept", "visibility": "Initial", "text": "yogurt pouch"}],
        agent_id="M05",
        agent_name="Ingredient-first analyst",
    )
    out = tmp_path / "test_roundtrip.jsonl"
    orch2 = ConsumerSimulationOrchestrator(output_path=out)
    orch2.persist_round_snapshot(snapshot)

    loaded = json.loads(out.read_text(encoding="utf-8").splitlines()[0])
    assert loaded["round_num"] == snapshot["round_num"]
    assert loaded["agent_id"] == snapshot["agent_id"]
    assert loaded["attitude_label"] == snapshot["attitude_label"]
    assert loaded["bucket"] == snapshot["bucket"]
    assert loaded["engagement"] == snapshot["engagement"]


# ===========================================================================
# Task 2 — SimulationKernelResult validation
# ===========================================================================


class TestSimulationKernelResultValidation:
    def test_valid_construction(self):
        r = SimulationKernelResult(
            attitude_label="positive", bucket="resonance", quote="ok", engagement=5,
        )
        assert r.engagement == 5

    def test_invalid_attitude_label_raises(self):
        with pytest.raises(ValueError, match="attitude_label"):
            SimulationKernelResult(
                attitude_label="excited", bucket="resonance", quote="q", engagement=5,
            )

    def test_invalid_bucket_raises(self):
        with pytest.raises(ValueError, match="bucket"):
            SimulationKernelResult(
                attitude_label="positive", bucket="unknown", quote="q", engagement=5,
            )

    def test_engagement_zero_raises(self):
        with pytest.raises(ValueError, match="engagement"):
            SimulationKernelResult(
                attitude_label="positive", bucket="resonance", quote="q", engagement=0,
            )

    def test_engagement_eleven_raises(self):
        with pytest.raises(ValueError, match="engagement"):
            SimulationKernelResult(
                attitude_label="positive", bucket="resonance", quote="q", engagement=11,
            )

    def test_engagement_boundary_1_ok(self):
        r = SimulationKernelResult(
            attitude_label="neutral", bucket="question", quote="q", engagement=1,
        )
        assert r.engagement == 1

    def test_engagement_boundary_10_ok(self):
        r = SimulationKernelResult(
            attitude_label="negative", bucket="risk", quote="q", engagement=10,
        )
        assert r.engagement == 10

    def test_all_valid_buckets_accepted(self):
        for b in ("resonance", "risk", "question", "misread"):
            r = SimulationKernelResult(
                attitude_label="neutral", bucket=b, quote="q", engagement=5,
            )
            assert r.bucket == b

    def test_all_valid_attitudes_accepted(self):
        for a in ("positive", "neutral", "negative"):
            r = SimulationKernelResult(
                attitude_label=a, bucket="question", quote="q", engagement=5,
            )
            assert r.attitude_label == a


# ===========================================================================
# Task 2 — LegacySimulationKernel behavior & parity
# ===========================================================================


class TestLegacySimulationKernelBehavior:
    kernel = LegacySimulationKernel()
    _base_traits = {"influence_weight": 0.5, "herd_tendency": "medium"}

    def test_risk_nodes_yield_negative_risk(self):
        nodes = [{"type": "RiskPoint", "text": "allergen concern"}]
        r = self.kernel.generate_response(
            round_num=1, agent_traits=self._base_traits, visible_nodes=nodes,
        )
        assert r.attitude_label == "negative"
        assert r.bucket == "risk"

    def test_round_ge1_high_herd_yields_positive_resonance(self):
        nodes = [{"type": "TalkingPoint", "text": "price angle"}]
        traits = {**self._base_traits, "herd_tendency": "high"}
        r = self.kernel.generate_response(
            round_num=1, agent_traits=traits, visible_nodes=nodes,
        )
        assert r.attitude_label == "positive"
        assert r.bucket == "resonance"

    def test_round_ge1_low_herd_yields_neutral_question(self):
        nodes = [{"type": "TalkingPoint", "text": "price angle"}]
        traits = {**self._base_traits, "herd_tendency": "low"}
        r = self.kernel.generate_response(
            round_num=1, agent_traits=traits, visible_nodes=nodes,
        )
        assert r.attitude_label == "neutral"
        assert r.bucket == "question"

    def test_initial_talking_nodes_yield_positive_resonance(self):
        nodes = [{"type": "TalkingPoint", "text": "breakfast angle"}]
        r = self.kernel.generate_response(
            round_num=0, agent_traits=self._base_traits, visible_nodes=nodes,
        )
        assert r.attitude_label == "positive"
        assert r.bucket == "resonance"

    def test_empty_nodes_yield_neutral_question(self):
        r = self.kernel.generate_response(
            round_num=0, agent_traits=self._base_traits, visible_nodes=[],
        )
        assert r.attitude_label == "neutral"
        assert r.bucket == "question"


class TestLegacyKernelEngagementParity:
    kernel = LegacySimulationKernel()

    @pytest.mark.parametrize(
        "influence_weight, round_num, expected",
        [
            (0.0, 0, 3),
            (0.5, 0, 6),
            (1.0, 0, 10),
            (0.52, 0, 7),
            (0.8, 0, 9),
            (0.8, 3, 10),
        ],
    )
    def test_compute_engagement_formula(self, influence_weight, round_num, expected):
        assert self.kernel.compute_engagement(influence_weight, round_num) == expected

    def test_generate_response_engagement_matches_compute(self):
        nodes = [{"type": "TalkingPoint", "text": "topic"}]
        traits = {"influence_weight": 0.6, "herd_tendency": "medium"}
        r = self.kernel.generate_response(
            round_num=2, agent_traits=traits, visible_nodes=nodes,
        )
        expected = self.kernel.compute_engagement(0.6, 2)
        assert r.engagement == expected

    def test_engagement_always_in_bounds(self):
        for w in (0.0, 0.5, 1.0):
            for rnd in range(5):
                e = self.kernel.compute_engagement(w, rnd)
                assert 1 <= e <= 10
