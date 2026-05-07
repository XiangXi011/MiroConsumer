import json
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


def test_start_large_society_blocked_when_phase6j_artifact_blocks(monkeypatch, tmp_path):
    app = create_app()
    app.config["TESTING"] = True
    sim_dir = tmp_path / "simulations" / "sim-phase6j"
    sim_dir.mkdir(parents=True, exist_ok=True)
    artifact = {
        "phase7_entry_decision": "BLOCKED",
        "golden_flow_result": "BLOCKED",
        "evidence_gatekeeping_result": "PASS",
        "reasoning_backend_coverage": 0.6,
        "template_fallback_coverage": 0.2,
    }
    (sim_dir / "phase6j_calibration_artifact.json").write_text(
        json.dumps(artifact, indent=2), encoding="utf-8"
    )
    monkeypatch.setattr(
        "app.services.application.simulation_app_service.Config.OASIS_SIMULATION_DATA_DIR",
        str(tmp_path / "simulations"),
    )
    with app.test_client() as client:
        with patch("app.services.application.simulation_app_service.SimulationAppService._simulation_repo") as repo:
            state = type("State", (), {
                "status": SimulationStatus.READY,
                "project_id": "p1",
                "graph_id": "g1",
                "project_type": "consumer_test",
                "simulation_id": "sim-phase6j",
            })()
            repo.get_simulation.return_value = state
            resp = client.post(
                "/api/simulation/start",
                json={"simulation_id": "sim-phase6j", "society_mode": "large_society", "max_rounds": 1},
            )

    assert resp.status_code == 400
    data = resp.get_json()
    assert "Phase 6J calibration blocks entry" in data["error"]
    assert data["details"]["blocked_mode"] == "large_society"
    assert data["details"]["phase7_entry_decision"] == "BLOCKED"


def test_start_standard_plus_blocked_when_phase6j_artifact_blocks(monkeypatch, tmp_path):
    app = create_app()
    app.config["TESTING"] = True
    sim_dir = tmp_path / "simulations" / "sim-phase6j-sp"
    sim_dir.mkdir(parents=True, exist_ok=True)
    artifact = {
        "phase7_entry_decision": "BLOCKED",
        "golden_flow_result": "BLOCKED",
        "evidence_gatekeeping_result": "PASS",
        "reasoning_backend_coverage": 0.6,
        "template_fallback_coverage": 0.2,
    }
    (sim_dir / "phase6j_calibration_artifact.json").write_text(
        json.dumps(artifact, indent=2), encoding="utf-8"
    )
    monkeypatch.setattr(
        "app.services.application.simulation_app_service.Config.OASIS_SIMULATION_DATA_DIR",
        str(tmp_path / "simulations"),
    )
    with app.test_client() as client:
        with patch("app.services.application.simulation_app_service.SimulationAppService._simulation_repo") as repo:
            state = type("State", (), {
                "status": SimulationStatus.READY,
                "project_id": "p1",
                "graph_id": "g1",
                "project_type": "consumer_test",
                "simulation_id": "sim-phase6j-sp",
            })()
            repo.get_simulation.return_value = state
            resp = client.post(
                "/api/simulation/start",
                json={"simulation_id": "sim-phase6j-sp", "society_mode": "standard_plus", "max_rounds": 1},
            )

    assert resp.status_code == 400
    data = resp.get_json()
    assert "Phase 6J calibration blocks entry" in data["error"]
    assert data["details"]["blocked_mode"] == "standard_plus"
    assert data["details"]["phase7_entry_decision"] == "BLOCKED"


