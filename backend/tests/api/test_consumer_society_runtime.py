from unittest.mock import patch

from app import create_app
from app.services.simulation_manager import SimulationStatus


def test_start_simulation_rejects_society_mode_for_non_consumer_simulation():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        with patch("app.services.application.simulation_app_service.SimulationAppService._simulation_repo") as repo:
            state = type("State", (), {
                "status": SimulationStatus.READY,
                "project_id": "p1",
                "graph_id": "g1",
                "project_type": "default",
            })()
            repo.get_simulation.return_value = state
            resp = client.post(
                "/api/simulation/start",
                json={"simulation_id": "sim-x", "society_mode": "standard"},
            )

    assert resp.status_code == 400
    assert "society" in resp.get_json()["error"].lower()


def test_start_simulation_rejects_society_max_agents_over_limit(monkeypatch):
    monkeypatch.setenv("MAX_SOCIETY_AGENTS", "100")
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        with patch("app.services.application.simulation_app_service.SimulationAppService._simulation_repo") as repo:
            state = type("State", (), {
                "status": SimulationStatus.READY,
                "project_id": "p1",
                "graph_id": "g1",
                "project_type": "consumer_test",
            })()
            repo.get_simulation.return_value = state
            resp = client.post(
                "/api/simulation/start",
                json={
                    "simulation_id": "sim-y",
                    "society_mode": "standard",
                    "society_max_agents": 101,
                },
            )

    assert resp.status_code == 400
    assert "MAX_SOCIETY_AGENTS" in resp.get_json()["error"]


def test_start_simulation_passes_society_config_to_runner():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        with patch("app.services.application.simulation_app_service.SimulationAppService._simulation_repo") as repo, patch(
            "app.services.application.simulation_app_service.SimulationRunner.start_simulation"
        ) as start:
            state = type("State", (), {
                "status": SimulationStatus.READY,
                "project_id": "p1",
                "graph_id": "g1",
                "project_type": "consumer_test",
            })()
            repo.get_simulation.return_value = state
            start.return_value.to_dict.return_value = {"simulation_id": "sim-z", "runner_status": "running"}
            resp = client.post(
                "/api/simulation/start",
                json={
                    "simulation_id": "sim-z",
                    "society_mode": "standard",
                    "society_seed": 123,
                    "society_max_agents": 100,
                    "advanced_society_mode": True,
                    "society_audit_sample_size": 9,
                },
            )

    assert resp.status_code == 200
    kwargs = start.call_args.kwargs
    assert kwargs["society_config"]["mode"] == "standard"
    assert kwargs["society_config"]["random_seed"] == 123
    assert kwargs["society_config"]["max_agents"] == 100
    assert kwargs["society_config"]["core_persona_count"] == 8
    assert kwargs["society_config"]["expanded_persona_count"] == 72
    assert kwargs["society_config"]["shadow_agent_count"] == 20
    assert kwargs["society_config"]["audit_sample_size"] == 9


def test_start_simulation_standard_defaults_to_32_agents():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        with patch("app.services.application.simulation_app_service.SimulationAppService._simulation_repo") as repo, patch(
            "app.services.application.simulation_app_service.SimulationRunner.start_simulation"
        ) as start:
            state = type("State", (), {
                "status": SimulationStatus.READY,
                "project_id": "p1",
                "graph_id": "g1",
                "project_type": "consumer_test",
            })()
            repo.get_simulation.return_value = state
            start.return_value.to_dict.return_value = {"simulation_id": "sim-default", "runner_status": "running"}
            resp = client.post(
                "/api/simulation/start",
                json={"simulation_id": "sim-default", "society_mode": "standard"},
            )

    assert resp.status_code == 200
    config = start.call_args.kwargs["society_config"]
    assert config["max_agents"] == 32
    assert config["core_persona_count"] == 8
    assert config["expanded_persona_count"] == 16
    assert config["shadow_agent_count"] == 8
    assert config["audit_sample_size"] == 4
    assert config["llm_budget_limit"] == 12


def test_start_simulation_standard_plus_defaults_to_100_agents():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        with patch("app.services.application.simulation_app_service.SimulationAppService._simulation_repo") as repo, patch(
            "app.services.application.simulation_app_service.SimulationRunner.start_simulation"
        ) as start:
            state = type("State", (), {
                "status": SimulationStatus.READY,
                "project_id": "p1",
                "graph_id": "g1",
                "project_type": "consumer_test",
            })()
            repo.get_simulation.return_value = state
            start.return_value.to_dict.return_value = {"simulation_id": "sim-plus", "runner_status": "running"}
            resp = client.post(
                "/api/simulation/start",
                json={"simulation_id": "sim-plus", "society_mode": "standard_plus"},
            )

    assert resp.status_code == 200
    config = start.call_args.kwargs["society_config"]
    assert config["max_agents"] == 100
    assert config["core_persona_count"] == 8
    assert config["expanded_persona_count"] == 72
    assert config["shadow_agent_count"] == 20
    assert config["audit_sample_size"] == 8
    assert config["llm_budget_limit"] == 16


def test_start_simulation_rejects_standard_over_32_without_advanced_mode():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        with patch("app.services.application.simulation_app_service.SimulationAppService._simulation_repo") as repo:
            state = type("State", (), {
                "status": SimulationStatus.READY,
                "project_id": "p1",
                "graph_id": "g1",
                "project_type": "consumer_test",
            })()
            repo.get_simulation.return_value = state
            resp = client.post(
                "/api/simulation/start",
                json={
                    "simulation_id": "sim-guard",
                    "society_mode": "standard",
                    "society_max_agents": 100,
                },
            )

    assert resp.status_code == 400
    assert "advanced_society_mode" in resp.get_json()["error"]
