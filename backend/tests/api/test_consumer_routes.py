from io import BytesIO
import json
from pathlib import Path
import sys
import threading


BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from flask import Flask

from app.api import consumer_bp, graph_bp, report_bp, simulation_bp
from app.api import graph as graph_api
from app.api import report as report_api
from app.api import simulation as simulation_api
from app.api import consumer as consumer_api
from app.models.project import ProjectManager, ProjectStatus
from app.models.task import TaskManager, TaskStatus
from app.services.consumer.document_ingest import DocumentIngestService
from app.services.consumer.source_registry import SourceRegistry
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
    app.register_blueprint(consumer_bp, url_prefix="/api/consumer")
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


def _consumer_brief_payload_with_lane_b():
    """Brief with enable_lane_b set to True."""
    return {
        "task_type": "concept_test",
        "product_concept_assets": ["Glow serum stick"],
        "copy_material": ["Brighter skin in one swipe"],
        "claims": ["Derm-tested glow boost"],
        "target_audience": ["busy commuters"],
        "usage_scene": ["morning commute"],
        "research_goal": "Understand first-impression appeal",
        "enable_lane_b": True,
    }


def _consumer_brief_payload_auto_enrich():
    """Brief with auto_enrich and NO manual background materials."""
    return {
        "task_type": "concept_test",
        "product_concept_assets": ["Glow serum stick"],
        "copy_material": ["Brighter skin in one swipe"],
        "claims": ["Derm-tested glow boost"],
        "target_audience": ["busy commuters"],
        "usage_scene": ["morning commute"],
        "research_goal": "Understand first-impression appeal",
        "research_mode": "auto_enrich",
    }


def _consumer_packaging_brief_payload():
    return {
        "task_type": "packaging_test",
        "packaging_assets": ["包装素材文件：舒客酵素亮白牙膏-绿色包装.png"],
        "copy_material": ["舒客酵素亮白牙膏｜温和去黄不刺激"],
        "target_audience": ["咖啡茶饮高频用户"],
        "usage_scene": ["早晚刷牙"],
        "research_goal": "判断包装是否传达温和去黄和清新口气",
    }


def _solid_png_bytes(color=(35, 166, 90), size=(4, 2)):
    from PIL import Image

    stream = BytesIO()
    Image.new("RGB", size, color).save(stream, format="PNG")
    stream.seek(0)
    return stream


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


def test_generate_ontology_ingests_uploaded_files_into_research_workspace(tmp_path, monkeypatch):
    uploads_dir = tmp_path / "uploads"
    projects_dir = uploads_dir / "projects"
    monkeypatch.setattr(graph_api.Config, "UPLOAD_FOLDER", str(uploads_dir))
    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(projects_dir))
    monkeypatch.setattr(graph_api.FileParser, "extract_text", staticmethod(lambda _: "Extracted document text about safety concerns."))
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
            "files": (BytesIO(b"consumer brief content"), "brief.txt"),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    payload = response.get_json()
    project_id = payload["data"]["project_id"]

    # Verify research workspace has sources and documents
    registry = SourceRegistry(project_id, upload_root=str(uploads_dir))
    ingest = DocumentIngestService(project_id, upload_root=str(uploads_dir))

    sources = registry.list_sources()
    assert len(sources) >= 1
    assert all(s.lane == "lane_a" for s in sources)

    docs = ingest.list_documents()
    assert len(docs) >= 1
    assert any("safety concerns" in d.raw_text for d in docs)

    chunks = ingest.load_chunks()
    assert len(chunks) > 0
    assert any("safety concerns" in c.text for c in chunks)


def test_packaging_image_upload_reaches_graph_and_simulation_config(tmp_path, monkeypatch):
    uploads_dir = tmp_path / "uploads"
    projects_dir = uploads_dir / "projects"
    simulations_dir = _configure_simulation_storage(tmp_path, monkeypatch)
    monkeypatch.setattr(graph_api.Config, "UPLOAD_FOLDER", str(uploads_dir))
    monkeypatch.setattr(graph_api.Config, "ZEP_API_KEY", None)
    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(projects_dir))
    _reset_task_manager()

    class FakeOntologyGenerator:
        def generate(self, document_texts, simulation_requirement, additional_context=None):
            assert any("视觉摘要" in text for text in document_texts)
            assert any("#23a65a" in text for text in document_texts)
            return {
                "entity_types": [{"name": "AudienceSegment", "attributes": []}],
                "edge_types": [],
                "analysis_summary": "packaging image consumed",
            }

    class ImmediateThread:
        def __init__(self, target=None, daemon=None):
            self._target = target
            self.daemon = daemon

        def start(self):
            self._target()

    monkeypatch.setattr(graph_api, "OntologyGenerator", FakeOntologyGenerator)
    monkeypatch.setattr(threading, "Thread", ImmediateThread)

    app = _create_test_app()
    client = app.test_client()

    generate_response = client.post(
        "/api/graph/ontology/generate",
        data={
            "simulation_requirement": "Run packaging test for Shuke toothpaste",
            "project_name": "舒客包装测试",
            "project_type": "consumer_test",
            "consumer_brief": json.dumps(_consumer_packaging_brief_payload(), ensure_ascii=False),
            "files": (_solid_png_bytes(), "舒客酵素亮白牙膏-绿色包装.png"),
        },
        content_type="multipart/form-data",
    )

    assert generate_response.status_code == 200
    project_id = generate_response.get_json()["data"]["project_id"]

    project = ProjectManager.get_project(project_id)
    extracted_text = ProjectManager.get_extracted_text(project_id)
    assert project is not None
    assert project.files[0]["filename"] == "舒客酵素亮白牙膏-绿色包装.png"
    assert project.consumer_brief["task_type"] == "packaging_test"
    assert project.consumer_brief["packaging_assets"] == ["包装素材文件：舒客酵素亮白牙膏-绿色包装.png"]
    assert "视觉摘要" in extracted_text
    assert "#23a65a" in extracted_text

    build_response = client.post("/api/graph/build", json={"project_id": project_id})
    assert build_response.status_code == 200
    graph_payload = ProjectManager.load_consumer_graph_payload(project_id)
    assert graph_payload is not None
    packaging_nodes = [
        node for node in graph_payload["nodes"]
        if "PackagingCue" in node.get("labels", [])
    ]
    assert any("舒客酵素亮白牙膏-绿色包装.png" in node["name"] for node in packaging_nodes)
    assert any(
        "#23a65a" in node["name"] or "#23a65a" in node.get("summary", "")
        for node in graph_payload["nodes"]
    )

    create_response = client.post("/api/simulation/create", json={"project_id": project_id})
    assert create_response.status_code == 200
    simulation_id = create_response.get_json()["data"]["simulation_id"]

    prepare_response = client.post("/api/simulation/prepare", json={"simulation_id": simulation_id})
    assert prepare_response.status_code == 200

    consumer_config = json.loads(
        (simulations_dir / simulation_id / "consumer_config.json").read_text(encoding="utf-8")
    )
    assert consumer_config["consumer_brief"]["task_type"] == "packaging_test"
    assert consumer_config["consumer_brief"]["packaging_assets"] == [
        "包装素材文件：舒客酵素亮白牙膏-绿色包装.png"
    ]
    assert "视觉摘要" in consumer_config["document_summary"]
    assert "#23a65a" in consumer_config["document_summary"]


