import json
from io import BytesIO
from pathlib import Path

from flask import Flask

from app.api import graph_bp, report_bp, simulation_bp
from app.api import graph as graph_api
from app.api import simulation as simulation_api
from app.models.project import ProjectManager, ProjectStatus
from app.models.task import TaskManager, TaskStatus
from app.services.consumer.graph_builder import ConsumerGraphBuilder
from app.services.consumer.models import ConsumerBusinessBrief
from app.services.simulation_runner import RunnerStatus, SimulationRunner


def _create_test_app():
    app = Flask(__name__)
    app.config["TESTING"] = True
    if hasattr(app, "json") and hasattr(app.json, "ensure_ascii"):
        app.json.ensure_ascii = False
    app.register_blueprint(graph_bp, url_prefix="/api/graph")
    app.register_blueprint(simulation_bp, url_prefix="/api/simulation")
    app.register_blueprint(report_bp, url_prefix="/api/report")
    return app


def _reset_task_manager():
    task_manager = TaskManager()
    task_manager._tasks.clear()


def _configure_simulation_storage(tmp_path, monkeypatch):
    simulations_dir = tmp_path / "uploads" / "simulations"
    monkeypatch.setattr(simulation_api.Config, "OASIS_SIMULATION_DATA_DIR", str(simulations_dir))
    monkeypatch.setattr(simulation_api.Config, "UPLOAD_FOLDER", str(tmp_path / "uploads"))
    monkeypatch.setattr(simulation_api.SimulationManager, "SIMULATION_DATA_DIR", str(simulations_dir))
    from app.services.simulation_manager import SimulationManager
    monkeypatch.setattr(SimulationManager, "SIMULATION_DATA_DIR", str(simulations_dir))
    return simulations_dir


def _seed_simulation(tmp_path, monkeypatch, simulation_id, project_type="consumer_test"):
    """Write a minimal simulation state.json so routes see a real simulation."""
    simulations_dir = _configure_simulation_storage(tmp_path, monkeypatch)
    sim_dir = simulations_dir / simulation_id
    sim_dir.mkdir(parents=True, exist_ok=True)
    state = {
        "simulation_id": simulation_id,
        "project_id": "proj_test",
        "graph_id": "graph_test",
        "project_type": project_type,
        "consumer_mode": project_type == "consumer_test",
        "status": "created",
        "created_at": "2024-01-01T00:00:00",
    }
    (sim_dir / "state.json").write_text(json.dumps(state), encoding="utf-8")
    return simulations_dir


def _consumer_brief_payload():
    return {
        "task_type": "concept_test",
        "product_concept_assets": ["Glow serum stick"],
        "copy_material": ["Brighter skin in one swipe"],
        "claims": ["Derm-tested glow boost"],
        "target_audience": ["busy commuters"],
        "usage_scene": ["morning commute"],
        "research_goal": "Understand first-impression appeal",
    }


def test_create_branch_route(tmp_path, monkeypatch):
    _seed_simulation(tmp_path, monkeypatch, "sim_test")

    app = _create_test_app()
    client = app.test_client()

    response = client.post(
        "/api/simulation/sim_test/branches",
        json={
            "name": "Clarification branch",
            "fork_round": 2,
            "description": "Inject clarification at round 2",
        },
    )

    assert response.status_code == 201
    payload = response.get_json()
    assert payload["success"] is True
    assert "branch_id" in payload["data"]
    assert payload["data"]["name"] == "Clarification branch"
    assert payload["data"]["fork_round"] == 2


def test_list_branches_route(tmp_path, monkeypatch):
    _seed_simulation(tmp_path, monkeypatch, "sim_list")

    app = _create_test_app()
    client = app.test_client()

    # Create two branches
    client.post(
        "/api/simulation/sim_list/branches",
        json={"name": "B1", "fork_round": 1},
    )
    client.post(
        "/api/simulation/sim_list/branches",
        json={"name": "B2", "fork_round": 1},
    )

    response = client.get("/api/simulation/sim_list/branches")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert len(payload["data"]["branches"]) == 2


