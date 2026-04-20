from io import BytesIO
import json
from pathlib import Path
import sys
import threading


BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from flask import Flask

from app.api import graph_bp, report_bp, simulation_bp
from app.api import graph as graph_api
from app.api import report as report_api
from app.api import simulation as simulation_api
from app.models.project import ProjectManager, ProjectStatus
from app.models.task import TaskManager, TaskStatus
from app.services.report_agent import ReportManager
from app.services.simulation_manager import SimulationManager


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
    monkeypatch.setattr(simulation_api.SimulationManager, "SIMULATION_DATA_DIR", str(simulations_dir))
    monkeypatch.setattr(SimulationManager, "SIMULATION_DATA_DIR", str(simulations_dir))
    return simulations_dir


def _configure_report_storage(tmp_path, monkeypatch):
    reports_dir = tmp_path / "uploads" / "reports"
    monkeypatch.setattr(report_api.ReportManager, "REPORTS_DIR", str(reports_dir))
    monkeypatch.setattr(ReportManager, "REPORTS_DIR", str(reports_dir))
    return reports_dir


def _consumer_brief_payload():
    return {
        "task_type": "concept_test",
        "product_concept_assets": ["Glow serum stick"],
        "copy_material": ["Brighter skin in one swipe"],
        "claims": ["Derm-tested glow boost"],
        "target_audience": ["busy commuters"],
        "usage_scene": ["morning commute"],
        "research_goal": "Understand first-impression appeal",
        "optional_background_materials": [
            "Some shoppers may repeat that the finish spreads quickly through group chats."
        ],
    }


def _write_consumer_rounds(simulations_dir, simulation_id):
    simulation_dir = simulations_dir / simulation_id
    simulation_dir.mkdir(parents=True, exist_ok=True)
    events = [
        {
            "round_num": 0,
            "agent_id": "persona_a",
            "agent_name": "Value Seeker",
            "attitude_label": "positive",
            "bucket": "resonance",
            "engagement": 9,
            "quote": "This actually sounds like a real breakfast fix.",
            "prompt": "Pinned BusinessBrief Summary: breakfast yogurt pouch",
            "visible_nodes": [{"type": "ProductConcept", "text": "breakfast yogurt pouch"}],
        },
        {
            "round_num": 0,
            "agent_id": "persona_b",
            "agent_name": "Proof First",
            "attitude_label": "neutral",
            "bucket": "question",
            "engagement": 5,
            "quote": "I get the idea, but I still want more proof.",
            "prompt": "Pinned BusinessBrief Summary: breakfast yogurt pouch",
            "visible_nodes": [{"type": "CopyPoint", "text": "low sugar"}],
        },
        {
            "round_num": 1,
            "agent_id": "persona_a",
            "agent_name": "Value Seeker",
            "attitude_label": "negative",
            "bucket": "risk",
            "engagement": 8,
            "quote": "Low sugar? I don't trust that claim after the debate.",
            "prompt": "Pinned BusinessBrief Summary: breakfast yogurt pouch",
            "visible_nodes": [{"type": "RiskPoint", "text": "sweetener debate"}],
        },
        {
            "round_num": 1,
            "agent_id": "persona_b",
            "agent_name": "Proof First",
            "attitude_label": "positive",
            "bucket": "resonance",
            "engagement": 7,
            "quote": "People would probably keep sharing the breakfast angle.",
            "prompt": "Pinned BusinessBrief Summary: breakfast yogurt pouch",
            "visible_nodes": [{"type": "TalkingPoint", "text": "breakfast angle"}],
        },
    ]
    (simulation_dir / "consumer_rounds.jsonl").write_text(
        "\n".join(json.dumps(event, ensure_ascii=False) for event in events) + "\n",
        encoding="utf-8",
    )


