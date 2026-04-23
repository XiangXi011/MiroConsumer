"""Phase 6A Task 4: project_type persistence contract regression tests.

Rules under test:
  1. Legacy callers that omit project_type on create-time graph intake
     still persist default compatibility behaviour.
  2. Callers that explicitly send project_type=consumer_test persist
     consumer_test through project creation and simulation creation.
  3. Persisted legacy artifacts with project_type=default round-trip
     through repositories and shared engine loading without requiring
     a legacy route shim.
  4. Canonical /api/consumer/* routes and legacy compatibility shim
     routes remain green after the new assertions.
"""

import json
from io import BytesIO
from pathlib import Path

import sys

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from flask import Flask

from app.api import consumer_bp, graph_bp, report_bp, simulation_bp
from app.api import graph as graph_api
from app.api import simulation as simulation_api
from app.models.project import ProjectManager, ProjectStatus
from app.models.task import TaskManager
from app.repositories.filesystem import FilesystemSimulationRepository
from app.services.simulation_manager import SimulationManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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


def _configure_storage(tmp_path, monkeypatch):
    uploads_dir = tmp_path / "uploads"
    projects_dir = uploads_dir / "projects"
    simulations_dir = uploads_dir / "simulations"
    monkeypatch.setattr(graph_api.Config, "UPLOAD_FOLDER", str(uploads_dir))
    monkeypatch.setattr(graph_api.Config, "ZEP_API_KEY", None)
    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(projects_dir))
    monkeypatch.setattr(simulation_api.Config, "OASIS_SIMULATION_DATA_DIR", str(simulations_dir))
    monkeypatch.setattr(simulation_api.Config, "UPLOAD_FOLDER", str(uploads_dir))
    monkeypatch.setattr(simulation_api.SimulationManager, "SIMULATION_DATA_DIR", str(simulations_dir))
    monkeypatch.setattr(SimulationManager, "SIMULATION_DATA_DIR", str(simulations_dir))
    return uploads_dir, simulations_dir


def _fake_ontology(monkeypatch):
    class FakeOntologyGenerator:
        def generate(self, document_texts, simulation_requirement, additional_context=None):
            return {
                "entity_types": [{"name": "ProductConcept", "attributes": []}],
                "edge_types": [{"name": "MENTIONS", "attributes": [], "source_targets": []}],
                "analysis_summary": "summary",
            }

    monkeypatch.setattr(graph_api, "OntologyGenerator", FakeOntologyGenerator)


def _reset_task_manager():
    task_manager = TaskManager()
    task_manager._tasks.clear()


# ---------------------------------------------------------------------------
# Rule 1 – legacy callers that omit project_type persist "default"
# ---------------------------------------------------------------------------

