"""Tests for consumer research actions API endpoint (Phase 6F)."""

from unittest.mock import patch

import pytest

from app import create_app


def _make_unified_response(action_type="deep_dive_conclusion"):
    """Return a valid Phase 6F unified response shape."""
    return {
        "action_type": action_type,
        "simulation_id": "sim_1",
        "target": {"kind": "finding", "id": "f1", "text": "claim"},
        "title": "Test Title",
        "summary": "test summary",
        "details_markdown": "test details",
        "evidence": {
            "support_level": "medium",
            "source_count": 0,
            "simulation_quote_count": 0,
            "gatekeeping_status": "pending",
        },
        "tool_trace": {
            "tool_name": "insight_forge",
            "consumer_tool_label": "消费者洞察深挖",
            "query": "claim",
        },
        "handoff": {
            "handoff_type": "",
            "target_context": {},
        },
    }


class TestConsumerResearchActionsAPI:
    @pytest.fixture
    def client(self):
        app = create_app()
        app.config["TESTING"] = True
        with app.test_client() as client:
            yield client

    def test_run_research_action_success(self, client):
        with patch(
            "app.api.consumer.ConsumerResearchActionService.run_action"
        ) as mock_run:
            mock_run.return_value = _make_unified_response("deep_dive_conclusion")
            resp = client.post(
                "/api/consumer/simulations/sim_1/research-actions",
                json={"action_type": "deep_dive_conclusion", "target": {"text": "claim"}},
            )
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["success"] is True
            result = data["data"]
            # Assert unified shape inside data
            assert "success" not in result
            assert "result" not in result
            assert result["action_type"] == "deep_dive_conclusion"
            assert result["simulation_id"] == "sim_1"
            assert isinstance(result["target"], dict)
            assert "title" in result
            assert "summary" in result
            assert "details_markdown" in result
            assert "support_level" in result["evidence"]
            assert "tool_name" in result["tool_trace"]
            assert "handoff_type" in result["handoff"]

    def test_run_research_action_missing_simulation(self, client):
        with patch(
            "app.api.consumer.ConsumerResearchActionService.run_action"
        ) as mock_run:
            mock_run.side_effect = ValueError("Simulation not found: sim_missing")
            resp = client.post(
                "/api/consumer/simulations/sim_missing/research-actions",
                json={"action_type": "deep_dive_conclusion", "target": {"text": "claim"}},
            )
            assert resp.status_code == 404
            data = resp.get_json()
            assert data["success"] is False

    def test_run_research_action_bad_input(self, client):
        with patch(
            "app.api.consumer.ConsumerResearchActionService.run_action"
        ) as mock_run:
            mock_run.side_effect = ValueError("action_type is required")
            resp = client.post(
                "/api/consumer/simulations/sim_1/research-actions",
                json={"target": {"text": "claim"}},
            )
            assert resp.status_code == 400
            data = resp.get_json()
            assert data["success"] is False

    def test_run_research_action_unknown_action(self, client):
        with patch(
            "app.api.consumer.ConsumerResearchActionService.run_action"
        ) as mock_run:
            mock_run.side_effect = ValueError("Unknown action_type: magic")
            resp = client.post(
                "/api/consumer/simulations/sim_1/research-actions",
                json={"action_type": "magic", "target": {"text": "claim"}},
            )
            assert resp.status_code == 400
            data = resp.get_json()
            assert data["success"] is False

    def test_run_research_action_non_consumer_simulation(self, client):
        with patch(
            "app.api.consumer.ConsumerResearchActionService.run_action"
        ) as mock_run:
            mock_run.side_effect = ValueError("not a consumer_test simulation")
            resp = client.post(
                "/api/consumer/simulations/sim_1/research-actions",
                json={"action_type": "deep_dive_conclusion", "target": {"text": "claim"}},
            )
            assert resp.status_code == 400
            data = resp.get_json()
            assert data["success"] is False

    def test_run_research_action_branch_conflict(self, client):
        with patch(
            "app.api.consumer.ConsumerResearchActionService.run_action"
        ) as mock_run:
            mock_run.side_effect = ValueError("Branch is already running")
            resp = client.post(
                "/api/consumer/simulations/sim_1/research-actions",
                json={
                    "action_type": "compare_branch_delta",
                    "target": {"kind": "branch", "id": "b1"},
                },
            )
            assert resp.status_code == 409
            data = resp.get_json()
            assert data["success"] is False

    def test_run_research_action_unexpected_error(self, client):
        with patch(
            "app.api.consumer.ConsumerResearchActionService.run_action"
        ) as mock_run:
            mock_run.side_effect = RuntimeError("Zep connection failed")
            resp = client.post(
                "/api/consumer/simulations/sim_1/research-actions",
                json={"action_type": "deep_dive_conclusion", "target": {"text": "claim"}},
            )
            assert resp.status_code == 500
            data = resp.get_json()
            assert data["success"] is False
            assert "traceback" not in data
