"""Unit tests for PropagationState and HybridSimulationKernel."""

from __future__ import annotations

import pytest

from app.services.consumer.hybrid_kernel import HybridSimulationKernel
from app.services.consumer.kernel_adapter import (
    VALID_ATTITUDE_LABELS,
    VALID_BUCKETS,
    SimulationKernelResult,
)
from app.services.consumer.legacy_kernel import LegacySimulationKernel
from app.services.consumer.propagation_state import (
    PropagationState,
    create_initial_state,
)


# ---------------------------------------------------------------------------
# create_initial_state
# ---------------------------------------------------------------------------


class TestCreateInitialState:
    def test_empty_histories_and_zero_counters(self) -> None:
        state = create_initial_state("agent-1")
        assert state.agent_id == "agent-1"
        assert state.attitude_history == []
        assert state.engagement_history == []
        assert state.cumulative_risk_exposure == 0
        assert state.social_reinforcement_count == 0
        assert state.last_bucket == ""
        assert state.rounds_seen_propagation_only == 0


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------


class TestUpdate:
    def test_tracks_attitude_and_engagement_histories(self) -> None:
        state = create_initial_state("a1")
        state.update("positive", 7, "resonance", [])
        state.update("negative", 3, "risk", [])
        assert state.attitude_history == ["positive", "negative"]
        assert state.engagement_history == [7, 3]
        assert state.last_bucket == "risk"

    def test_risk_exposure_accumulates_by_riskpoint_count(self) -> None:
        state = create_initial_state("a1")
        nodes = [
            {"type": "RiskPoint", "visibility": "Initial", "text": "sugar"},
            {"type": "TalkingPoint", "visibility": "Initial", "text": "taste"},
            {"type": "RiskPoint", "visibility": "Propagation_Only", "text": "allergen"},
        ]
        state.update("neutral", 5, "question", nodes)
        assert state.cumulative_risk_exposure == 2

        state.update("negative", 4, "risk", [
            {"type": "RiskPoint", "visibility": "Restricted", "text": "recall"},
        ])
        assert state.cumulative_risk_exposure == 3

    def test_propagation_only_increments_when_all_propagation_only(self) -> None:
        state = create_initial_state("a1")
        po_nodes = [
            {"type": "TalkingPoint", "visibility": "Propagation_Only", "text": "buzz"},
            {"type": "RiskPoint", "visibility": "Propagation_Only", "text": "leak"},
        ]
        state.update("positive", 6, "resonance", po_nodes)
        assert state.rounds_seen_propagation_only == 1

    def test_propagation_only_does_not_increment_when_mixed(self) -> None:
        state = create_initial_state("a1")
        mixed = [
            {"type": "TalkingPoint", "visibility": "Propagation_Only", "text": "buzz"},
            {"type": "RiskPoint", "visibility": "Initial", "text": "risk"},
        ]
        state.update("positive", 6, "resonance", mixed)
        assert state.rounds_seen_propagation_only == 0

    def test_propagation_only_does_not_increment_on_empty_list(self) -> None:
        state = create_initial_state("a1")
        state.update("neutral", 5, "question", [])
        assert state.rounds_seen_propagation_only == 0

    def test_resonance_increments_social_reinforcement_count(self) -> None:
        state = create_initial_state("a1")
        state.update("positive", 8, "resonance", [])
        state.update("positive", 7, "resonance", [])
        state.update("negative", 3, "risk", [])
        assert state.social_reinforcement_count == 2


# ---------------------------------------------------------------------------
# to_prior_state_dict
# ---------------------------------------------------------------------------


class TestToPriorStateDict:
    def test_returns_expected_plain_structure(self) -> None:
        state = create_initial_state("a1")
        state.update("positive", 7, "resonance", [
            {"type": "RiskPoint", "visibility": "Propagation_Only", "text": "x"},
        ])
        d = state.to_prior_state_dict()
        assert d == {
            "agent_id": "a1",
            "attitude_history": ["positive"],
            "engagement_history": [7],
            "cumulative_risk_exposure": 1,
            "social_reinforcement_count": 1,
            "last_bucket": "resonance",
            "rounds_seen_propagation_only": 1,
        }
        # Verify it's a plain dict, not a dataclass reference
        assert isinstance(d, dict)
        assert isinstance(d["attitude_history"], list)
        assert isinstance(d["engagement_history"], list)


# ---------------------------------------------------------------------------
# HybridSimulationKernel – core tests
# ---------------------------------------------------------------------------

_TALKING_NODE = {"type": "TalkingPoint", "visibility": "Initial", "text": "great taste"}
_RISK_NODE = {"type": "RiskPoint", "visibility": "Initial", "text": "high sugar"}


def _make_prior_state(agent_id: str, **overrides: object) -> dict:
    """Build a minimal prior_state dict for the hybrid kernel."""
    base = {
        "agent_id": agent_id,
        "attitude_history": [],
        "engagement_history": [],
        "cumulative_risk_exposure": 0,
        "social_reinforcement_count": 0,
        "last_bucket": "",
        "rounds_seen_propagation_only": 0,
    }
    base.update(overrides)
    return base