def test_legacy_omitted_project_type_defaults_to_default(tmp_path, monkeypatch):
    """When project_type is not sent in the form, the project persists
    project_type='default' and simulation creation carries that through."""
    _configure_storage(tmp_path, monkeypatch)
    _fake_ontology(monkeypatch)
    _reset_task_manager()

    app = _create_test_app()
    client = app.test_client()

    # Call generate_ontology WITHOUT project_type in the form data
    response = client.post(
        "/api/graph/ontology/generate",
        data={
            "simulation_requirement": "Legacy default project",
            "project_name": "Legacy Default",
            "files": (BytesIO(b"sample text"), "doc.txt"),
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    project_id = response.get_json()["data"]["project_id"]

    project = ProjectManager.get_project(project_id)
    assert project is not None
    assert project.project_type == "default"

    # Build graph for the default project — simulation route needs a graph_id.
    # Simulate a completed graph by setting graph_id and status directly.
    project.graph_id = "graph_legacy_default"
    project.status = ProjectStatus.GRAPH_COMPLETED
    ProjectManager.save_project(project)

    # Create simulation via API
    sim_response = client.post(
        "/api/simulation/create",
        json={"project_id": project_id},
    )
    assert sim_response.status_code == 200
    sim_data = sim_response.get_json()["data"]
    assert sim_data["project_type"] == "default"
    assert sim_data["consumer_mode"] is False


# ---------------------------------------------------------------------------
# Rule 2 – explicit project_type=consumer_test persists through
#           project creation and simulation creation
# ---------------------------------------------------------------------------

def test_explicit_consumer_test_persists_through_project_and_simulation(tmp_path, monkeypatch):
    """Sending project_type=consumer_test must be carried from project
    creation all the way into the simulation state."""
    _configure_storage(tmp_path, monkeypatch)
    _fake_ontology(monkeypatch)
    _reset_task_manager()

    app = _create_test_app()
    client = app.test_client()

    response = client.post(
        "/api/graph/ontology/generate",
        data={
            "simulation_requirement": "Consumer test project",
            "project_name": "Consumer Persist",
            "project_type": "consumer_test",
            "files": (BytesIO(b"consumer text"), "doc.txt"),
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    project_id = response.get_json()["data"]["project_id"]

    project = ProjectManager.get_project(project_id)
    assert project is not None
    assert project.project_type == "consumer_test"

    # Set graph_id so simulation creation can proceed
    project.graph_id = "graph_consumer_persist"
    project.status = ProjectStatus.GRAPH_COMPLETED
    ProjectManager.save_project(project)

    sim_response = client.post(
        "/api/simulation/create",
        json={"project_id": project_id},
    )
    assert sim_response.status_code == 200
    sim_data = sim_response.get_json()["data"]
    assert sim_data["project_type"] == "consumer_test"
    assert sim_data["consumer_mode"] is True


# ---------------------------------------------------------------------------
# Rule 3 – persisted legacy artifacts with project_type=default round-trip
#           through repositories without a legacy route shim
# ---------------------------------------------------------------------------

def test_default_project_type_round_trips_through_filesystem_repo(tmp_path, monkeypatch):
    """A SimulationState with project_type='default' must survive a
    create -> save -> load cycle via FilesystemSimulationRepository."""
    _, simulations_dir = _configure_storage(tmp_path, monkeypatch)

    repo = FilesystemSimulationRepository()

    # Create via repository (project_type defaults to "default")
    state = repo.create_simulation(
        project_id="proj_roundtrip",
        graph_id="graph_roundtrip",
        project_type="default",
    )
    assert state.project_type == "default"
    assert state.consumer_mode is False

    # Load back from disk
    loaded = repo.get_simulation(state.simulation_id)
    assert loaded is not None
    assert loaded.project_type == "default"
    assert loaded.consumer_mode is False
    assert loaded.simulation_id == state.simulation_id

    # Verify the raw JSON on disk also carries the fields
    import os
    state_file = os.path.join(
        str(simulations_dir), state.simulation_id, "state.json"
    )
    with open(state_file, "r", encoding="utf-8") as fh:
        raw = json.load(fh)
    assert raw["project_type"] == "default"
    assert raw["consumer_mode"] is False


def test_consumer_test_round_trips_through_filesystem_repo(tmp_path, monkeypatch):
    """Same round-trip test but for project_type='consumer_test'."""
    _, simulations_dir = _configure_storage(tmp_path, monkeypatch)

    repo = FilesystemSimulationRepository()

    state = repo.create_simulation(
        project_id="proj_consumer_rt",
        graph_id="graph_consumer_rt",
        project_type="consumer_test",
    )
    assert state.project_type == "consumer_test"
    assert state.consumer_mode is True

    loaded = repo.get_simulation(state.simulation_id)
    assert loaded is not None
    assert loaded.project_type == "consumer_test"
    assert loaded.consumer_mode is True


def test_none_project_type_normalises_to_default(tmp_path, monkeypatch):
    """Passing project_type=None must normalise to 'default', not None."""
    _, _ = _configure_storage(tmp_path, monkeypatch)

    repo = FilesystemSimulationRepository()
    state = repo.create_simulation(
        project_id="proj_none",
        graph_id="graph_none",
        project_type=None,
    )
    assert state.project_type == "default"
    assert state.consumer_mode is False

    loaded = repo.get_simulation(state.simulation_id)
    assert loaded.project_type == "default"


def test_legacy_state_json_without_project_type_loads_as_default(tmp_path, monkeypatch):
    """A pre-existing state.json that has no project_type key must load
    with project_type='default' (backward compatibility)."""
    _, simulations_dir = _configure_storage(tmp_path, monkeypatch)

    sim_id = "sim_no_pt_key"
    sim_dir = simulations_dir / sim_id
    sim_dir.mkdir(parents=True, exist_ok=True)

    # Write a minimal state.json WITHOUT project_type / consumer_mode keys
    legacy_state = {
        "simulation_id": sim_id,
        "project_id": "proj_legacy",
        "graph_id": "graph_legacy",
        "status": "created",
        "created_at": "2024-01-01T00:00:00",
    }
    (sim_dir / "state.json").write_text(
        json.dumps(legacy_state), encoding="utf-8"
    )

    repo = FilesystemSimulationRepository()
    loaded = repo.get_simulation(sim_id)
    assert loaded is not None
    assert loaded.project_type == "default"
    assert loaded.consumer_mode is False


# ---------------------------------------------------------------------------
# Rule 4 – canonical /api/consumer/* and legacy shim routes stay green
# ---------------------------------------------------------------------------

def test_canonical_consumer_routes_green_after_contract_assertions(tmp_path, monkeypatch):
    """After the above contract assertions, canonical consumer routes
    (branches CRUD) must still return 200/201 for a consumer_test sim."""
    _, simulations_dir = _configure_storage(tmp_path, monkeypatch)

    sim_id = "sim_canon_green"
    sim_dir = simulations_dir / sim_id
    sim_dir.mkdir(parents=True, exist_ok=True)
    state = {
        "simulation_id": sim_id,
        "project_id": "proj_canon",
        "graph_id": "graph_canon",
        "project_type": "consumer_test",
        "consumer_mode": True,
        "status": "created",
        "created_at": "2024-01-01T00:00:00",
    }
    (sim_dir / "state.json").write_text(json.dumps(state), encoding="utf-8")

    app = _create_test_app()
    client = app.test_client()

    # Create branch via canonical route
    resp = client.post(
        f"/api/consumer/simulations/{sim_id}/branches",
        json={"name": "Contract branch", "fork_round": 0},
    )
    assert resp.status_code == 201
    assert resp.get_json()["success"] is True

    # List branches via canonical route
    resp = client.get(f"/api/consumer/simulations/{sim_id}/branches")
    assert resp.status_code == 200
    assert resp.get_json()["success"] is True


def test_legacy_shim_routes_green_after_contract_assertions(tmp_path, monkeypatch):
    """Legacy compatibility shim routes (e.g. /api/simulation/branches)
    must still work for a consumer_test sim."""
    _, simulations_dir = _configure_storage(tmp_path, monkeypatch)

    sim_id = "sim_legacy_green"
    sim_dir = simulations_dir / sim_id
    sim_dir.mkdir(parents=True, exist_ok=True)
    state = {
        "simulation_id": sim_id,
        "project_id": "proj_legacy_shim",
        "graph_id": "graph_legacy_shim",
        "project_type": "consumer_test",
        "consumer_mode": True,
        "status": "created",
        "created_at": "2024-01-01T00:00:00",
    }
    (sim_dir / "state.json").write_text(json.dumps(state), encoding="utf-8")

    app = _create_test_app()
    client = app.test_client()

    # Legacy shim: create branch via /api/simulation/{sim_id}/branches
    resp = client.post(
        f"/api/simulation/{sim_id}/branches",
        json={"name": "Legacy shim branch", "fork_round": 1},
    )
    assert resp.status_code in (200, 201)
    body = resp.get_json()
    assert body["success"] is True


def test_canonical_routes_green_for_default_project_type(tmp_path, monkeypatch):
    """Canonical consumer routes should degrade gracefully (not 500) for
    a default project_type simulation."""
    _, simulations_dir = _configure_storage(tmp_path, monkeypatch)

    sim_id = "sim_canon_default"
    sim_dir = simulations_dir / sim_id
    sim_dir.mkdir(parents=True, exist_ok=True)
    state = {
        "simulation_id": sim_id,
        "project_id": "proj_canon_default",
        "graph_id": "graph_canon_default",
        "project_type": "default",
        "consumer_mode": False,
        "status": "created",
        "created_at": "2024-01-01T00:00:00",
    }
    (sim_dir / "state.json").write_text(json.dumps(state), encoding="utf-8")

    app = _create_test_app()
    client = app.test_client()

    # Listing branches should not 500 even for default project_type
    resp = client.get(f"/api/consumer/simulations/{sim_id}/branches")
    assert resp.status_code != 500
