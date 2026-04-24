"""Unit tests for PropagationState round-to-round memory."""

from __future__ import annotations

import pytest

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