def test_list_interventions_for_simulation_route(tmp_path, monkeypatch):
    _seed_simulation(tmp_path, monkeypatch, "sim_int")

    app = _create_test_app()
    client = app.test_client()

    branch_resp = client.post(
        "/api/simulation/sim_int/branches",
        json={"name": "Int branch", "fork_round": 1},
    )
    branch_id = branch_resp.get_json()["data"]["branch_id"]

    client.post(
        f"/api/simulation/sim_int/branches/{branch_id}/interventions",
        json={
            "intervention_type": "clarification_injection",
            "payload": {"message": "Clarify sugar"},
            "target_round": 2,
        },
    )

    response = client.get("/api/simulation/sim_int/interventions")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert len(payload["data"]["interventions"]) == 1
    assert payload["data"]["interventions"][0]["payload"]["message"] == "Clarify sugar"


def test_list_interventions_for_branch_route(tmp_path, monkeypatch):
    _seed_simulation(tmp_path, monkeypatch, "sim_b")

    app = _create_test_app()
    client = app.test_client()

    branch_resp = client.post(
        "/api/simulation/sim_b/branches",
        json={"name": "Branch", "fork_round": 1},
    )
    branch_id = branch_resp.get_json()["data"]["branch_id"]

    client.post(
        f"/api/simulation/sim_b/branches/{branch_id}/interventions",
        json={
            "intervention_type": "evidence_reveal",
            "payload": {"evidence": "Study X"},
        },
    )

    response = client.get(f"/api/simulation/sim_b/branches/{branch_id}/interventions")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert len(payload["data"]["interventions"]) == 1
    assert payload["data"]["interventions"][0]["intervention_type"] == "evidence_reveal"


def test_branch_comparison_context_route(tmp_path, monkeypatch):
    _seed_simulation(tmp_path, monkeypatch, "sim_cmp")

    app = _create_test_app()
    client = app.test_client()

    base_resp = client.post(
        "/api/simulation/sim_cmp/branches",
        json={"name": "Base", "fork_round": 0},
    )
    base_id = base_resp.get_json()["data"]["branch_id"]

    branch_resp = client.post(
        "/api/simulation/sim_cmp/branches",
        json={"name": "Variant", "fork_round": 1, "parent_branch_id": base_id},
    )
    branch_id = branch_resp.get_json()["data"]["branch_id"]

    # Seed base rounds artifact
    simulations_dir = tmp_path / "uploads" / "simulations"
    base_dir = simulations_dir / "sim_cmp" / "branches" / base_id
    base_dir.mkdir(parents=True, exist_ok=True)
    (base_dir / "rounds.jsonl").write_text(
        json.dumps(
            {"round_num": 0, "agent_id": "a1", "attitude_label": "neutral", "bucket": "question"}
        )
        + "\n",
        encoding="utf-8",
    )

    # Seed branch rounds artifact
    branch_dir = simulations_dir / "sim_cmp" / "branches" / branch_id
    branch_dir.mkdir(parents=True, exist_ok=True)
    (branch_dir / "rounds.jsonl").write_text(
        json.dumps(
            {"round_num": 0, "agent_id": "a1", "attitude_label": "positive", "bucket": "resonance"}
        )
        + "\n",
        encoding="utf-8",
    )

    client.post(
        f"/api/simulation/sim_cmp/branches/{branch_id}/interventions",
        json={
            "intervention_type": "revised_claim_injection",
            "payload": {"claim": "Updated claim"},
            "target_round": 1,
        },
    )

    response = client.get(f"/api/simulation/sim_cmp/branches/{branch_id}/comparison")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["data"]["branch_id"] == branch_id
    assert payload["data"]["base_branch_id"] == base_id
    assert payload["data"]["fork_round"] == 1
    assert len(payload["data"]["interventions"]) == 1
    assert "base_summary" in payload["data"]
    assert "branch_summary" in payload["data"]


def test_create_branch_invalid_fork_round(tmp_path, monkeypatch):
    _seed_simulation(tmp_path, monkeypatch, "sim_inv")

    app = _create_test_app()
    client = app.test_client()

    response = client.post(
        "/api/simulation/sim_inv/branches",
        json={"name": "Bad", "fork_round": -1},
    )
    assert response.status_code == 400


