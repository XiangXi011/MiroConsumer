"""Tests for canonical consumer routes under /api/consumer/.

These mirror the existing simulation/report compatibility shim tests but
assert that the new canonical URLs work and return the same shapes.
"""

import json
from pathlib import Path

from flask import Flask

from app.api import consumer_bp, graph_bp, report_bp, simulation_bp
from app.api import simulation as simulation_api
from app.models.project import ProjectManager
from app.services.simulation_runner import SimulationRunner


def _create_test_app():
    app = Flask(__name__)
    app.config["TESTING"] = True
    if hasattr(app, "json") and hasattr(app.json, "ensure_ascii"):
        app.json.ensure_ascii = False
    app.register_blueprint(graph_bp, url_prefix="/api/graph")
    app.register_blueprint(simulation_bp, url_prefix="/api/simulation")
    app.register_blueprint(report_bp, url_prefix="/api/report")
    app.register_blueprint(consumer_bp, url_prefix="/api/consumer")
    return app


def _configure_simulation_storage(tmp_path, monkeypatch):
    simulations_dir = tmp_path / "uploads" / "simulations"
    monkeypatch.setattr(simulation_api.Config, "OASIS_SIMULATION_DATA_DIR", str(simulations_dir))
    monkeypatch.setattr(simulation_api.Config, "UPLOAD_FOLDER", str(tmp_path / "uploads"))
    monkeypatch.setattr(simulation_api.SimulationManager, "SIMULATION_DATA_DIR", str(simulations_dir))
    from app.services.simulation_manager import SimulationManager
    monkeypatch.setattr(SimulationManager, "SIMULATION_DATA_DIR", str(simulations_dir))
    return simulations_dir


def _seed_simulation(tmp_path, monkeypatch, simulation_id, project_type="consumer_test"):
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


# ---- Branches ----

def test_canonical_create_branch_route(tmp_path, monkeypatch):
    _seed_simulation(tmp_path, monkeypatch, "sim_can_branch")

    app = _create_test_app()
    client = app.test_client()

    response = client.post(
        "/api/consumer/simulations/sim_can_branch/branches",
        json={"name": "Canonical branch", "fork_round": 2, "description": "Test"},
    )

    assert response.status_code == 201
    payload = response.get_json()
    assert payload["success"] is True
    assert "branch_id" in payload["data"]
    assert payload["data"]["name"] == "Canonical branch"


def test_canonical_list_branches_route(tmp_path, monkeypatch):
    _seed_simulation(tmp_path, monkeypatch, "sim_can_list")

    app = _create_test_app()
    client = app.test_client()

    client.post(
        "/api/consumer/simulations/sim_can_list/branches",
        json={"name": "B1", "fork_round": 1},
    )
    client.post(
        "/api/consumer/simulations/sim_can_list/branches",
        json={"name": "B2", "fork_round": 1},
    )

    response = client.get("/api/consumer/simulations/sim_can_list/branches")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert len(payload["data"]["branches"]) == 2


# ---- Interventions ----

def test_canonical_list_interventions_for_simulation_route(tmp_path, monkeypatch):
    _seed_simulation(tmp_path, monkeypatch, "sim_can_int")

    app = _create_test_app()
    client = app.test_client()

    branch_resp = client.post(
        "/api/consumer/simulations/sim_can_int/branches",
        json={"name": "Int branch", "fork_round": 1},
    )
    branch_id = branch_resp.get_json()["data"]["branch_id"]

    client.post(
        f"/api/consumer/simulations/sim_can_int/branches/{branch_id}/interventions",
        json={"intervention_type": "clarification_injection", "payload": {"message": "x"}},
    )

    response = client.get("/api/consumer/simulations/sim_can_int/interventions")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert len(payload["data"]["interventions"]) == 1