class TestQuoteVarietyAcrossAgents:
    """Different agent_id values in prior_state produce different quotes."""

    def test_different_agents_different_quotes(self) -> None:
        kernel = HybridSimulationKernel()
        traits = {"influence_weight": 0.5}
        prior_a = _make_prior_state("agent-alpha")
        prior_b = _make_prior_state("agent-beta")
        r_a = kernel.generate_response(1, traits, [_TALKING_NODE], prior_a)
        r_b = kernel.generate_response(1, traits, [_TALKING_NODE], prior_b)
        # At least one pair must differ across a sample of 3 agent ids
        prior_c = _make_prior_state("agent-gamma")
        r_c = kernel.generate_response(1, traits, [_TALKING_NODE], prior_c)
        quotes = {r_a.quote, r_b.quote, r_c.quote}
        assert len(quotes) > 1, "Expected different quotes across agents"


class TestQuoteVariationAcrossRounds:
    """Same agent but different round_num produces different quotes."""

    def test_different_rounds_different_quotes(self) -> None:
        kernel = HybridSimulationKernel()
        traits = {"influence_weight": 0.5}
        prior = _make_prior_state("agent-1")
        quotes = set()
        for rnd in range(5):
            r = kernel.generate_response(rnd, traits, [_TALKING_NODE], prior)
            quotes.add(r.quote)
        assert len(quotes) > 1, "Expected quote variation across rounds"


class TestPriorStateNoneParityWithLegacy:
    """HybridSimulationKernel with prior_state=None matches LegacySimulationKernel."""

    @pytest.fixture()
    def hybrid(self) -> HybridSimulationKernel:
        return HybridSimulationKernel()

    @pytest.fixture()
    def legacy(self) -> LegacySimulationKernel:
        return LegacySimulationKernel()

    def _assert_parity(
        self,
        hybrid: HybridSimulationKernel,
        legacy: LegacySimulationKernel,
        round_num: int,
        traits: dict,
        nodes: list,
    ) -> None:
        h = hybrid.generate_response(round_num, traits, nodes, prior_state=None)
        l = legacy.generate_response(round_num, traits, nodes, prior_state=None)
        assert h.attitude_label == l.attitude_label
        assert h.bucket == l.bucket
        assert h.quote == l.quote
        assert h.engagement == l.engagement

    def test_risk_only(self, hybrid: HybridSimulationKernel, legacy: LegacySimulationKernel) -> None:
        self._assert_parity(hybrid, legacy, 0, {"influence_weight": 0.5}, [_RISK_NODE])

    def test_round0_talking_node(self, hybrid: HybridSimulationKernel, legacy: LegacySimulationKernel) -> None:
        self._assert_parity(hybrid, legacy, 0, {"influence_weight": 0.5}, [_TALKING_NODE])

    def test_round1_herd_high(self, hybrid: HybridSimulationKernel, legacy: LegacySimulationKernel) -> None:
        self._assert_parity(
            hybrid, legacy, 1, {"influence_weight": 0.5, "herd_tendency": "high"}, [_TALKING_NODE]
        )

    def test_round1_herd_medium(self, hybrid: HybridSimulationKernel, legacy: LegacySimulationKernel) -> None:
        self._assert_parity(
            hybrid, legacy, 1, {"influence_weight": 0.5, "herd_tendency": "medium"}, [_TALKING_NODE]
        )

    def test_empty_visible_nodes(self, hybrid: HybridSimulationKernel, legacy: LegacySimulationKernel) -> None:
        self._assert_parity(hybrid, legacy, 0, {"influence_weight": 0.5}, [])


class TestThresholdCumulativeRisk:
    """cumulative_risk_exposure >= 2 pushes non-risk base positive/neutral to negative/risk."""

    @pytest.mark.parametrize(
        "round_num,traits,nodes,expected_base_bucket",
        [
            # round 0, talking node → base positive/resonance
            (0, {"influence_weight": 0.5}, [_TALKING_NODE], "resonance"),
            # round 1, herd=medium → base neutral/question
            (1, {"influence_weight": 0.5, "herd_tendency": "medium"}, [_TALKING_NODE], "question"),
        ],
    )
    def test_risk_exposure_flips_to_negative_risk(
        self, round_num: int, traits: dict, nodes: list, expected_base_bucket: str
    ) -> None:
        kernel = HybridSimulationKernel()
        prior = _make_prior_state("agent-risk", cumulative_risk_exposure=2)
        result = kernel.generate_response(round_num, traits, nodes, prior)
        assert result.attitude_label == "negative"
        assert result.bucket == "risk"

    def test_risk_exposure_1_does_not_flip(self) -> None:
        kernel = HybridSimulationKernel()
        prior = _make_prior_state("agent-risk-low", cumulative_risk_exposure=1)
        result = kernel.generate_response(0, {"influence_weight": 0.5}, [_TALKING_NODE], prior)
        # exposure=1 is below threshold, base positive/resonance stays
        assert result.attitude_label == "positive"
        assert result.bucket == "resonance"