def test_generate_ontology_persists_consumer_project_metadata(tmp_path, monkeypatch):
    uploads_dir = tmp_path / "uploads"
    projects_dir = uploads_dir / "projects"
    monkeypatch.setattr(graph_api.Config, "UPLOAD_FOLDER", str(uploads_dir))
    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(projects_dir))
    monkeypatch.setattr(graph_api.FileParser, "extract_text", staticmethod(lambda _: "consumer research text"))
    monkeypatch.setattr(graph_api.TextProcessor, "preprocess_text", staticmethod(lambda text: text))

    class FakeOntologyGenerator:
        def generate(self, document_texts, simulation_requirement, additional_context=None):
            return {
                "entity_types": [{"name": "ProductConcept", "attributes": []}],
                "edge_types": [{"name": "MENTIONS", "attributes": [], "source_targets": []}],
                "analysis_summary": "summary",
            }

    monkeypatch.setattr(graph_api, "OntologyGenerator", FakeOntologyGenerator)

    app = _create_test_app()
    client = app.test_client()

    response = client.post(
        "/api/graph/ontology/generate",
        data={
            "simulation_requirement": "Simulate consumer reactions",
            "project_name": "Consumer Test Project",
            "project_type": "consumer_test",
            "consumer_brief": json.dumps(_consumer_brief_payload()),
            "files": (BytesIO(b"consumer brief"), "brief.txt"),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    payload = response.get_json()
    project = ProjectManager.get_project(payload["data"]["project_id"])

    assert project is not None
    assert project.project_type == "consumer_test"
    assert project.consumer_brief["task_type"] == "concept_test"
    assert project.consumer_brief["product_concept_assets"] == ["Glow serum stick"]


def test_consumer_build_route_stores_graph_and_graph_data_is_retrievable(tmp_path, monkeypatch):
    uploads_dir = tmp_path / "uploads"
    projects_dir = uploads_dir / "projects"
    monkeypatch.setattr(graph_api.Config, "UPLOAD_FOLDER", str(uploads_dir))
    monkeypatch.setattr(graph_api.Config, "ZEP_API_KEY", None)
    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(projects_dir))
    _reset_task_manager()

    class ExplodingGraphBuilderService:
        def __init__(self, *args, **kwargs):
            raise AssertionError("Zep GraphBuilderService should not be used for consumer_test projects")

    monkeypatch.setattr(graph_api, "GraphBuilderService", ExplodingGraphBuilderService)

    project = ProjectManager.create_project(name="Consumer Build")
    project.project_type = "consumer_test"
    project.status = ProjectStatus.ONTOLOGY_GENERATED
    project.ontology = {"entity_types": [{"name": "ProductConcept", "attributes": []}], "edge_types": []}
    project.consumer_brief = _consumer_brief_payload()
    ProjectManager.save_project(project)
    ProjectManager.save_extracted_text(
        project.project_id,
        "This may spread quickly through creators. There is also a deeper technical contamination risk.",
    )

    app = _create_test_app()
    client = app.test_client()

    build_response = client.post("/api/graph/build", json={"project_id": project.project_id})

    assert build_response.status_code == 200
    build_payload = build_response.get_json()["data"]

    task = TaskManager().get_task(build_payload["task_id"])
    saved_project = ProjectManager.get_project(project.project_id)
    graph_response = client.get(f"/api/graph/data/{saved_project.graph_id}")

    assert task is not None
    assert task.status == TaskStatus.COMPLETED
    assert saved_project is not None
    assert saved_project.graph_id == f"consumer_{project.project_id}"
    assert saved_project.status == ProjectStatus.GRAPH_COMPLETED
    project_meta_path = projects_dir / project.project_id / "project.json"
    project_meta = json.loads(project_meta_path.read_text(encoding="utf-8"))
    graph_payload_path = projects_dir / project.project_id / "consumer_graph.json"

    assert saved_project.consumer_context in (None, {})
    assert "graph_payload" not in json.dumps(project_meta, ensure_ascii=False)
    assert graph_payload_path.exists()
    assert json.loads(graph_payload_path.read_text(encoding="utf-8"))["graph_id"] == saved_project.graph_id
    assert graph_response.status_code == 200
    assert graph_response.get_json()["data"]["graph_id"] == saved_project.graph_id
    assert any(
        node["visibility"] != "Initial"
        for node in graph_response.get_json()["data"]["nodes"]
        if "RiskPoint" in node["labels"]
    )


def test_reset_project_clears_local_consumer_graph_payload(tmp_path, monkeypatch):
    uploads_dir = tmp_path / "uploads"
    projects_dir = uploads_dir / "projects"
    monkeypatch.setattr(graph_api.Config, "UPLOAD_FOLDER", str(uploads_dir))
    monkeypatch.setattr(graph_api.Config, "ZEP_API_KEY", None)
    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(projects_dir))
    _reset_task_manager()

    project = ProjectManager.create_project(name="Consumer Reset")
    project.project_type = "consumer_test"
    project.status = ProjectStatus.ONTOLOGY_GENERATED
    project.ontology = {"entity_types": [{"name": "ProductConcept", "attributes": []}], "edge_types": []}
    project.consumer_brief = _consumer_brief_payload()
    ProjectManager.save_project(project)
    ProjectManager.save_extracted_text(project.project_id, "Contamination risk may spread in creator circles.")

    app = _create_test_app()
    client = app.test_client()

    build_response = client.post("/api/graph/build", json={"project_id": project.project_id})
    graph_id = ProjectManager.get_project(project.project_id).graph_id
    assert build_response.status_code == 200
    assert client.get(f"/api/graph/data/{graph_id}").status_code == 200

    reset_response = client.post(f"/api/graph/project/{project.project_id}/reset")

    assert reset_response.status_code == 200
    assert client.get(f"/api/graph/data/{graph_id}").status_code == 404
    assert not (projects_dir / project.project_id / "consumer_graph.json").exists()