def test_intervention_route_rejects_invalid_type(tmp_path, monkeypatch):
    _seed_simulation(tmp_path, monkeypatch, "sim_rej")

    app = _create_test_app()
    client = app.test_client()

    branch_resp = client.post(
        "/api/simulation/sim_rej/branches",
        json={"name": "Branch", "fork_round": 1},
    )
    branch_id = branch_resp.get_json()["data"]["branch_id"]

    response = client.post(
        f"/api/simulation/sim_rej/branches/{branch_id}/interventions",
        json={"intervention_type": "bad_type", "payload": {}},
    )
    assert response.status_code == 400


def test_comparison_context_404_for_missing_branch(tmp_path, monkeypatch):
    _seed_simulation(tmp_path, monkeypatch, "sim_404")

    app = _create_test_app()
    client = app.test_client()

    response = client.get("/api/simulation/sim_404/branches/no-such-branch/comparison")
    assert response.status_code == 404


# ---- Regression tests for contract gaps ----

def test_create_branch_on_missing_simulation_returns_404(tmp_path, monkeypatch):
    _configure_simulation_storage(tmp_path, monkeypatch)

    app = _create_test_app()
    client = app.test_client()

    response = client.post(
        "/api/simulation/sim_missing/branches",
        json={"name": "Orphan", "fork_round": 1},
    )
    assert response.status_code == 404
    payload = response.get_json()
    assert payload["success"] is False
    assert "not found" in payload["error"].lower()


def test_create_branch_on_non_consumer_simulation_returns_400(tmp_path, monkeypatch):
    _seed_simulation(tmp_path, monkeypatch, "sim_default", project_type="default")

    app = _create_test_app()
    client = app.test_client()

    response = client.post(
        "/api/simulation/sim_default/branches",
        json={"name": "Should fail", "fork_round": 1},
    )
    assert response.status_code == 400
    payload = response.get_json()
    assert payload["success"] is False
    assert "not a consumer_test" in payload["error"].lower()


def test_add_intervention_to_missing_branch_returns_404(tmp_path, monkeypatch):
    _seed_simulation(tmp_path, monkeypatch, "sim_nobranch")

    app = _create_test_app()
    client = app.test_client()

    response = client.post(
        "/api/simulation/sim_nobranch/branches/no_branch/interventions",
        json={"intervention_type": "clarification_injection", "payload": {"message": "x"}},
    )
    assert response.status_code == 404
    payload = response.get_json()
    assert payload["success"] is False
    assert "not found" in payload["error"].lower()


def test_list_interventions_for_missing_branch_returns_404(tmp_path, monkeypatch):
    _seed_simulation(tmp_path, monkeypatch, "sim_nobranch2")

    app = _create_test_app()
    client = app.test_client()

    response = client.get("/api/simulation/sim_nobranch2/branches/no_branch/interventions")
    assert response.status_code == 404
    payload = response.get_json()
    assert payload["success"] is False
    assert "not found" in payload["error"].lower()


def test_create_branch_with_missing_parent_branch_returns_400(tmp_path, monkeypatch):
    _seed_simulation(tmp_path, monkeypatch, "sim_parent")

    app = _create_test_app()
    client = app.test_client()

    response = client.post(
        "/api/simulation/sim_parent/branches",
        json={"name": "Child", "fork_round": 1, "parent_branch_id": "does_not_exist"},
    )
    assert response.status_code == 400
    payload = response.get_json()
    assert payload["success"] is False
    assert "parent branch not found" in payload["error"].lower()


def test_list_branches_rejects_non_consumer_simulation(tmp_path, monkeypatch):
    _seed_simulation(tmp_path, monkeypatch, "sim_lc", project_type="default")

    app = _create_test_app()
    client = app.test_client()

    response = client.get("/api/simulation/sim_lc/branches")
    assert response.status_code == 400


def test_list_interventions_for_simulation_rejects_non_consumer(tmp_path, monkeypatch):
    _seed_simulation(tmp_path, monkeypatch, "sim_li", project_type="default")

    app = _create_test_app()
    client = app.test_client()

    response = client.get("/api/simulation/sim_li/interventions")
    assert response.status_code == 400
