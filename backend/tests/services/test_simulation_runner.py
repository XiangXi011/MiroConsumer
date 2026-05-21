"""Tests for simulation_runner core logic."""

from __future__ import annotations

import json
import os
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from app.services.simulation_ipc import SimulationIPCClient
from app.services.simulation_runner import (
    AgentAction,
    RoundSummary,
    RunnerStatus,
    SimulationRunner,
    SimulationRunState,
)


class TestRunnerStatus:
    """Test RunnerStatus enum."""

    def test_status_values(self):
        """RunnerStatus has expected values."""
        assert RunnerStatus.IDLE == "idle"
        assert RunnerStatus.RUNNING == "running"
        assert RunnerStatus.COMPLETED == "completed"
        assert RunnerStatus.FAILED == "failed"
        assert RunnerStatus.STOPPING == "stopping"
        assert RunnerStatus.STOPPED == "stopped"


class TestAgentAction:
    """Test AgentAction dataclass."""

    def test_to_dict(self):
        """AgentAction serializes to dict correctly."""
        action = AgentAction(
            round_num=1,
            timestamp="2024-01-01T00:00:00",
            platform="reddit",
            agent_id=0,
            agent_name="Test Agent",
            action_type="CONSUMER_REACTION",
            action_args={"key": "value"},
            result="test result",
            success=True,
        )
        d = action.to_dict()
        assert d["round_num"] == 1
        assert d["platform"] == "reddit"
        assert d["agent_name"] == "Test Agent"
        assert d["action_args"] == {"key": "value"}
        assert d["result"] == "test result"
        assert d["success"] is True

    def test_defaults(self):
        """AgentAction has correct default values."""
        action = AgentAction(
            round_num=0,
            timestamp=datetime.now().isoformat(),
            platform="twitter",
            agent_id=0,
            agent_name="A",
            action_type="TEST",
        )
        assert action.action_args == {}
        assert action.result is None
        assert action.success is True


class TestRoundSummary:
    """Test RoundSummary dataclass."""

    def test_to_dict(self):
        """RoundSummary serializes to dict correctly."""
        summary = RoundSummary(
            round_num=0,
            start_time="2024-01-01T00:00:00",
            end_time="2024-01-01T00:01:00",
            simulated_hour=1,
            twitter_actions=2,
            reddit_actions=3,
            active_agents=[0, 1],
        )
        d = summary.to_dict()
        assert d["round_num"] == 0
        assert d["simulated_hour"] == 1
        assert d["twitter_actions"] == 2
        assert d["reddit_actions"] == 3
        assert d["actions_count"] == 0
        assert d["active_agents"] == [0, 1]

    def test_with_actions(self):
        """RoundSummary counts actions correctly."""
        action = AgentAction(
            round_num=0,
            timestamp="2024-01-01T00:00:00",
            platform="reddit",
            agent_id=0,
            agent_name="A",
            action_type="TEST",
        )
        summary = RoundSummary(
            round_num=0,
            start_time="2024-01-01T00:00:00",
            actions=[action],
        )
        d = summary.to_dict()
        assert d["actions_count"] == 1
        assert len(d["actions"]) == 1