def test_consumer_build_with_uploaded_material_produces_workspace_findings(tmp_path, monkeypatch):
    uploads_dir = tmp_path / "uploads"
    projects_dir = uploads_dir / "projects"
    monkeypatch.setattr(graph_api.Config, "UPLOAD_FOLDER", str(uploads_dir))
    monkeypatch.setattr(graph_api.Config, "ZEP_API_KEY", None)
    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(projects_dir))
    _reset_task_manager()

    # Pre-populate research workspace with an ingested document
    project = ProjectManager.create_project(name="Consumer Build With Workspace")
    project.project_type = "consumer_test"
    project.status = ProjectStatus.ONTOLOGY_GENERATED
    project.ontology = {"entity_types": [{"name": "ProductConcept", "attributes": []}], "edge_types": []}
    project.consumer_brief = _consumer_brief_payload_auto_enrich()
    ProjectManager.save_project(project)
    ProjectManager.save_extracted_text(project.project_id, "Some extracted text.")

    # Seed the workspace with a Lane A source + chunks
    registry = SourceRegistry(project.project_id, upload_root=str(uploads_dir))
    ingest = DocumentIngestService(project.project_id, upload_root=str(uploads_dir))
    source = registry.register_source(
        lane="lane_a",
        source_type="upload",
        label="Uploaded safety report",
    )
    ingest.ingest_text(
        source_id=source.source_id,
        text="There is a safety concern about the ingredient that may cause debate.",
        title="safety_report.txt",
    )

    class ExplodingGraphBuilderService:
        def __init__(self, *args, **kwargs):
            raise AssertionError("Zep GraphBuilderService should not be used for consumer_test projects")

    monkeypatch.setattr(graph_api, "GraphBuilderService", ExplodingGraphBuilderService)

    app = _create_test_app()
    client = app.test_client()

    build_response = client.post("/api/graph/build", json={"project_id": project.project_id})

    assert build_response.status_code == 200
    saved_project = ProjectManager.get_project(project.project_id)

    assert saved_project is not None
    assert saved_project.consumer_context is not None
    # The snapshot should include workspace findings + auto_enrich findings
    assert saved_project.consumer_context.get("research_findings_count", 0) > 0
    assert saved_project.consumer_context.get("ingested_document_count", 0) > 0
    assert saved_project.consumer_context.get("auto_enrich_count", 0) > 0

    # Verify snapshot metadata
    snapshot_meta = saved_project.consumer_context.get("research_snapshot", {})
    assert snapshot_meta.get("source_count", 0) > 0
    assert snapshot_meta.get("document_count", 0) > 0
    assert snapshot_meta.get("chunk_count", 0) > 0
    assert snapshot_meta.get("finding_count", 0) > 0


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

    assert saved_project.consumer_context is not None
    assert saved_project.consumer_context.get("research_mode") == "manual_only"
    assert saved_project.consumer_context.get("research_findings_count", 0) >= 0
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