def test_delete_project_removes_local_consumer_graph_payload(tmp_path, monkeypatch):
    uploads_dir = tmp_path / "uploads"
    projects_dir = uploads_dir / "projects"
    monkeypatch.setattr(graph_api.Config, "UPLOAD_FOLDER", str(uploads_dir))
    monkeypatch.setattr(graph_api.Config, "ZEP_API_KEY", None)
    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(projects_dir))
    _reset_task_manager()

    project = ProjectManager.create_project(name="Consumer Delete")
    project.project_type = "consumer_test"
    project.status = ProjectStatus.ONTOLOGY_GENERATED
    project.ontology = {"entity_types": [{"name": "ProductConcept", "attributes": []}], "edge_types": []}
    project.consumer_brief = _consumer_brief_payload()
    ProjectManager.save_project(project)
    ProjectManager.save_extracted_text(project.project_id, "Technical contamination risk appears in the background.")

    app = _create_test_app()
    client = app.test_client()

    build_response = client.post("/api/graph/build", json={"project_id": project.project_id})
    graph_id = ProjectManager.get_project(project.project_id).graph_id
    graph_file = projects_dir / project.project_id / "consumer_graph.json"

    assert build_response.status_code == 200
    assert graph_file.exists()

    delete_response = client.delete(f"/api/graph/project/{project.project_id}")

    assert delete_response.status_code == 200
    assert not (projects_dir / project.project_id).exists()
    assert client.get(f"/api/graph/data/{graph_id}").status_code == 404


def test_delete_graph_route_handles_consumer_local_graphs(tmp_path, monkeypatch):
    uploads_dir = tmp_path / "uploads"
    projects_dir = uploads_dir / "projects"
    monkeypatch.setattr(graph_api.Config, "UPLOAD_FOLDER", str(uploads_dir))
    monkeypatch.setattr(graph_api.Config, "ZEP_API_KEY", None)
    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(projects_dir))
    _reset_task_manager()

    project = ProjectManager.create_project(name="Consumer Graph Delete")
    project.project_type = "consumer_test"
    project.status = ProjectStatus.ONTOLOGY_GENERATED
    project.ontology = {"entity_types": [{"name": "ProductConcept", "attributes": []}], "edge_types": []}
    project.consumer_brief = _consumer_brief_payload()
    ProjectManager.save_project(project)
    ProjectManager.save_extracted_text(project.project_id, "Technical contamination risk appears in the background.")

    app = _create_test_app()
    client = app.test_client()

    build_response = client.post("/api/graph/build", json={"project_id": project.project_id})
    saved_project = ProjectManager.get_project(project.project_id)
    graph_id = saved_project.graph_id
    graph_file = projects_dir / project.project_id / "consumer_graph.json"

    assert build_response.status_code == 200
    assert graph_file.exists()
    assert client.get(f"/api/graph/data/{graph_id}").status_code == 200

    delete_response = client.delete(f"/api/graph/delete/{graph_id}")

    assert delete_response.status_code == 200
    refreshed_project = ProjectManager.get_project(project.project_id)
    assert refreshed_project is not None
    assert refreshed_project.graph_id is None
    assert refreshed_project.graph_build_task_id is None
    assert refreshed_project.status == ProjectStatus.ONTOLOGY_GENERATED
    assert not graph_file.exists()
    assert client.get(f"/api/graph/data/{graph_id}").status_code == 404


