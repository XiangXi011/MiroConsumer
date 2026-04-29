from unittest.mock import patch

from app import create_app


def test_interview_and_focus_group_history_routes_return_fixed_payloads():
    app = create_app()
    app.config["TESTING"] = True

    with app.test_client() as client:
        with patch("app.api.consumer.ConsumerAppService.list_interview_history") as interviews, patch(
            "app.api.consumer.ConsumerAppService.list_focus_group_history"
        ) as focus_groups:
            interviews.return_value = {"items": [{"interview_id": "interview-1", "topic": "proof"}]}
            focus_groups.return_value = {"items": [{"focus_group_id": "focus-1", "topic": "proof"}]}

            interview_resp = client.get("/api/consumer/simulations/sim-1/interviews/history")
            focus_resp = client.get("/api/consumer/simulations/sim-1/focus-groups/history")

    assert interview_resp.status_code == 200
    assert interview_resp.get_json()["data"]["items"][0]["interview_id"] == "interview-1"
    assert focus_resp.status_code == 200
    assert focus_resp.get_json()["data"]["items"][0]["focus_group_id"] == "focus-1"


def test_history_route_maps_missing_history_to_404():
    app = create_app()
    app.config["TESTING"] = True

    with app.test_client() as client:
        with patch("app.api.consumer.ConsumerAppService.list_interview_history") as interviews:
            interviews.side_effect = ValueError("history not found")
            resp = client.get("/api/consumer/simulations/sim-missing/interviews/history")

    assert resp.status_code == 404
    assert resp.get_json()["success"] is False