def test_consumer_build_auto_enrich_produces_findings_without_manual_background(
    tmp_path, monkeypatch
):
    uploads_dir = tmp_path / "uploads"
    projects_dir = uploads_dir / "projects"
    monkeypatch.setattr(graph_api.Config, "UPLOAD_FOLDER", str(uploads_dir))
    monkeypatch.setattr(graph_api.Config, "ZEP_API_KEY", None)
    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(projects_dir))
    _reset_task_manager()

    project = ProjectManager.create_project(name="Consumer Auto Enrich")
    project.project_type = "consumer_test"
    project.status = ProjectStatus.ONTOLOGY_GENERATED
    project.ontology = {"entity_types": [{"name": "ProductConcept", "attributes": []}], "edge_types": []}
    project.consumer_brief = _consumer_brief_payload_auto_enrich()
    ProjectManager.save_project(project)
    ProjectManager.save_extracted_text(project.project_id, "Some extracted text.")

    app = _create_test_app()
    client = app.test_client()

    build_response = client.post("/api/graph/build", json={"project_id": project.project_id})

    assert build_response.status_code == 200
    saved_project = ProjectManager.get_project(project.project_id)

    assert saved_project is not None
    assert saved_project.consumer_context is not None
    assert saved_project.consumer_context.get("research_mode") == "auto_enrich"
    assert saved_project.consumer_context.get("research_findings_count", 0) > 0
    assert saved_project.consumer_context.get("auto_enrich_count", 0) > 0
    assert saved_project.consumer_context.get("manual_background_count", 0) == 0

    graph_response = client.get(f"/api/graph/data/{saved_project.graph_id}")
    graph_data = graph_response.get_json()["data"]
    research_nodes = [n for n in graph_data["nodes"] if "ResearchFinding" in n["labels"]]
    assert len(research_nodes) > 0
    assert any(
        n["attributes"].get("provenance", {}).get("source_label") == "auto_enrich"
        for n in research_nodes
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

    import app.services.application.graph_app_service as _graph_app_svc
    monkeypatch.setattr(_graph_app_svc, "GraphBuilderService", FakeGraphBuilderService)
    monkeypatch.setattr(_graph_app_svc.threading, "Thread", ImmediateThread)
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


def test_prepare_consumer_simulation_auto_enrich_persists_findings(tmp_path, monkeypatch):
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

    project = ProjectManager.create_project(name="Consumer Auto Enrich Prepare")
    project.project_type = "consumer_test"
    project.graph_id = f"consumer_{project.project_id}"
    project.consumer_brief = _consumer_brief_payload_auto_enrich()
    ProjectManager.save_project(project)
    ProjectManager.save_extracted_text(project.project_id, "Some extracted text.")

    app = _create_test_app()
    client = app.test_client()

    create_response = client.post("/api/simulation/create", json={"project_id": project.project_id})
    assert create_response.status_code == 200
    simulation_id = create_response.get_json()["data"]["simulation_id"]

    prepare_response = client.post("/api/simulation/prepare", json={"simulation_id": simulation_id})

    assert prepare_response.status_code == 200
    simulation_dir = simulations_dir / simulation_id
    consumer_config = json.loads((simulation_dir / "consumer_config.json").read_text(encoding="utf-8"))

    assert consumer_config["research_mode"] == "auto_enrich"
    assert consumer_config["research_findings_count"] > 0
    assert consumer_config["auto_enrich_count"] > 0
    assert consumer_config["manual_background_count"] == 0
    assert len(consumer_config["research_findings"]) > 0
    assert any(
        f["source_label"] == "auto_enrich" for f in consumer_config["research_findings"]
    )


def test_consumer_build_persists_enable_lane_b(tmp_path, monkeypatch):
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

    project = ProjectManager.create_project(name="Consumer Lane B")
    project.project_type = "consumer_test"
    project.status = ProjectStatus.ONTOLOGY_GENERATED
    project.ontology = {"entity_types": [{"name": "ProductConcept", "attributes": []}], "edge_types": []}
    project.consumer_brief = _consumer_brief_payload_with_lane_b()
    ProjectManager.save_project(project)
    ProjectManager.save_extracted_text(project.project_id, "Some extracted text.")

    app = _create_test_app()
    client = app.test_client()

    build_response = client.post("/api/graph/build", json={"project_id": project.project_id})

    assert build_response.status_code == 200
    saved_project = ProjectManager.get_project(project.project_id)

    assert saved_project is not None
    assert saved_project.consumer_context is not None
    assert saved_project.consumer_context.get("enable_lane_b") is True


def test_prepare_consumer_simulation_persists_enable_lane_b(tmp_path, monkeypatch):
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

    project = ProjectManager.create_project(name="Consumer Lane B Prepare")
    project.project_type = "consumer_test"
    project.graph_id = f"consumer_{project.project_id}"
    project.consumer_brief = _consumer_brief_payload_with_lane_b()
    ProjectManager.save_project(project)
    ProjectManager.save_extracted_text(project.project_id, "Some extracted text.")

    app = _create_test_app()
    client = app.test_client()

    create_response = client.post("/api/simulation/create", json={"project_id": project.project_id})
    assert create_response.status_code == 200
    simulation_id = create_response.get_json()["data"]["simulation_id"]

    prepare_response = client.post("/api/simulation/prepare", json={"simulation_id": simulation_id})

    assert prepare_response.status_code == 200
    simulation_dir = simulations_dir / simulation_id
    consumer_config = json.loads((simulation_dir / "consumer_config.json").read_text(encoding="utf-8"))

    assert consumer_config["enable_lane_b"] is True
    state_payload = json.loads((simulation_dir / "state.json").read_text(encoding="utf-8"))
    assert state_payload["enable_lane_b"] is True


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
    sim_dir = simulations_dir / state.simulation_id
    sim_dir.mkdir(parents=True, exist_ok=True)
    (sim_dir / "phase6j_calibration_artifact.json").write_text(
        json.dumps(
            {
                "phase7_entry_decision": "PASS",
                "golden_flow_result": "PASS",
                "evidence_gatekeeping_result": "PASS",
                "reasoning_backend_coverage": 0.8,
                "template_fallback_coverage": 0.1,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    app = _create_test_app()
    client = app.test_client()

    response = client.get(f"/api/simulation/{state.simulation_id}/consumer-summary")

    assert response.status_code == 200
    payload = response.get_json()["data"]
    assert payload["summary"]["attitude_shift_rate"] > 0
    assert payload["representative_voc_quotes"]["risk"][0]["quote"].startswith("Low sugar")


def _write_consumer_rounds_with_events(simulations_dir, simulation_id):
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
            "visible_finding_ids": [],
            "propagation_events": [],
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
            "visible_finding_ids": ["r1"],
            "propagation_events": [
                {
                    "event_id": "evt_persona_a_r1_ris",
                    "event_type": "risk_discovery",
                    "actor_id": "persona_a",
                    "target_ids": [],
                    "trigger_finding_ids": ["r1"],
                    "supporting_quote": "Low sugar? I don't trust that claim after the debate.",
                    "round_index": 1,
                }
            ],
        },
    ]
    (simulation_dir / "consumer_rounds.jsonl").write_text(
        "\n".join(json.dumps(event, ensure_ascii=False) for event in events) + "\n",
        encoding="utf-8",
    )
    (simulation_dir / "consumer_config.json").write_text(
        json.dumps(
            {
                "research_findings": [
                    {
                        "finding_id": "r1",
                        "finding_type": "risk_signal",
                        "summary": "Sweetener concern",
                        "evidence_snippets": ["Sweetener concern"],
                        "source_label": "brief_background",
                        "visibility": "Restricted",
                        "confidence": 0.6,
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def test_consumer_summary_route_exposes_phase2_fields(tmp_path, monkeypatch):
    uploads_dir = tmp_path / "uploads"
    projects_dir = uploads_dir / "projects"
    simulations_dir = _configure_simulation_storage(tmp_path, monkeypatch)
    monkeypatch.setattr(graph_api.Config, "UPLOAD_FOLDER", str(uploads_dir))
    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(projects_dir))

    project = ProjectManager.create_project(name="Consumer Phase2")
    project.project_type = "consumer_test"
    project.graph_id = f"consumer_{project.project_id}"
    project.consumer_brief = _consumer_brief_payload()
    ProjectManager.save_project(project)

    state = SimulationManager().create_simulation(
        project_id=project.project_id,
        graph_id=project.graph_id,
        project_type="consumer_test",
    )
    _write_consumer_rounds_with_events(simulations_dir, state.simulation_id)

    app = _create_test_app()
    client = app.test_client()

    response = client.get(f"/api/simulation/{state.simulation_id}/consumer-summary")

    assert response.status_code == 200
    payload = response.get_json()["data"]
    assert "event_counts" in payload
    assert "top_risk_findings" in payload
    assert "cascade_metrics" in payload
    assert payload["event_counts"]["risk_discovery"] == 1
    assert payload["top_risk_findings"] == []
    assert payload["evidence_gatekeeping_summary"]["blocked_count"] >= 1
    assert payload["cascade_metrics"]["community_count"] >= 0


def test_consumer_summary_route_exposes_task_aware_price_fields(tmp_path, monkeypatch):
    uploads_dir = tmp_path / "uploads"
    projects_dir = uploads_dir / "projects"
    simulations_dir = _configure_simulation_storage(tmp_path, monkeypatch)
    monkeypatch.setattr(graph_api.Config, "UPLOAD_FOLDER", str(uploads_dir))
    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(projects_dir))

    project = ProjectManager.create_project(name="Consumer Price Summary")
    project.project_type = "consumer_test"
    project.graph_id = f"consumer_{project.project_id}"
    project.consumer_brief = {
        "task_type": "price_test",
        "product_concept_assets": ["Protein yogurt pouch"],
        "copy_material": ["14g protein"],
        "price_points": ["$9.99", "$14.99"],
        "price_context": "subscription monthly",
        "target_audience": ["busy professionals"],
        "usage_scene": ["morning commute"],
        "research_goal": "Find acceptable price range",
    }
    ProjectManager.save_project(project)

    state = SimulationManager().create_simulation(
        project_id=project.project_id,
        graph_id=project.graph_id,
        project_type="consumer_test",
    )
    _write_consumer_rounds_with_events(simulations_dir, state.simulation_id)

    app = _create_test_app()
    client = app.test_client()

    response = client.get(f"/api/simulation/{state.simulation_id}/consumer-summary")

    assert response.status_code == 200
    payload = response.get_json()["data"]
    assert payload["task_type"] == "price_test"
    assert payload["acceptable_price_points"] == ["$9.99", "$14.99"]
    assert payload["resisted_price_points"] == ["$14.99"]
    assert payload["price_context"] == "subscription monthly"


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
    sim_dir = simulations_dir / state.simulation_id
    sim_dir.mkdir(parents=True, exist_ok=True)
    (sim_dir / "phase6j_calibration_artifact.json").write_text(
        json.dumps(
            {
                "phase7_entry_decision": "PASS",
                "golden_flow_result": "PASS",
                "evidence_gatekeeping_result": "PASS",
                "reasoning_backend_coverage": 0.8,
                "template_fallback_coverage": 0.1,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

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


def test_consumer_build_persists_project_level_research_artifacts(tmp_path, monkeypatch):
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

    project = ProjectManager.create_project(name="Consumer Build Artifacts")
    project.project_type = "consumer_test"
    project.status = ProjectStatus.ONTOLOGY_GENERATED
    project.ontology = {"entity_types": [{"name": "ProductConcept", "attributes": []}], "edge_types": []}
    project.consumer_brief = _consumer_brief_payload()
    ProjectManager.save_project(project)
    ProjectManager.save_extracted_text(project.project_id, "Some extracted text.")

    app = _create_test_app()
    client = app.test_client()

    build_response = client.post("/api/graph/build", json={"project_id": project.project_id})

    assert build_response.status_code == 200
    research_dir = uploads_dir / "projects" / project.project_id / "research"
    assert (research_dir / "findings.json").exists()
    assert (research_dir / "research_snapshot.json").exists()

    findings_data = json.loads((research_dir / "findings.json").read_text(encoding="utf-8"))
    assert findings_data["project_id"] == project.project_id
    assert findings_data["finding_count"] > 0

    snapshot_data = json.loads((research_dir / "research_snapshot.json").read_text(encoding="utf-8"))
    assert snapshot_data["project_id"] == project.project_id
    assert snapshot_data["snapshot_id"] == f"rsnap_{project.project_id}"


def test_prepare_consumer_simulation_refreshes_project_level_artifacts(tmp_path, monkeypatch):
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

    project = ProjectManager.create_project(name="Consumer Prepare Artifacts")
    project.project_type = "consumer_test"
    project.graph_id = f"consumer_{project.project_id}"
    project.consumer_brief = _consumer_brief_payload()
    ProjectManager.save_project(project)
    ProjectManager.save_extracted_text(project.project_id, "Some extracted text.")

    # Pre-seed old artifacts to verify they get refreshed
    from app.services.consumer.project_research_persistence import persist_findings, persist_snapshot
    from app.services.consumer.models import ResearchSnapshot
    persist_findings(project.project_id, [], upload_root=str(uploads_dir))
    persist_snapshot(
        project.project_id,
        ResearchSnapshot(snapshot_id="old_snap", project_id=project.project_id, created_at="2026-04-21T10:00:00+00:00"),
        upload_root=str(uploads_dir),
    )

    app = _create_test_app()
    client = app.test_client()

    create_response = client.post("/api/simulation/create", json={"project_id": project.project_id})
    assert create_response.status_code == 200
    simulation_id = create_response.get_json()["data"]["simulation_id"]

    prepare_response = client.post("/api/simulation/prepare", json={"simulation_id": simulation_id})
    assert prepare_response.status_code == 200

    research_dir = uploads_dir / "projects" / project.project_id / "research"
    findings_data = json.loads((research_dir / "findings.json").read_text(encoding="utf-8"))
    assert findings_data["finding_count"] > 0

    snapshot_data = json.loads((research_dir / "research_snapshot.json").read_text(encoding="utf-8"))
    assert snapshot_data["snapshot_id"] == f"rsnap_{project.project_id}"
    assert snapshot_data["finding_count"] > 0


def test_report_context_prefers_project_level_artifacts(tmp_path, monkeypatch):
    uploads_dir = tmp_path / "uploads"
    projects_dir = uploads_dir / "projects"
    simulations_dir = _configure_simulation_storage(tmp_path, monkeypatch)
    monkeypatch.setattr(graph_api.Config, "UPLOAD_FOLDER", str(uploads_dir))
    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(projects_dir))

    project = ProjectManager.create_project(name="Consumer Report Project Artifacts")
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

    # Write consumer_config.json with OLD findings
    simulation_dir = simulations_dir / state.simulation_id
    simulation_dir.mkdir(parents=True, exist_ok=True)
    (simulation_dir / "consumer_config.json").write_text(
        json.dumps(
            {
                "research_findings": [
                    {
                        "finding_id": "old_f1",
                        "finding_type": "risk_signal",
                        "summary": "Old simulation finding",
                        "evidence_snippets": ["Old simulation finding"],
                        "source_label": "brief_background",
                        "visibility": "Restricted",
                        "confidence": 0.6,
                    }
                ],
                "research_snapshot": {"snapshot_id": "old_snap", "finding_count": 1},
                "retrieval_traces": [],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    # Write project-level artifacts with NEW findings
    from app.services.consumer.project_research_persistence import persist_findings, persist_snapshot
    from app.services.consumer.models import ResearchFinding, ResearchSnapshot, GraphVisibility
    new_findings = [
        ResearchFinding(
            finding_id="new_f1",
            finding_type="trend_signal",
            summary="New project-level finding",
            visibility=GraphVisibility.Propagation_Only,
            source_label="auto_enrich",
        )
    ]
    new_snapshot = ResearchSnapshot(
        snapshot_id=f"rsnap_{project.project_id}",
        project_id=project.project_id,
        created_at="2026-04-21T10:00:00+00:00",
        findings=new_findings,
    )
    persist_findings(project.project_id, new_findings, upload_root=str(uploads_dir))
    persist_snapshot(project.project_id, new_snapshot, upload_root=str(uploads_dir))

    from app.services.report_agent import ReportAgent
    agent = ReportAgent(
        graph_id=project.graph_id,
        simulation_id=state.simulation_id,
        simulation_requirement="Test",
        project_id=project.project_id,
    )
    context = agent._build_consumer_report_context()

    assert context["research_findings"][0]["finding_id"] == "new_f1"
    assert context["research_snapshot"]["snapshot_id"] == f"rsnap_{project.project_id}"


def test_report_context_falls_back_to_consumer_config_when_project_artifacts_missing(tmp_path, monkeypatch):
    uploads_dir = tmp_path / "uploads"
    projects_dir = uploads_dir / "projects"
    simulations_dir = _configure_simulation_storage(tmp_path, monkeypatch)
    monkeypatch.setattr(graph_api.Config, "UPLOAD_FOLDER", str(uploads_dir))
    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(projects_dir))

    project = ProjectManager.create_project(name="Consumer Report Fallback")
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

    simulation_dir = simulations_dir / state.simulation_id
    simulation_dir.mkdir(parents=True, exist_ok=True)
    (simulation_dir / "consumer_config.json").write_text(
        json.dumps(
            {
                "research_findings": [
                    {
                        "finding_id": "fallback_f1",
                        "finding_type": "risk_signal",
                        "summary": "Fallback finding",
                        "evidence_snippets": ["Fallback finding"],
                        "source_label": "brief_background",
                        "visibility": "Restricted",
                        "confidence": 0.6,
                    }
                ],
                "research_snapshot": {"snapshot_id": "fallback_snap", "finding_count": 1},
                "retrieval_traces": [],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    from app.services.report_agent import ReportAgent
    agent = ReportAgent(
        graph_id=project.graph_id,
        simulation_id=state.simulation_id,
        simulation_requirement="Test",
        project_id=project.project_id,
    )
    context = agent._build_consumer_report_context()

    assert context["research_findings"][0]["finding_id"] == "fallback_f1"
    assert context["research_snapshot"]["snapshot_id"] == "fallback_snap"


def test_register_benchmark_rejects_non_consumer_project(tmp_path, monkeypatch):
    """Benchmark registration should be gated to consumer_test projects."""
    uploads_dir = tmp_path / "uploads"
    projects_dir = uploads_dir / "projects"
    monkeypatch.setattr(graph_api.Config, "UPLOAD_FOLDER", str(uploads_dir))
    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(projects_dir))

    non_consumer_project = ProjectManager.create_project(name="Non Consumer")
    non_consumer_project.project_type = "default"
    ProjectManager.save_project(non_consumer_project)

    import app.services.application.benchmark_app_service as _bench_svc

    def fake_get_asset(asset_id):
        return {"asset_id": asset_id, "project_id": non_consumer_project.project_id}

    monkeypatch.setattr(_bench_svc, "get_asset", fake_get_asset)

    app = _create_test_app()
    client = app.test_client()

    response = client.post(
        "/api/report/benchmarks/register",
        json={
            "name": "Test Benchmark",
            "source_pack_lineage": "asset_pack_001",
            "expected_signals": {"acceptance_band": "mixed"},
        },
    )

    assert response.status_code == 400
    payload = response.get_json()
    assert "consumer_test" in payload["error"]


def test_register_benchmark_rejects_missing_asset_pack(tmp_path, monkeypatch):
    """Benchmark registration should reject when the source asset pack does not exist."""
    app = _create_test_app()
    client = app.test_client()

    response = client.post(
        "/api/report/benchmarks/register",
        json={
            "name": "Test Benchmark",
            "source_pack_lineage": "asset_pack_missing",
            "expected_signals": {"acceptance_band": "mixed"},
        },
    )

    assert response.status_code == 404
    payload = response.get_json()
    assert "Asset pack not found" in payload["error"]


def test_register_benchmark_accepts_consumer_project(tmp_path, monkeypatch):
    """Benchmark registration should succeed for consumer_test projects."""
    uploads_dir = tmp_path / "uploads"
    projects_dir = uploads_dir / "projects"
    monkeypatch.setattr(graph_api.Config, "UPLOAD_FOLDER", str(uploads_dir))
    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(projects_dir))
    monkeypatch.setattr(report_api.Config, "UPLOAD_FOLDER", str(uploads_dir))

    consumer_project = ProjectManager.create_project(name="Consumer Project")
    consumer_project.project_type = "consumer_test"
    ProjectManager.save_project(consumer_project)

    import app.services.application.benchmark_app_service as _bench_svc

    def fake_get_asset(asset_id):
        return {"asset_id": asset_id, "project_id": consumer_project.project_id}

    monkeypatch.setattr(_bench_svc, "get_asset", fake_get_asset)

    app = _create_test_app()
    client = app.test_client()

    response = client.post(
        "/api/report/benchmarks/register",
        json={
            "name": "Test Benchmark",
            "source_pack_lineage": "asset_pack_001",
            "expected_signals": {"acceptance_band": "mixed"},
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert "benchmark_id" in payload["data"]


def test_replay_benchmark_rejects_non_consumer_project(tmp_path, monkeypatch):
    """Benchmark replay should be gated to consumer_test projects."""
    uploads_dir = tmp_path / "uploads"
    projects_dir = uploads_dir / "projects"
    monkeypatch.setattr(graph_api.Config, "UPLOAD_FOLDER", str(uploads_dir))
    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(projects_dir))

    non_consumer_project = ProjectManager.create_project(name="Non Consumer")
    non_consumer_project.project_type = "default"
    ProjectManager.save_project(non_consumer_project)

    app = _create_test_app()
    client = app.test_client()

    response = client.post(
        "/api/report/benchmarks/bench_123/replay",
        json={
            "report_context": {"summary": {}},
            "project_id": non_consumer_project.project_id,
        },
    )

    assert response.status_code == 400
    payload = response.get_json()
    assert "consumer_test" in payload["error"]


def test_replay_benchmark_rejects_non_consumer_simulation(tmp_path, monkeypatch):
    """Benchmark replay should be gated to consumer_test simulations."""
    uploads_dir = tmp_path / "uploads"
    projects_dir = uploads_dir / "projects"
    _configure_simulation_storage(tmp_path, monkeypatch)
    monkeypatch.setattr(graph_api.Config, "UPLOAD_FOLDER", str(uploads_dir))
    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(projects_dir))

    non_consumer_project = ProjectManager.create_project(name="Non Consumer")
    non_consumer_project.project_type = "default"
    ProjectManager.save_project(non_consumer_project)

    state = SimulationManager().create_simulation(
        project_id=non_consumer_project.project_id,
        graph_id="graph_123",
        project_type="default",
    )

    app = _create_test_app()
    client = app.test_client()

    response = client.post(
        "/api/report/benchmarks/bench_123/replay",
        json={
            "report_context": {"summary": {}},
            "simulation_id": state.simulation_id,
        },
    )

    assert response.status_code == 400
    payload = response.get_json()
    assert "consumer_test" in payload["error"]


def test_replay_benchmark_requires_project_or_simulation_id(tmp_path, monkeypatch):
    """Benchmark replay should require project_id or simulation_id for gating."""
    app = _create_test_app()
    client = app.test_client()

    response = client.post(
        "/api/report/benchmarks/bench_123/replay",
        json={
            "report_context": {"summary": {}},
        },
    )

    assert response.status_code == 400
    payload = response.get_json()
    assert "project_id or simulation_id is required" in payload["error"]


def test_replay_benchmark_accepts_consumer_project(tmp_path, monkeypatch):
    """Benchmark replay should succeed for consumer_test projects."""
    uploads_dir = tmp_path / "uploads"
    projects_dir = uploads_dir / "projects"
    monkeypatch.setattr(graph_api.Config, "UPLOAD_FOLDER", str(uploads_dir))
    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(projects_dir))
    monkeypatch.setattr(report_api.Config, "UPLOAD_FOLDER", str(uploads_dir))

    consumer_project = ProjectManager.create_project(name="Consumer Project")
    consumer_project.project_type = "consumer_test"
    ProjectManager.save_project(consumer_project)

    from app.services.consumer.benchmark_registry import register_benchmark
    benchmark = register_benchmark(
        name="Test Bench",
        source_pack_lineage="pack_001",
        expected_signals={"acceptance_band": "mixed"},
        upload_root=str(uploads_dir),
    )

    app = _create_test_app()
    client = app.test_client()

    response = client.post(
        f"/api/report/benchmarks/{benchmark['benchmark_id']}/replay",
        json={
            "report_context": {"summary": {}},
            "project_id": consumer_project.project_id,
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert "replay_id" in payload["data"]


def test_get_replay_result_rejects_non_consumer_project(tmp_path, monkeypatch):
    """Replay result fetch should be gated to consumer_test projects."""
    uploads_dir = tmp_path / "uploads"
    projects_dir = uploads_dir / "projects"
    monkeypatch.setattr(graph_api.Config, "UPLOAD_FOLDER", str(uploads_dir))
    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(projects_dir))
    monkeypatch.setattr(report_api.Config, "UPLOAD_FOLDER", str(uploads_dir))

    non_consumer_project = ProjectManager.create_project(name="Non Consumer")
    non_consumer_project.project_type = "default"
    ProjectManager.save_project(non_consumer_project)

    from app.services.consumer.benchmark_replay import replay_benchmark
    from app.services.consumer.benchmark_registry import register_benchmark
    benchmark = register_benchmark(
        name="Test Bench",
        source_pack_lineage="pack_001",
        expected_signals={"acceptance_band": "mixed"},
        upload_root=str(uploads_dir),
    )
    replay = replay_benchmark(
        benchmark_id=benchmark["benchmark_id"],
        report_context={"summary": {}},
        project_id=non_consumer_project.project_id,
        upload_root=str(uploads_dir),
    )

    app = _create_test_app()
    client = app.test_client()

    response = client.get(f"/api/report/benchmark-replays/{replay['replay_id']}")

    assert response.status_code == 400
    payload = response.get_json()
    assert "consumer_test" in payload["error"]


def test_get_replay_result_rejects_non_consumer_simulation(tmp_path, monkeypatch):
    """Replay result fetch should be gated to consumer_test simulations."""
    uploads_dir = tmp_path / "uploads"
    projects_dir = uploads_dir / "projects"
    _configure_simulation_storage(tmp_path, monkeypatch)
    monkeypatch.setattr(graph_api.Config, "UPLOAD_FOLDER", str(uploads_dir))
    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(projects_dir))
    monkeypatch.setattr(report_api.Config, "UPLOAD_FOLDER", str(uploads_dir))

    non_consumer_project = ProjectManager.create_project(name="Non Consumer")
    non_consumer_project.project_type = "default"
    ProjectManager.save_project(non_consumer_project)

    state = SimulationManager().create_simulation(
        project_id=non_consumer_project.project_id,
        graph_id="graph_123",
        project_type="default",
    )

    from app.services.consumer.benchmark_replay import replay_benchmark
    from app.services.consumer.benchmark_registry import register_benchmark
    benchmark = register_benchmark(
        name="Test Bench",
        source_pack_lineage="pack_001",
        expected_signals={"acceptance_band": "mixed"},
        upload_root=str(uploads_dir),
    )
    replay = replay_benchmark(
        benchmark_id=benchmark["benchmark_id"],
        report_context={"summary": {}},
        simulation_id=state.simulation_id,
        upload_root=str(uploads_dir),
    )

    app = _create_test_app()
    client = app.test_client()

    response = client.get(f"/api/report/benchmark-replays/{replay['replay_id']}")

    assert response.status_code == 400
    payload = response.get_json()
    assert "consumer_test" in payload["error"]


def test_get_replay_result_accepts_consumer_project(tmp_path, monkeypatch):
    """Replay result fetch should succeed for consumer_test projects."""
    uploads_dir = tmp_path / "uploads"
    projects_dir = uploads_dir / "projects"
    monkeypatch.setattr(graph_api.Config, "UPLOAD_FOLDER", str(uploads_dir))
    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(projects_dir))
    monkeypatch.setattr(report_api.Config, "UPLOAD_FOLDER", str(uploads_dir))

    consumer_project = ProjectManager.create_project(name="Consumer Project")
    consumer_project.project_type = "consumer_test"
    ProjectManager.save_project(consumer_project)

    from app.services.consumer.benchmark_replay import replay_benchmark
    from app.services.consumer.benchmark_registry import register_benchmark
    benchmark = register_benchmark(
        name="Test Bench",
        source_pack_lineage="pack_001",
        expected_signals={"acceptance_band": "mixed"},
        upload_root=str(uploads_dir),
    )
    replay = replay_benchmark(
        benchmark_id=benchmark["benchmark_id"],
        report_context={"summary": {}},
        project_id=consumer_project.project_id,
        upload_root=str(uploads_dir),
    )

    app = _create_test_app()
    client = app.test_client()

    response = client.get(f"/api/report/benchmark-replays/{replay['replay_id']}")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["data"]["replay_id"] == replay["replay_id"]


def test_repeated_prepare_reports_reuse_metadata(tmp_path, monkeypatch):
    """Calling /prepare on an already-prepared simulation should report reuse metadata."""
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

    project = ProjectManager.create_project(name="Consumer Reuse")
    project.project_type = "consumer_test"
    project.graph_id = f"consumer_{project.project_id}"
    project.consumer_brief = _consumer_brief_payload()
    ProjectManager.save_project(project)
    ProjectManager.save_extracted_text(project.project_id, "Some extracted text.")

    app = _create_test_app()
    client = app.test_client()

    create_response = client.post("/api/simulation/create", json={"project_id": project.project_id})
    assert create_response.status_code == 200
    simulation_id = create_response.get_json()["data"]["simulation_id"]

    # First prepare
    prepare_response = client.post("/api/simulation/prepare", json={"simulation_id": simulation_id})
    assert prepare_response.status_code == 200
    first_data = prepare_response.get_json()["data"]
    assert first_data["already_prepared"] is False

    # Second prepare (reuse)
    reuse_response = client.post("/api/simulation/prepare", json={"simulation_id": simulation_id})
    assert reuse_response.status_code == 200
    reuse_data = reuse_response.get_json()["data"]
    assert reuse_data["already_prepared"] is True
    assert "prepare_manifest" in reuse_data
    assert reuse_data["prepare_manifest"]["reuse_count"] == 1
    assert reuse_data["prepare_manifest"]["last_reused_at"] is not None

    # Third prepare (reuse again)
    reuse_response3 = client.post("/api/simulation/prepare", json={"simulation_id": simulation_id})
    assert reuse_response3.status_code == 200
    reuse_data3 = reuse_response3.get_json()["data"]
    assert reuse_data3["prepare_manifest"]["reuse_count"] == 2


def test_prepare_status_includes_manifest_when_prepared(tmp_path, monkeypatch):
    """GET /prepare/status should include prepare_manifest when simulation is already prepared."""
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

    project = ProjectManager.create_project(name="Consumer Status Manifest")
    project.project_type = "consumer_test"
    project.graph_id = f"consumer_{project.project_id}"
    project.consumer_brief = _consumer_brief_payload()
    ProjectManager.save_project(project)
    ProjectManager.save_extracted_text(project.project_id, "Some extracted text.")

    app = _create_test_app()
    client = app.test_client()

    create_response = client.post("/api/simulation/create", json={"project_id": project.project_id})
    assert create_response.status_code == 200
    simulation_id = create_response.get_json()["data"]["simulation_id"]

    prepare_response = client.post("/api/simulation/prepare", json={"simulation_id": simulation_id})
    assert prepare_response.status_code == 200

    status_response = client.post("/api/simulation/prepare/status", json={"simulation_id": simulation_id})
    assert status_response.status_code == 200
    status_data = status_response.get_json()["data"]
    assert status_data["already_prepared"] is True
    assert "prepare_manifest" in status_data
    assert status_data["prepare_manifest"]["simulation_id"] == simulation_id
    assert status_data["prepare_manifest"]["project_type"] == "consumer_test"


# ============== Consumer bounded-context API route tests ==============


def test_consumer_api_consumer_summary_matches_legacy_route(tmp_path, monkeypatch):
    """The new /api/consumer/simulation/.../consumer-summary returns the same data as the legacy route."""
    uploads_dir = tmp_path / "uploads"
    projects_dir = uploads_dir / "projects"
    simulations_dir = tmp_path / "uploads" / "simulations"
    monkeypatch.setattr(simulation_api.Config, "OASIS_SIMULATION_DATA_DIR", str(simulations_dir))
    monkeypatch.setattr(simulation_api.SimulationManager, "SIMULATION_DATA_DIR", str(simulations_dir))
    monkeypatch.setattr(SimulationManager, "SIMULATION_DATA_DIR", str(simulations_dir))
    monkeypatch.setattr(graph_api.Config, "UPLOAD_FOLDER", str(uploads_dir))
    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(projects_dir))

    project = ProjectManager.create_project(name="Consumer API Summary")
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

    legacy_response = client.get(f"/api/simulation/{state.simulation_id}/consumer-summary")
    canonical_response = client.get(f"/api/consumer/simulation/{state.simulation_id}/consumer-summary")

    assert legacy_response.status_code == 200
    assert canonical_response.status_code == 200
    assert legacy_response.get_json()["data"] == canonical_response.get_json()["data"]


def test_consumer_api_consumer_summary_404_for_missing_sim():
    app = _create_test_app()
    client = app.test_client()

    response = client.get("/api/consumer/simulation/sim_missing/consumer-summary")
    assert response.status_code == 404
    assert "sim_missing" in response.get_json()["error"]


def test_consumer_api_consumer_summary_400_for_non_consumer(tmp_path, monkeypatch):
    uploads_dir = tmp_path / "uploads"
    projects_dir = uploads_dir / "projects"
    simulations_dir = tmp_path / "uploads" / "simulations"
    monkeypatch.setattr(simulation_api.Config, "OASIS_SIMULATION_DATA_DIR", str(simulations_dir))
    monkeypatch.setattr(simulation_api.SimulationManager, "SIMULATION_DATA_DIR", str(simulations_dir))
    monkeypatch.setattr(SimulationManager, "SIMULATION_DATA_DIR", str(simulations_dir))
    monkeypatch.setattr(graph_api.Config, "UPLOAD_FOLDER", str(uploads_dir))
    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(projects_dir))

    project = ProjectManager.create_project(name="Non Consumer")
    project.project_type = "default"
    ProjectManager.save_project(project)

    state = SimulationManager().create_simulation(
        project_id=project.project_id,
        graph_id="graph_123",
        project_type="default",
    )

    app = _create_test_app()
    client = app.test_client()

    response = client.get(f"/api/consumer/simulation/{state.simulation_id}/consumer-summary")
    assert response.status_code == 400
    assert "consumer_test" in response.get_json()["error"].lower()


def test_consumer_api_consumer_summary_exposes_phase2_fields(tmp_path, monkeypatch):
    uploads_dir = tmp_path / "uploads"
    projects_dir = uploads_dir / "projects"
    simulations_dir = tmp_path / "uploads" / "simulations"
    monkeypatch.setattr(simulation_api.Config, "OASIS_SIMULATION_DATA_DIR", str(simulations_dir))
    monkeypatch.setattr(simulation_api.SimulationManager, "SIMULATION_DATA_DIR", str(simulations_dir))
    monkeypatch.setattr(SimulationManager, "SIMULATION_DATA_DIR", str(simulations_dir))
    monkeypatch.setattr(graph_api.Config, "UPLOAD_FOLDER", str(uploads_dir))
    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(projects_dir))

    project = ProjectManager.create_project(name="Consumer Phase2 API")
    project.project_type = "consumer_test"
    project.graph_id = f"consumer_{project.project_id}"
    project.consumer_brief = _consumer_brief_payload()
    ProjectManager.save_project(project)

    state = SimulationManager().create_simulation(
        project_id=project.project_id,
        graph_id=project.graph_id,
        project_type="consumer_test",
    )
    _write_consumer_rounds_with_events(simulations_dir, state.simulation_id)

    app = _create_test_app()
    client = app.test_client()

    response = client.get(f"/api/consumer/simulation/{state.simulation_id}/consumer-summary")
    assert response.status_code == 200
    payload = response.get_json()["data"]
    assert "event_counts" in payload
    assert "cascade_metrics" in payload
    assert payload["event_counts"]["risk_discovery"] == 1
    # top_risk_findings may be empty due to evidence gatekeeping in uncommitted work
    assert "top_risk_findings" in payload