class TestSimulationRunState:
    """Test SimulationRunState dataclass."""

    def test_initial_state(self):
        """RunState initializes with correct defaults."""
        state = SimulationRunState(simulation_id="sim_123")
        assert state.simulation_id == "sim_123"
        assert state.runner_status == RunnerStatus.IDLE
        assert state.current_round == 0
        assert state.total_rounds == 0
        assert state.twitter_actions_count == 0
        assert state.reddit_actions_count == 0
        assert state.recent_actions == []
        assert state.error is None

    def test_add_action(self):
        """Adding action updates state correctly."""
        state = SimulationRunState(simulation_id="sim_123")
        action = AgentAction(
            round_num=0,
            timestamp="2024-01-01T00:00:00",
            platform="reddit",
            agent_id=0,
            agent_name="A",
            action_type="TEST",
        )
        state.add_action(action)
        assert len(state.recent_actions) == 1
        assert state.reddit_actions_count == 1

    def test_add_action_twitter(self):
        """Adding twitter action updates correct counter."""
        state = SimulationRunState(simulation_id="sim_123")
        action = AgentAction(
            round_num=0,
            timestamp="2024-01-01T00:00:00",
            platform="twitter",
            agent_id=0,
            agent_name="A",
            action_type="TEST",
        )
        state.add_action(action)
        assert state.twitter_actions_count == 1
        assert state.reddit_actions_count == 0

    def test_to_dict(self):
        """RunState serializes to dict correctly."""
        state = SimulationRunState(
            simulation_id="sim_123",
            runner_status=RunnerStatus.RUNNING,
            current_round=5,
            total_rounds=10,
        )
        d = state.to_dict()
        assert d["simulation_id"] == "sim_123"
        assert d["runner_status"] == "running"
        assert d["current_round"] == 5
        assert d["total_rounds"] == 10
        assert d["progress_percent"] == 50.0

    def test_to_detail_dict(self):
        """RunState detail dict includes recent actions."""
        state = SimulationRunState(simulation_id="sim_123")
        state.add_action(
            AgentAction(
                round_num=0,
                timestamp="2024-01-01T00:00:00",
                platform="reddit",
                agent_id=0,
                agent_name="A",
                action_type="TEST",
            )
        )
        d = state.to_detail_dict()
        assert "recent_actions" in d
        assert d["rounds_count"] == 0

    def test_recent_actions_limit(self):
        """Recent actions respects max limit."""
        state = SimulationRunState(simulation_id="sim_123")
        state.max_recent_actions = 3
        for i in range(5):
            state.add_action(
                AgentAction(
                    round_num=i,
                    timestamp=f"2024-01-01T00:0{i}:00",
                    platform="reddit",
                    agent_id=0,
                    agent_name="A",
                    action_type="TEST",
                )
            )
        assert len(state.recent_actions) == 3


class TestSimulationRunnerStateIO:
    """Test SimulationRunner state persistence."""

    def test_load_run_state_missing(self, tmp_path, monkeypatch):
        """Loading missing state returns None."""
        monkeypatch.setattr(
            SimulationRunner, "RUN_STATE_DIR", str(tmp_path / "simulations")
        )
        SimulationRunner._run_states.clear()
        result = SimulationRunner._load_run_state("nonexistent")
        assert result is None

    def test_save_and_load_run_state(self, tmp_path, monkeypatch):
        """Saved state can be loaded back."""
        monkeypatch.setattr(
            SimulationRunner, "RUN_STATE_DIR", str(tmp_path / "simulations")
        )
        SimulationRunner._run_states.clear()

        state = SimulationRunState(
            simulation_id="sim_test",
            runner_status=RunnerStatus.COMPLETED,
            current_round=3,
            total_rounds=5,
        )
        SimulationRunner._save_run_state(state)

        loaded = SimulationRunner._load_run_state("sim_test")
        assert loaded is not None
        assert loaded.simulation_id == "sim_test"
        assert loaded.runner_status == RunnerStatus.COMPLETED
        assert loaded.current_round == 3

    def test_get_run_state_from_memory(self, tmp_path, monkeypatch):
        """get_run_state returns state from memory when available."""
        monkeypatch.setattr(
            SimulationRunner, "RUN_STATE_DIR", str(tmp_path / "simulations")
        )
        SimulationRunner._run_states.clear()

        state = SimulationRunState(simulation_id="sim_mem")
        SimulationRunner._run_states["sim_mem"] = state

        result = SimulationRunner.get_run_state("sim_mem")
        assert result is not None
        assert result.simulation_id == "sim_mem"


class TestSimulationRunnerStart:
    """Test SimulationRunner.start_simulation validation."""

    def test_start_missing_config_raises(self, tmp_path, monkeypatch):
        """Starting simulation without config raises ValueError."""
        monkeypatch.setattr(
            SimulationRunner, "RUN_STATE_DIR", str(tmp_path / "simulations")
        )
        SimulationRunner._run_states.clear()

        with pytest.raises(ValueError, match="请先调用 /prepare 接口"):
            SimulationRunner.start_simulation("sim_no_config")


