import json
from pathlib import Path

from flask import Flask

from app.api import consumer_bp, graph_bp, report_bp, simulation_bp
from app.api import graph as graph_api
from app.api import report as report_api
from app.api import simulation as simulation_api
from app.models.project import ProjectManager, ProjectStatus
from app.models.task import TaskManager
from app.services.consumer.society.consumer_roles import ConsumerRole
from app.services.consumer.society.population_models import ConsumerSocietyAgent, ConsumerSocietySnapshot
from app.services.consumer.society.state_store import SocietyStateStore
from app.services.report_agent import ReportManager
from app.services.simulation_manager import SimulationManager, SimulationStatus


class _ImmediateThread:
    def __init__(self, target=None, daemon=None):
        self._target = target
        self.daemon = daemon

    def start(self):
        self._target()


def _create_test_app():
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(graph_bp, url_prefix="/api/graph")
    app.register_blueprint(simulation_bp, url_prefix="/api/simulation")
    app.register_blueprint(report_bp, url_prefix="/api/report")
    app.register_blueprint(consumer_bp, url_prefix="/api/consumer")
    return app


def _configure_storage(tmp_path, monkeypatch):
    uploads_dir = tmp_path / "uploads"
    projects_dir = uploads_dir / "projects"
    simulations_dir = uploads_dir / "simulations"
    reports_dir = uploads_dir / "reports"
    monkeypatch.setattr(graph_api.Config, "UPLOAD_FOLDER", str(uploads_dir))
    monkeypatch.setattr(report_api.Config, "UPLOAD_FOLDER", str(uploads_dir))
    monkeypatch.setattr(simulation_api.Config, "UPLOAD_FOLDER", str(uploads_dir))
    monkeypatch.setattr(simulation_api.Config, "OASIS_SIMULATION_DATA_DIR", str(simulations_dir))
    monkeypatch.setattr(SimulationManager, "SIMULATION_DATA_DIR", str(simulations_dir))
    monkeypatch.setattr(simulation_api.SimulationManager, "SIMULATION_DATA_DIR", str(simulations_dir))
    monkeypatch.setattr(ProjectManager, "PROJECTS_DIR", str(projects_dir))
    monkeypatch.setattr(ReportManager, "REPORTS_DIR", str(reports_dir))
    monkeypatch.setattr(report_api.ReportManager, "REPORTS_DIR", str(reports_dir))
    TaskManager()._tasks.clear()
    return uploads_dir, simulations_dir


def _business_brief():
    return {
        "task_type": "concept_test",
        "product_concept_assets": ["low sugar yogurt pouch"],
        "copy_material": ["breakfast protein without the sugar crash"],
        "claims": ["low sugar", "10g protein"],
        "target_audience": ["busy students"],
        "usage_scene": ["morning commute"],
        "research_goal": "Find spread, misunderstanding, and trust repair path.",
        "optional_background_materials": [
            "Uploaded QA says the sweetener source is documented by supplier testing."
        ],
    }