def test_default_build_route_keeps_legacy_graph_builder_path(tmp_path, monkeypatch):
    uploads_dir = tmp_path / "uploads"
    projects_dir = uploads_dir / "projects"
    monkeypatch.setattr(graph_api.Config, "UPLOAD_FOLDER", str(uploads_dir))
    monkeypatch.setattr(graph_api.Config, "ZEP_API_KEY", "test-zep-key")
    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(projects_dir))
    _reset_task_manager()

    builder_calls = {"count": 0}

    class FakeGraphBuilderService:
        def __init__(self, api_key=None):
            builder_calls["count"] += 1
            self.api_key = api_key

        def create_graph(self, name):
            return "zep_graph_123"

        def set_ontology(self, graph_id, ontology):
            return None

        def add_text_batches(self, graph_id, chunks, batch_size=3, progress_callback=None):
            if progress_callback:
                progress_callback("added", 1.0)
            return ["episode-1"]

        def _wait_for_episodes(self, episode_uuids, progress_callback=None):
            if progress_callback:
                progress_callback("done", 1.0)

        def get_graph_data(self, graph_id):
            return {"graph_id": graph_id, "nodes": [], "edges": [], "node_count": 0, "edge_count": 0}

    class ImmediateThread:
        def __init__(self, target=None, daemon=None):
            self._target = target
            self.daemon = daemon

        def start(self):
            self._target()

    monkeypatch.setattr(graph_api, "GraphBuilderService", FakeGraphBuilderService)
    monkeypatch.setattr(graph_api.threading, "Thread", ImmediateThread)
    monkeypatch.setattr(graph_api.TextProcessor, "split_text", staticmethod(lambda text, chunk_size, overlap: [text]))

    project = ProjectManager.create_project(name="Default Build")
    project.status = ProjectStatus.ONTOLOGY_GENERATED
    project.ontology = {"entity_types": [{"name": "Entity", "attributes": []}], "edge_types": []}
    ProjectManager.save_project(project)
    ProjectManager.save_extracted_text(project.project_id, "legacy graph text")

    app = _create_test_app()
    client = app.test_client()

    response = client.post("/api/graph/build", json={"project_id": project.project_id})

    assert response.status_code == 200
    assert builder_calls["count"] == 1

    task = TaskManager().get_task(response.get_json()["data"]["task_id"])
    saved_project = ProjectManager.get_project(project.project_id)

    assert task is not None
    assert task.status == TaskStatus.COMPLETED
    assert saved_project is not None
    assert saved_project.graph_id == "zep_graph_123"


def test_create_simulation_defaults_to_legacy_mode_when_project_type_missing(tmp_path, monkeypatch):
    uploads_dir = tmp_path / "uploads"
    projects_dir = uploads_dir / "projects"
    monkeypatch.setattr(graph_api.Config, "UPLOAD_FOLDER", str(uploads_dir))
    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(projects_dir))
    _configure_simulation_storage(tmp_path, monkeypatch)

    project = ProjectManager.create_project(name="Legacy Simulation")
    project.graph_id = "zep_graph_legacy"
    ProjectManager.save_project(project)

    app = _create_test_app()
    client = app.test_client()

    response = client.post("/api/simulation/create", json={"project_id": project.project_id})

    assert response.status_code == 200
    payload = response.get_json()["data"]
    assert payload["project_type"] == "default"
    assert payload["consumer_mode"] is False
    assert payload["graph_id"] == "zep_graph_legacy"


def test_prepare_consumer_simulation_uses_persona_pack_and_writes_consumer_artifacts(
    tmp_path, monkeypatch
):
    uploads_dir = tmp_path / "uploads"
    projects_dir = uploads_dir / "projects"
    simulations_dir = _configure_simulation_storage(tmp_path, monkeypatch)
    monkeypatch.setattr(graph_api.Config, "UPLOAD_FOLDER", str(uploads_dir))
    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(projects_dir))
    _reset_task_manager()

    class ExplodingZepEntityReader:
        def __init__(self, *args, **kwargs):
            raise AssertionError("Consumer prepare should not initialize ZepEntityReader")

    class ImmediateThread:
        def __init__(self, target=None, daemon=None):
            self._target = target
            self.daemon = daemon

        def start(self):
            self._target()

    monkeypatch.setattr(simulation_api, "ZepEntityReader", ExplodingZepEntityReader)
    monkeypatch.setattr(threading, "Thread", ImmediateThread)

    project = ProjectManager.create_project(name="Consumer Simulation")
    project.project_type = "consumer_test"
    project.graph_id = f"consumer_{project.project_id}"
    project.consumer_brief = _consumer_brief_payload()
    ProjectManager.save_project(project)
    ProjectManager.save_extracted_text(
        project.project_id,
        "Some shoppers say the finish spreads quickly through creator circles.",
    )

    app = _create_test_app()
    client = app.test_client()

    create_response = client.post("/api/simulation/create", json={"project_id": project.project_id})
    assert create_response.status_code == 200
    simulation_id = create_response.get_json()["data"]["simulation_id"]

    prepare_response = client.post("/api/simulation/prepare", json={"simulation_id": simulation_id})

    assert prepare_response.status_code == 200
    prepare_payload = prepare_response.get_json()["data"]
    task = TaskManager().get_task(prepare_payload["task_id"])

    assert task is not None
    assert task.status == TaskStatus.COMPLETED
    assert task.result["consumer_mode"] is True
    assert task.result["project_type"] == "consumer_test"
    assert task.result["profiles_count"] > 0
    assert task.result["persona_pack_id"]
    assert task.result["pinned_brief_summary"]

    simulation_dir = simulations_dir / simulation_id
    state_payload = json.loads((simulation_dir / "state.json").read_text(encoding="utf-8"))
    reddit_profiles = json.loads((simulation_dir / "reddit_profiles.json").read_text(encoding="utf-8"))
    config_payload = json.loads((simulation_dir / "simulation_config.json").read_text(encoding="utf-8"))

    assert state_payload["consumer_mode"] is True
    assert state_payload["project_type"] == "consumer_test"
    assert state_payload["persona_pack_id"]
    assert state_payload["pinned_brief_summary"]
    assert len(reddit_profiles) == task.result["profiles_count"]
    assert config_payload["consumer_mode"] is True
    assert config_payload["project_type"] == "consumer_test"
    assert config_payload["persona_pack_id"]
    assert config_payload["pinned_brief_summary"]
    assert (simulation_dir / "twitter_profiles.csv").exists()