class TestSimulationRunnerHelpers:
    """Test SimulationRunner helper methods."""

    def test_check_all_platforms_completed_no_logs(self, tmp_path, monkeypatch):
        """Check completion when no log files exist."""
        monkeypatch.setattr(
            SimulationRunner, "RUN_STATE_DIR", str(tmp_path / "simulations")
        )
        sim_dir = tmp_path / "simulations" / "sim_complete"
        sim_dir.mkdir(parents=True)

        state = SimulationRunState(simulation_id="sim_complete")
        result = SimulationRunner._check_all_platforms_completed(state)
        # No platforms enabled, so at-least-one check returns False
        assert result is False

    def test_cleanup_simulation_logs_missing_dir(self, tmp_path, monkeypatch):
        """Cleanup on missing dir returns success message."""
        monkeypatch.setattr(
            SimulationRunner, "RUN_STATE_DIR", str(tmp_path / "simulations")
        )
        result = SimulationRunner.cleanup_simulation_logs("sim_missing")
        assert result["success"] is True

    def test_cleanup_simulation_logs(self, tmp_path, monkeypatch):
        """Cleanup removes log files."""
        monkeypatch.setattr(
            SimulationRunner, "RUN_STATE_DIR", str(tmp_path / "simulations")
        )
        sim_dir = tmp_path / "simulations" / "sim_clean"
        sim_dir.mkdir(parents=True)
        (sim_dir / "run_state.json").write_text("{}")
        (sim_dir / "simulation.log").write_text("log")

        SimulationRunner._run_states["sim_clean"] = SimulationRunState(
            simulation_id="sim_clean"
        )

        result = SimulationRunner.cleanup_simulation_logs("sim_clean")
        assert result["success"] is True
        assert "run_state.json" in result["cleaned_files"]
        assert "simulation.log" in result["cleaned_files"]
        assert "sim_clean" not in SimulationRunner._run_states

    def test_read_actions_from_file_missing(self):
        """Reading from missing file returns empty list."""
        actions = SimulationRunner._read_actions_from_file("/nonexistent/path")
        assert actions == []

    def test_read_actions_from_file(self, tmp_path):
        """Reading from valid actions file."""
        actions_file = tmp_path / "actions.jsonl"
        actions_file.write_text(
            json.dumps(
                {
                    "round": 0,
                    "timestamp": "2024-01-01T00:00:00",
                    "agent_id": 0,
                    "agent_name": "A",
                    "action_type": "TEST",
                    "platform": "reddit",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        actions = SimulationRunner._read_actions_from_file(str(actions_file))
        assert len(actions) == 1
        assert actions[0].agent_name == "A"
        assert actions[0].action_type == "TEST"

    def test_read_actions_skips_events(self, tmp_path):
        """Reading skips event_type entries."""
        actions_file = tmp_path / "actions.jsonl"
        actions_file.write_text(
            json.dumps({"event_type": "simulation_start"})
            + "\n"
            + json.dumps(
                {
                    "round": 0,
                    "timestamp": "2024-01-01T00:00:00",
                    "agent_id": 0,
                    "agent_name": "A",
                    "action_type": "TEST",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        actions = SimulationRunner._read_actions_from_file(str(actions_file))
        assert len(actions) == 1
        assert actions[0].action_type == "TEST"

    def test_get_timeline_empty(self, tmp_path, monkeypatch):
        """Timeline for simulation with no actions is empty."""
        monkeypatch.setattr(
            SimulationRunner, "RUN_STATE_DIR", str(tmp_path / "simulations")
        )
        timeline = SimulationRunner.get_timeline("sim_empty")
        assert timeline == []

    def test_get_agent_stats_empty(self, tmp_path, monkeypatch):
        """Agent stats for simulation with no actions is empty."""
        monkeypatch.setattr(
            SimulationRunner, "RUN_STATE_DIR", str(tmp_path / "simulations")
        )
        stats = SimulationRunner.get_agent_stats("sim_empty")
        assert stats == []


class TestSimulationRunnerCleanup:
    """Test SimulationRunner cleanup methods."""

    def test_cleanup_all_simulations_idempotent(self):
        """cleanup_all is safe to call multiple times."""
        SimulationRunner._cleanup_done = False
        SimulationRunner._processes.clear()
        SimulationRunner._graph_memory_enabled.clear()

        # Should not raise
        SimulationRunner.cleanup_all_simulations()
        # Second call with flag set should early-return
        SimulationRunner.cleanup_all_simulations()
