from unittest.mock import patch

from app import create_app


def test_representative_agents_interview_and_focus_group_routes_return_success():
    app = create_app()
    app.config["TESTING"] = True

    with app.test_client() as client:
        with patch("app.api.consumer.ConsumerAppService.list_representative_agents") as reps, patch(
            "app.api.consumer.ConsumerAppService.run_consumer_interview"
        ) as interview, patch("app.api.consumer.ConsumerAppService.run_focus_group") as focus:
            reps.return_value = {"items": [{"agent_id": "agent-1"}]}
            interview.return_value = {"interview_id": "interview-1", "answers": []}
            focus.return_value = {"focus_group_id": "focus-1", "turns": []}

            reps_resp = client.get("/api/consumer/simulations/sim-1/representative-agents")
            interview_resp = client.post(
                "/api/consumer/simulations/sim-1/interviews",
                json={"topic": "proof", "questions": ["why"], "mode": "snapshot"},
            )
            focus_resp = client.post(
                "/api/consumer/simulations/sim-1/focus-groups",
                json={"topic": "proof", "moderator_goal": "find disagreement"},
            )

    assert reps_resp.status_code == 200
    assert reps_resp.get_json()["data"]["items"][0]["agent_id"] == "agent-1"
    assert interview_resp.status_code == 200
    assert interview_resp.get_json()["data"]["interview_id"] == "interview-1"
    assert focus_resp.status_code == 200
    assert focus_resp.get_json()["data"]["focus_group_id"] == "focus-1"


def test_interview_route_maps_live_mode_unavailable_to_409():
    app = create_app()
    app.config["TESTING"] = True

    with app.test_client() as client:
        with patch("app.api.consumer.ConsumerAppService.run_consumer_interview") as interview:
            interview.side_effect = ValueError("live mode environment is not running")
            resp = client.post(
                "/api/consumer/simulations/sim-1/interviews",
                json={"topic": "proof", "mode": "live"},
            )

    assert resp.status_code == 409
    assert resp.get_json()["success"] is False


def test_interview_route_live_mode_without_running_simulation_returns_409_from_real_service():
    app = create_app()
    app.config["TESTING"] = True
    state = type(
        "State",
        (),
        {
            "status": "ready",
            "project_id": "project-1",
            "graph_id": "graph-1",
            "project_type": "consumer_test",
            "consumer_mode": True,
        },
    )()

    with app.test_client() as client:
        with patch("app.services.application.consumer_app_service.ConsumerAppService._simulation_repo") as repo:
            repo.get_simulation.return_value = state
            resp = client.post(
                "/api/consumer/simulations/sim-live/interviews",
                json={"topic": "proof", "mode": "live", "roles": ["skeptic"]},
            )

    assert resp.status_code == 409
    assert resp.get_json()["success"] is False