def test_start_quick_allowed_even_when_phase6j_artifact_blocks(monkeypatch, tmp_path):
    app = create_app()
    app.config["TESTING"] = True
    sim_dir = tmp_path / "simulations" / "sim-phase6j-quick"
    sim_dir.mkdir(parents=True, exist_ok=True)
    artifact = {
        "phase7_entry_decision": "BLOCKED",
        "golden_flow_result": "BLOCKED",
        "evidence_gatekeeping_result": "PASS",
        "reasoning_backend_coverage": 0.6,
        "template_fallback_coverage": 0.2,
    }
    (sim_dir / "phase6j_calibration_artifact.json").write_text(
        json.dumps(artifact, indent=2), encoding="utf-8"
    )
    monkeypatch.setattr(
        "app.services.application.simulation_app_service.Config.OASIS_SIMULATION_DATA_DIR",
        str(tmp_path / "simulations"),
    )
    with app.test_client() as client:
        with patch("app.services.application.simulation_app_service.SimulationAppService._simulation_repo") as repo, patch(
            "app.services.application.simulation_app_service.SimulationRunner.start_simulation"
        ) as start:
            state = type("State", (), {
                "status": SimulationStatus.READY,
                "project_id": "p1",
                "graph_id": "g1",
                "project_type": "consumer_test",
                "simulation_id": "sim-phase6j-quick",
            })()
            repo.get_simulation.return_value = state
            start.return_value.to_dict.return_value = {"simulation_id": "sim-phase6j-quick", "runner_status": "running"}
            resp = client.post(
                "/api/simulation/start",
                json={"simulation_id": "sim-phase6j-quick", "society_mode": "quick"},
            )

    assert resp.status_code == 200


def test_start_large_society_allowed_when_phase6j_artifact_passes(monkeypatch, tmp_path):
    app = create_app()
    app.config["TESTING"] = True
    sim_dir = tmp_path / "simulations" / "sim-phase6j-pass"
    sim_dir.mkdir(parents=True, exist_ok=True)
    artifact = {
        "phase7_entry_decision": "PASS",
        "golden_flow_result": "PASS",
        "evidence_gatekeeping_result": "PASS",
        "reasoning_backend_coverage": 0.8,
        "template_fallback_coverage": 0.1,
    }
    (sim_dir / "phase6j_calibration_artifact.json").write_text(
        json.dumps(artifact, indent=2), encoding="utf-8"
    )
    monkeypatch.setattr(
        "app.services.application.simulation_app_service.Config.OASIS_SIMULATION_DATA_DIR",
        str(tmp_path / "simulations"),
    )
    with app.test_client() as client:
        with patch("app.services.application.simulation_app_service.SimulationAppService._simulation_repo") as repo, patch(
            "app.services.application.simulation_app_service.SimulationRunner.start_simulation"
        ) as start:
            state = type("State", (), {
                "status": SimulationStatus.READY,
                "project_id": "p1",
                "graph_id": "g1",
                "project_type": "consumer_test",
                "simulation_id": "sim-phase6j-pass",
            })()
            repo.get_simulation.return_value = state
            start.return_value.to_dict.return_value = {"simulation_id": "sim-phase6j-pass", "runner_status": "running"}
            resp = client.post(
                "/api/simulation/start",
                json={"simulation_id": "sim-phase6j-pass", "society_mode": "large_society", "max_rounds": 1},
            )

    assert resp.status_code == 200


def test_start_standard_plus_allowed_when_no_phase6j_artifact(monkeypatch, tmp_path):
    app = create_app()
    app.config["TESTING"] = True
    sim_dir = tmp_path / "simulations" / "sim-no-artifact"
    sim_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(
        "app.services.application.simulation_app_service.Config.OASIS_SIMULATION_DATA_DIR",
        str(tmp_path / "simulations"),
    )
    with app.test_client() as client:
        with patch("app.services.application.simulation_app_service.SimulationAppService._simulation_repo") as repo, patch(
            "app.services.application.simulation_app_service.SimulationRunner.start_simulation"
        ) as start:
            state = type("State", (), {
                "status": SimulationStatus.READY,
                "project_id": "p1",
                "graph_id": "g1",
                "project_type": "consumer_test",
                "simulation_id": "sim-no-artifact",
            })()
            repo.get_simulation.return_value = state
            start.return_value.to_dict.return_value = {"simulation_id": "sim-no-artifact", "runner_status": "running"}
            resp = client.post(
                "/api/simulation/start",
                json={"simulation_id": "sim-no-artifact", "society_mode": "standard_plus"},
            )

    assert resp.status_code == 200