def test_consumer_summary_route_returns_voc_and_shift(tmp_path, monkeypatch):
    uploads_dir = tmp_path / "uploads"
    projects_dir = uploads_dir / "projects"
    simulations_dir = _configure_simulation_storage(tmp_path, monkeypatch)
    monkeypatch.setattr(graph_api.Config, "UPLOAD_FOLDER", str(uploads_dir))
    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(projects_dir))

    project = ProjectManager.create_project(name="Consumer Summary")
    project.project_type = "consumer_test"
    project.graph_id = f"consumer_{project.project_id}"
    project.consumer_brief = _consumer_brief_payload()
    ProjectManager.save_project(project)

    state = SimulationManager().create_simulation(
        project_id=project.project_id,
        graph_id=project.graph_id,
        project_type="consumer_test",
    )
    _write_consumer_rounds(simulations_dir, state.simulation_id)

    app = _create_test_app()
    client = app.test_client()

    response = client.get(f"/api/simulation/{state.simulation_id}/consumer-summary")

    assert response.status_code == 200
    payload = response.get_json()["data"]
    assert payload["summary"]["attitude_shift_rate"] > 0
    assert payload["representative_voc_quotes"]["risk"][0]["quote"].startswith("Low sugar")


def test_generate_consumer_report_includes_voc_quotes(tmp_path, monkeypatch):
    uploads_dir = tmp_path / "uploads"
    projects_dir = uploads_dir / "projects"
    simulations_dir = _configure_simulation_storage(tmp_path, monkeypatch)
    reports_dir = _configure_report_storage(tmp_path, monkeypatch)
    monkeypatch.setattr(graph_api.Config, "UPLOAD_FOLDER", str(uploads_dir))
    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(projects_dir))
    _reset_task_manager()

    class ImmediateThread:
        def __init__(self, target=None, daemon=None):
            self._target = target
            self.daemon = daemon

        def start(self):
            self._target()

    monkeypatch.setattr(threading, "Thread", ImmediateThread)

    project = ProjectManager.create_project(name="Consumer Report")
    project.project_type = "consumer_test"
    project.graph_id = f"consumer_{project.project_id}"
    project.consumer_brief = _consumer_brief_payload()
    ProjectManager.save_project(project)

    state = SimulationManager().create_simulation(
        project_id=project.project_id,
        graph_id=project.graph_id,
        project_type="consumer_test",
    )
    _write_consumer_rounds(simulations_dir, state.simulation_id)

    app = _create_test_app()
    client = app.test_client()

    response = client.post("/api/report/generate", json={"simulation_id": state.simulation_id})

    assert response.status_code == 200
    payload = response.get_json()["data"]
    task = TaskManager().get_task(payload["task_id"])

    assert task is not None
    assert task.status == TaskStatus.COMPLETED
    report = ReportManager.get_report(task.result["report_id"])
    assert report is not None
    assert report.outline.title.startswith("消费者传播测试")
    assert "This actually sounds like a real breakfast fix." in report.markdown_content
    assert "Low sugar? I don't trust that claim" in report.markdown_content
    assert reports_dir.exists()