class TestThresholdSocialReinforcement:
    """social_reinforcement_count >= 3 pushes neutral/question base to positive/resonance."""

    def test_social_reinforcement_flips_neutral_to_positive(self) -> None:
        kernel = HybridSimulationKernel()
        # round 1, herd=medium → base neutral/question
        prior = _make_prior_state("agent-social", social_reinforcement_count=3)
        result = kernel.generate_response(
            1, {"influence_weight": 0.5, "herd_tendency": "medium"}, [_TALKING_NODE], prior
        )
        assert result.attitude_label == "positive"
        assert result.bucket == "resonance"

    def test_social_reinforcement_2_does_not_flip(self) -> None:
        kernel = HybridSimulationKernel()
        prior = _make_prior_state("agent-social-low", social_reinforcement_count=2)
        result = kernel.generate_response(
            1, {"influence_weight": 0.5, "herd_tendency": "medium"}, [_TALKING_NODE], prior
        )
        assert result.attitude_label == "neutral"
        assert result.bucket == "question"


class TestThresholdPropagationOnly:
    """rounds_seen_propagation_only >= 3 converts neutral/question into neutral/misread."""

    def test_propagation_only_flips_question_to_misread(self) -> None:
        kernel = HybridSimulationKernel()
        # round 1, herd=medium → base neutral/question
        prior = _make_prior_state("agent-prop", rounds_seen_propagation_only=3)
        result = kernel.generate_response(
            1, {"influence_weight": 0.5, "herd_tendency": "medium"}, [_TALKING_NODE], prior
        )
        assert result.attitude_label == "neutral"
        assert result.bucket == "misread"

    def test_propagation_only_2_does_not_flip(self) -> None:
        kernel = HybridSimulationKernel()
        prior = _make_prior_state("agent-prop-low", rounds_seen_propagation_only=2)
        result = kernel.generate_response(
            1, {"influence_weight": 0.5, "herd_tendency": "medium"}, [_TALKING_NODE], prior
        )
        assert result.attitude_label == "neutral"
        assert result.bucket == "question"


class TestNoRiskPointAntiOverfit:
    """No RiskPoint nodes with non-risk prior_state counters should not drift to negative."""

    @pytest.mark.parametrize(
        "overrides",
        [
            {"social_reinforcement_count": 5, "rounds_seen_propagation_only": 5},
            {"social_reinforcement_count": 10, "rounds_seen_propagation_only": 10},
        ],
    )
    def test_non_risk_counters_do_not_cause_negative_drift(self, overrides: dict) -> None:
        kernel = HybridSimulationKernel()
        prior = _make_prior_state("agent-nodrift", cumulative_risk_exposure=0, **overrides)
        result = kernel.generate_response(0, {"influence_weight": 0.5}, [_TALKING_NODE], prior)
        # round 0 with talking node → base positive/resonance, no risk exposure
        assert result.attitude_label != "negative", (
            f"Unexpected negative drift with overrides={overrides}"
        )


class TestSchemaValuesAndEngagementRange:
    """Output schema values are always valid and engagement stays in 1..10."""

    @pytest.mark.parametrize(
        "round_num,traits,nodes",
        [
            (0, {"influence_weight": 0.0}, []),
            (0, {"influence_weight": 1.0}, [_RISK_NODE]),
            (1, {"influence_weight": 0.5, "herd_tendency": "high"}, [_TALKING_NODE]),
            (5, {"influence_weight": 0.8}, [_TALKING_NODE]),
            (0, {"influence_weight": 0.5}, [_TALKING_NODE]),
        ],
    )
    def test_prior_state_none_schema(self, round_num: int, traits: dict, nodes: list) -> None:
        kernel = HybridSimulationKernel()
        result = kernel.generate_response(round_num, traits, nodes, prior_state=None)
        assert result.attitude_label in VALID_ATTITUDE_LABELS
        assert result.bucket in VALID_BUCKETS
        assert 1 <= result.engagement <= 10

    @pytest.mark.parametrize(
        "overrides",
        [
            {"cumulative_risk_exposure": 5},
            {"social_reinforcement_count": 6},
            {"rounds_seen_propagation_only": 4},
            {"cumulative_risk_exposure": 10, "social_reinforcement_count": 10},
        ],
    )
    def test_prior_state_schema(self, overrides: dict) -> None:
        kernel = HybridSimulationKernel()
        traits = {"influence_weight": 0.5}
        prior = _make_prior_state("agent-x", **overrides)
        result = kernel.generate_response(1, traits, [_TALKING_NODE], prior)
        assert result.attitude_label in VALID_ATTITUDE_LABELS
        assert result.bucket in VALID_BUCKETS
        assert 1 <= result.engagement <= 10