def test_canonical_list_interventions_for_branch_route(tmp_path, monkeypatch):
    _seed_simulation(tmp_path, monkeypatch, "sim_can_b")

    app = _create_test_app()
    client = app.test_client()

    branch_resp = client.post(
        "/api/consumer/simulations/sim_can_b/branches",
        json={"name": "Branch", "fork_round": 1},
    )
    branch_id = branch_resp.get_json()["data"]["branch_id"]

    client.post(
        f"/api/consumer/simulations/sim_can_b/branches/{branch_id}/interventions",
        json={"intervention_type": "evidence_reveal", "payload": {"evidence": "Study"}},
    )

    response = client.get(
        f"/api/consumer/simulations/sim_can_b/branches/{branch_id}/interventions"
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert len(payload["data"]["interventions"]) == 1


# ---- Comparison ----

def test_canonical_branch_comparison_route(tmp_path, monkeypatch):
    _seed_simulation(tmp_path, monkeypatch, "sim_can_cmp")

    app = _create_test_app()
    client = app.test_client()

    base_resp = client.post(
        "/api/consumer/simulations/sim_can_cmp/branches",
        json={"name": "Base", "fork_round": 0},
    )
    base_id = base_resp.get_json()["data"]["branch_id"]

    branch_resp = client.post(
        "/api/consumer/simulations/sim_can_cmp/branches",
        json={"name": "Variant", "fork_round": 1, "parent_branch_id": base_id},
    )
    branch_id = branch_resp.get_json()["data"]["branch_id"]

    # Seed rounds artifacts
    simulations_dir = tmp_path / "uploads" / "simulations"
    for bid in (base_id, branch_id):
        bdir = simulations_dir / "sim_can_cmp" / "branches" / bid
        bdir.mkdir(parents=True, exist_ok=True)
        (bdir / "rounds.jsonl").write_text(
            json.dumps(
                {"round_num": 0, "agent_id": "a1", "attitude_label": "neutral", "bucket": "question"}
            )
            + "\n",
            encoding="utf-8",
        )

    response = client.get(
        f"/api/consumer/simulations/sim_can_cmp/branches/{branch_id}/comparison"
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["data"]["branch_id"] == branch_id
    assert "base_summary" in payload["data"]
    assert "branch_summary" in payload["data"]


# ---- Resume / Status ----

def test_canonical_resume_branch_route(tmp_path, monkeypatch):
    _seed_simulation(tmp_path, monkeypatch, "sim_can_res")
    simulations_dir = tmp_path / "uploads" / "simulations"
    sim_dir = simulations_dir / "sim_can_res"
    sim_dir.mkdir(parents=True, exist_ok=True)
    (sim_dir / "simulation_config.json").write_text(
        json.dumps(
            {
                "project_id": "proj_test",
                "project_type": "consumer_test",
                "consumer_mode": True,
                "pinned_brief_summary": "Brief",
                "time_config": {"total_simulation_hours": 1, "minutes_per_round": 30},
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(SimulationRunner, "run_branch_simulation", lambda *a, **k: None)

    app = _create_test_app()
    client = app.test_client()

    branch_resp = client.post(
        "/api/consumer/simulations/sim_can_res/branches",
        json={"name": "Resume Branch", "fork_round": 0},
    )
    branch_id = branch_resp.get_json()["data"]["branch_id"]

    response = client.post(
        f"/api/consumer/simulations/sim_can_res/branches/{branch_id}/resume"
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["data"]["status"] == "running"


def test_canonical_get_branch_status_route(tmp_path, monkeypatch):
    _seed_simulation(tmp_path, monkeypatch, "sim_can_stat")

    app = _create_test_app()
    client = app.test_client()

    branch_resp = client.post(
        "/api/consumer/simulations/sim_can_stat/branches",
        json={"name": "Status Branch", "fork_round": 0},
    )
    branch_id = branch_resp.get_json()["data"]["branch_id"]

    response = client.get(
        f"/api/consumer/simulations/sim_can_stat/branches/{branch_id}/status"
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["data"]["status"] == "idle"
    assert payload["data"]["branch_status"] == "active"


# ---- Comparison Snapshots ----

def test_canonical_create_comparison_snapshot(tmp_path, monkeypatch):
    """Create comparison via canonical consumer route."""
    _seed_simulation(tmp_path, monkeypatch, "sim_cmp_left")
    _seed_simulation(tmp_path, monkeypatch, "sim_cmp_right")

    # Seed consumer rounds so sides have data
    for sim_id in ("sim_cmp_left", "sim_cmp_right"):
        sim_dir = tmp_path / "uploads" / "simulations" / sim_id
        (sim_dir / "consumer_rounds.jsonl").write_text(
            json.dumps(
                {"round_num": 0, "agent_id": "a1", "attitude_label": "positive", "bucket": "resonance"}
            )
            + "\n",
            encoding="utf-8",
        )

    app = _create_test_app()
    client = app.test_client()

    response = client.post(
        "/api/consumer/comparisons",
        json={
            "mode": "run_vs_run",
            "left_simulation_id": "sim_cmp_left",
            "right_simulation_id": "sim_cmp_right",
        },
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert "comparison_id" in payload["data"]
    assert payload["data"]["mode"] == "run_vs_run"


def test_canonical_list_and_get_comparison_snapshot(tmp_path, monkeypatch):
    _seed_simulation(tmp_path, monkeypatch, "sim_cmp_l2")
    _seed_simulation(tmp_path, monkeypatch, "sim_cmp_r2")

    for sim_id in ("sim_cmp_l2", "sim_cmp_r2"):
        sim_dir = tmp_path / "uploads" / "simulations" / sim_id
        (sim_dir / "consumer_rounds.jsonl").write_text(
            json.dumps(
                {"round_num": 0, "agent_id": "a1", "attitude_label": "positive", "bucket": "resonance"}
            )
            + "\n",
            encoding="utf-8",
        )

    app = _create_test_app()
    client = app.test_client()

    create_resp = client.post(
        "/api/consumer/comparisons",
        json={
            "mode": "run_vs_run",
            "left_simulation_id": "sim_cmp_l2",
            "right_simulation_id": "sim_cmp_r2",
        },
    )
    comparison_id = create_resp.get_json()["data"]["comparison_id"]
    project_id = create_resp.get_json()["data"]["project_ids"][0]

    list_resp = client.get(f"/api/consumer/comparisons?project_id={project_id}")
    assert list_resp.status_code == 200
    list_payload = list_resp.get_json()
    assert list_payload["success"] is True
    assert any(item["comparison_id"] == comparison_id for item in list_payload["data"]["items"])

    get_resp = client.get(f"/api/consumer/comparisons/{comparison_id}")
    assert get_resp.status_code == 200
    get_payload = get_resp.get_json()
    assert get_payload["success"] is True
    assert get_payload["data"]["comparison_id"] == comparison_id


# ---- Research Assets ----

def test_canonical_export_and_get_research_asset(tmp_path, monkeypatch):
    _seed_simulation(tmp_path, monkeypatch, "sim_asset")
    uploads_dir = tmp_path / "uploads"
    monkeypatch.setattr(simulation_api.Config, "UPLOAD_FOLDER", str(uploads_dir))

    # Seed a consumer project
    projects_dir = uploads_dir / "projects"
    projects_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(projects_dir))

    project = ProjectManager.create_project(name="Asset Project")
    project.project_type = "consumer_test"
    ProjectManager.save_project(project)

    # Update simulation state to belong to project
    sim_dir = uploads_dir / "simulations" / "sim_asset"
    state = json.loads((sim_dir / "state.json").read_text(encoding="utf-8"))
    state["project_id"] = project.project_id
    (sim_dir / "state.json").write_text(json.dumps(state), encoding="utf-8")

    # Seed config and rounds so export can read findings
    (sim_dir / "consumer_config.json").write_text(
        json.dumps({"research_findings": []}), encoding="utf-8"
    )
    (sim_dir / "consumer_rounds.jsonl").write_text(
        json.dumps(
            {"round_num": 0, "agent_id": "a1", "attitude_label": "positive", "bucket": "resonance"}
        )
        + "\n",
        encoding="utf-8",
    )

    app = _create_test_app()
    client = app.test_client()

    export_resp = client.post(
        "/api/consumer/research-assets/export",
        json={"project_id": project.project_id, "simulation_id": "sim_asset", "name": "Test Asset"},
    )
    assert export_resp.status_code == 200
    export_payload = export_resp.get_json()
    assert export_payload["success"] is True
    assert "asset_id" in export_payload["data"]
    asset_id = export_payload["data"]["asset_id"]

    get_resp = client.get(f"/api/consumer/research-assets/{asset_id}")
    assert get_resp.status_code == 200
    get_payload = get_resp.get_json()
    assert get_payload["success"] is True
    assert get_payload["data"]["asset_id"] == asset_id


def test_canonical_list_research_assets(tmp_path, monkeypatch):
    _seed_simulation(tmp_path, monkeypatch, "sim_asset_list")
    uploads_dir = tmp_path / "uploads"
    monkeypatch.setattr(simulation_api.Config, "UPLOAD_FOLDER", str(uploads_dir))

    projects_dir = uploads_dir / "projects"
    projects_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(projects_dir))

    project = ProjectManager.create_project(name="List Project")
    project.project_type = "consumer_test"
    ProjectManager.save_project(project)

    sim_dir = uploads_dir / "simulations" / "sim_asset_list"
    state = json.loads((sim_dir / "state.json").read_text(encoding="utf-8"))
    state["project_id"] = project.project_id
    (sim_dir / "state.json").write_text(json.dumps(state), encoding="utf-8")
    (sim_dir / "consumer_config.json").write_text(
        json.dumps({"research_findings": []}), encoding="utf-8"
    )
    (sim_dir / "consumer_rounds.jsonl").write_text(
        json.dumps(
            {"round_num": 0, "agent_id": "a1", "attitude_label": "positive", "bucket": "resonance"}
        )
        + "\n",
        encoding="utf-8",
    )

    app = _create_test_app()
    client = app.test_client()

    client.post(
        "/api/consumer/research-assets/export",
        json={"project_id": project.project_id, "simulation_id": "sim_asset_list"},
    )

    list_resp = client.get(f"/api/consumer/research-assets?project_id={project.project_id}")
    assert list_resp.status_code == 200
    list_payload = list_resp.get_json()
    assert list_payload["success"] is True
    assert len(list_payload["data"]["items"]) >= 1


# ---- Consumer Summary (smoke gate) ----

def test_canonical_consumer_summary_smoke_gate(tmp_path, monkeypatch):
    """End-to-end smoke test for consumer summary via canonical route."""
    _seed_simulation(tmp_path, monkeypatch, "sim_smoke")

    uploads_dir = tmp_path / "uploads"
    monkeypatch.setattr(simulation_api.Config, "UPLOAD_FOLDER", str(uploads_dir))

    # Seed consumer config with brief and findings
    sim_dir = uploads_dir / "simulations" / "sim_smoke"
    (sim_dir / "consumer_config.json").write_text(
        json.dumps(
            {
                "consumer_brief": {
                    "task_type": "concept_test",
                    "product_concept_assets": ["proto.png"],
                    "research_goal": "Test appeal",
                },
                "research_findings": [
                    {
                        "finding_id": "f1",
                        "finding_type": "category_context",
                        "summary": "Strong resonance",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    # Seed consumer rounds with propagation events
    (sim_dir / "consumer_rounds.jsonl").write_text(
        json.dumps(
            {
                "round_num": 0,
                "agent_id": "a1",
                "attitude_label": "positive",
                "bucket": "resonance",
                "propagation_events": [
                    {
                        "event_id": "e1",
                        "event_type": "positive_relay",
                        "actor_id": "a1",
                        "round_index": 0,
                    }
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    app = _create_test_app()
    client = app.test_client()

    response = client.get("/api/consumer/simulation/sim_smoke/consumer-summary")
    payload = response.get_json()
    assert response.status_code == 200, f"Unexpected status: {response.status_code}, payload: {payload}"
    assert payload["success"] is True
    assert "data" in payload
    data = payload["data"]
    # Phase 1 baseline fields
    assert "attitude_shift_rate" in data
    # Phase 2 enrichment fields
    assert "event_counts" in data
    assert "causal_chains" in data
    assert "task_type" in data


# ---- Error handling parity ----

def test_canonical_create_branch_404_on_missing_simulation(tmp_path, monkeypatch):
    _configure_simulation_storage(tmp_path, monkeypatch)

    app = _create_test_app()
    client = app.test_client()

    response = client.post(
        "/api/consumer/simulations/sim_missing/branches",
        json={"name": "Orphan", "fork_round": 1},
    )
    assert response.status_code == 404
    payload = response.get_json()
    assert payload["success"] is False
    assert "not found" in payload["error"].lower()


def test_canonical_resume_rejects_already_running(tmp_path, monkeypatch):
    from app.services.consumer.intervention_manager import ConsumerInterventionManager

    _seed_simulation(tmp_path, monkeypatch, "sim_can_busy")
    simulations_dir = tmp_path / "uploads" / "simulations"
    sim_dir = simulations_dir / "sim_can_busy"
    sim_dir.mkdir(parents=True, exist_ok=True)
    (sim_dir / "simulation_config.json").write_text(
        json.dumps(
            {
                "project_id": "proj_test",
                "project_type": "consumer_test",
                "consumer_mode": True,
                "pinned_brief_summary": "Brief",
                "time_config": {"total_simulation_hours": 1, "minutes_per_round": 30},
            }
        ),
        encoding="utf-8",
    )

    app = _create_test_app()
    client = app.test_client()

    branch_resp = client.post(
        "/api/consumer/simulations/sim_can_busy/branches",
        json={"name": "Busy Branch", "fork_round": 0},
    )
    branch_id = branch_resp.get_json()["data"]["branch_id"]

    mgr = ConsumerInterventionManager()
    mgr.update_branch_run_status("sim_can_busy", branch_id, {"status": "running"})

    response = client.post(
        f"/api/consumer/simulations/sim_can_busy/branches/{branch_id}/resume"
    )
    assert response.status_code == 409
    payload = response.get_json()
    assert payload["success"] is False
    assert "already running" in payload["error"].lower()