def _write_rounds(simulations_dir: Path, simulation_id: str):
    simulation_dir = simulations_dir / simulation_id
    simulation_dir.mkdir(parents=True, exist_ok=True)
    events = [
        {
            "round_num": 0,
            "agent_id": "agent-skeptic",
            "agent_name": "Proof First",
            "attitude_label": "neutral",
            "bucket": "question",
            "engagement": 6,
            "quote": "I need proof before I trust the low sugar claim.",
            "visible_nodes": [{"type": "CopyPoint", "text": "low sugar"}],
            "propagation_events": [],
        },
        {
            "round_num": 1,
            "agent_id": "agent-skeptic",
            "agent_name": "Proof First",
            "attitude_label": "negative",
            "bucket": "risk",
            "engagement": 9,
            "quote": "The sweetener proof is the blocker for me.",
            "visible_nodes": [{"type": "RiskPoint", "text": "sweetener proof gap"}],
            "propagation_events": [
                {
                    "event_id": "evt-proof-gap",
                    "event_type": "risk_discovery",
                    "actor_id": "agent-skeptic",
                    "target_ids": ["agent-advocate"],
                    "trigger_finding_ids": ["finding-supported", "finding-weak"],
                    "supporting_quote": "The sweetener proof is the blocker for me.",
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
                "consumer_brief": _business_brief(),
                "research_findings": [
                    {
                        "finding_id": "finding-supported",
                        "finding_type": "risk_signal",
                        "summary": "Sweetener proof gap blocks trust.",
                        "evidence_snippets": ["supplier testing documents sweetener source", "QA confirms low sugar test"],
                        "snippet_id": "chunk-supported",
                        "retrieval_trace_id": "trace-supported",
                        "source_id": "source-upload",
                        "source_label": "ingested_document",
                        "confidence": 0.82,
                    },
                    {
                        "finding_id": "finding-weak",
                        "finding_type": "trend_signal",
                        "summary": "Students resist 29.9 price without value proof.",
                        "evidence_snippets": ["one public review questions value"],
                        "snippet_id": "chunk-weak",
                        "source_id": "source-web",
                        "source_label": "public_web",
                        "confidence": 0.42,
                    },
                ],
                "retrieval_traces": [
                    {
                        "trace_id": "trace-supported",
                        "query": "sweetener proof",
                        "lane": "lane_a",
                        "chunk_ids": ["chunk-supported"],
                        "scores": [0.91],
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def _write_society(simulations_dir: Path, simulation_id: str):
    store = SocietyStateStore(base_dir=simulations_dir)
    store.write_population(
        simulation_id,
        [
            ConsumerSocietyAgent(
                agent_id="agent-skeptic",
                parent_persona_id="persona-1",
                layer="core",
                segment="proof-first students",
                role=ConsumerRole.Skeptic,
                channel_affinity={"zhihu_qa": 0.9},
                state={"attitude_start": "neutral", "attitude_latest": "skeptical"},
            ),
            ConsumerSocietyAgent(
                agent_id="agent-advocate",
                parent_persona_id="persona-2",
                layer="core",
                segment="busy commuters",
                role=ConsumerRole.Advocate,
                channel_affinity={"xiaohongshu": 0.8},
                state={"attitude_start": "neutral", "attitude_latest": "positive"},
            ),
        ],
    )
    store.write_rounds(
        simulation_id,
        [
            ConsumerSocietySnapshot(
                simulation_id=simulation_id,
                run_id="run-1",
                round_index=0,
                agents_count=2,
                events=[
                    {
                        "event_id": "event-skeptic",
                        "agent_id": "agent-skeptic",
                        "consumer_event_type": "ASK_PROOF",
                        "quote": "Show me supplier proof before I believe this.",
                        "finding_ids": ["finding-supported"],
                    }
                ],
            )
        ],
    )
    store.write_channel_metrics(simulation_id, {"channels": {"zhihu_qa": {"fit_score": 0.61}}})
    store.write_channel_events(
        simulation_id,
        [{"event_id": "channel-1", "actor_id": "agent-skeptic", "channel_id": "zhihu_qa"}],
    )


def test_consumer_concept_test_golden_flow_is_structurally_complete(tmp_path, monkeypatch):
    uploads_dir, simulations_dir = _configure_storage(tmp_path, monkeypatch)
    monkeypatch.setattr("threading.Thread", _ImmediateThread)

    project = ProjectManager.create_project(name="Golden Concept")
    project.project_type = "consumer_test"
    project.status = ProjectStatus.GRAPH_COMPLETED
    project.graph_id = f"consumer_{project.project_id}"
    project.consumer_brief = _business_brief()
    project.simulation_requirement = "Run consumer concept propagation test"
    ProjectManager.save_project(project)
    ProjectManager.save_extracted_text(project.project_id, "supplier testing documents sweetener source")

    captured_start = {}

    class _RunState:
        def to_dict(self):
            return {"simulation_id": captured_start["simulation_id"], "runner_status": "running"}

    def fake_start_simulation(**kwargs):
        captured_start.update(kwargs)
        return _RunState()

    monkeypatch.setattr(
        "app.services.application.simulation_app_service.SimulationRunner.start_simulation",
        fake_start_simulation,
    )

    app = _create_test_app()
    client = app.test_client()

    create_resp = client.post("/api/simulation/create", json={"project_id": project.project_id})
    assert create_resp.status_code == 200
    simulation_id = create_resp.get_json()["data"]["simulation_id"]

    prepare_resp = client.post("/api/simulation/prepare", json={"simulation_id": simulation_id})
    assert prepare_resp.status_code == 200
    prepare_data = prepare_resp.get_json()["data"]
    assert prepare_data["already_prepared"] is False
    prepared_state = SimulationManager().get_simulation(simulation_id)
    assert prepared_state.project_type == "consumer_test"
    assert prepared_state.consumer_mode is True

    start_resp = client.post(
        "/api/simulation/start",
        json={
            "simulation_id": simulation_id,
            "society_mode": "standard",
            "society_seed": 42,
            "society_max_agents": 240,
            "society_audit_sample_size": 8,
            "max_rounds": 2,
        },
    )
    assert start_resp.status_code == 200
    assert captured_start["society_config"]["mode"] == "standard"
    assert captured_start["society_config"]["random_seed"] == 42
    assert captured_start["society_config"]["max_agents"] == 240

    state = SimulationManager().get_simulation(simulation_id)
    state.status = SimulationStatus.COMPLETED
    SimulationManager().save_simulation(state)
    _write_rounds(simulations_dir, simulation_id)
    _write_society(simulations_dir, simulation_id)

    summary_resp = client.get(f"/api/consumer/simulation/{simulation_id}/consumer-summary")
    assert summary_resp.status_code == 200
    summary = summary_resp.get_json()["data"]
    assert summary["event_counts"]["risk_discovery"] == 1
    assert summary["causal_voc_quotes"][0]["event_id"] == "evt-proof-gap"
    assert summary["report_confidence"]["confidence_label"] in {"high", "medium", "low", "unknown"}

    report_resp = client.post(
        "/api/report/generate",
        json={"simulation_id": simulation_id, "force_regenerate": True},
    )
    assert report_resp.status_code == 200
    report_id = report_resp.get_json()["data"]["report_id"]
    report_status = client.post(
        "/api/report/generate/status",
        json={"simulation_id": simulation_id, "task_id": report_resp.get_json()["data"]["task_id"]},
    )
    assert report_status.status_code == 200
    report_payload = client.get(f"/api/report/{report_id}").get_json()["data"]
    report_context = report_payload["report_context"]
    assert report_context["evidence_gatekeeping_summary"]["allowed_count"] >= 1
    assert all(
        finding.get("source_id") or finding.get("support_level") in {"weak_support", "insufficient_support"}
        for finding in report_context.get("top_risk_findings", [])
    )

    target_finding = report_context["top_risk_findings"][0]
    focus_resp = client.post(
        f"/api/consumer/simulations/{simulation_id}/focus-groups",
        json={
            "topic": "sweetener proof repair",
            "moderator_goal": "Turn the report finding into a concrete revision",
            "roles": ["skeptic", "advocate"],
            "target_context": {
                "task_type": "concept_test",
                "finding_id": target_finding["finding_id"],
                "claim": target_finding["summary"],
                "evidence_map": {
                    target_finding["finding_id"]: {
                        "support_level": "supported",
                        "source_count": 1,
                    }
                },
            },
        },
    )
    assert focus_resp.status_code == 200
    focus = focus_resp.get_json()["data"]
    assert len(focus["turns"]) == 4
    assert focus["consensus"]
    assert focus["disagreements"]
    assert focus["evidence_map"]

    modification_advice = {
        "finding_id": target_finding["finding_id"],
        "advice": focus["next_what_if_experiments"][0],
        "evidence_backed": bool(focus["evidence_map"]),
    }
    assert modification_advice["evidence_backed"] is True
    assert target_finding["finding_id"] in modification_advice["advice"]
