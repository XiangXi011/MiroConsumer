"""Phase 7 production smoke tests."""

import json
import os
import subprocess
from pathlib import Path

import pytest
from flask import Flask
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api import consumer_bp, graph_bp, report_bp, simulation_bp
from app.config import Config
from app.repositories.factory import create_repository_bundle
from app.repositories.sqlalchemy import metadata
from app.services.application.concurrency import create_lock_manager
from app.services.application.queue_task_executor import QueueTaskExecutor
from app.services.application.sqlite_queue import SQLiteQueueBackend
from app.services.application.task_executor import ThreadTaskExecutor
from app.services.report_agent import Report, ReportStatus


ROOT = Path(__file__).resolve().parents[3]


def _docker_daemon_ready():
    try:
        completed = subprocess.run(
            ["docker", "info"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
            timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return completed.returncode == 0


def _create_app():
    app = Flask(__name__)
    app.config["TESTING"] = True
    if hasattr(app, "json") and hasattr(app.json, "ensure_ascii"):
        app.json.ensure_ascii = False
    app.register_blueprint(graph_bp, url_prefix="/api/graph")
    app.register_blueprint(simulation_bp, url_prefix="/api/simulation")
    app.register_blueprint(report_bp, url_prefix="/api/report")
    app.register_blueprint(consumer_bp, url_prefix="/api/consumer")
    return app


def test_phase6j_entry_report_allows_phase7():
    report = json.loads(
        (ROOT / "docs/superpowers/reports/phase6j_calibration_report.json").read_text(
            encoding="utf-8"
        )
    )

    assert report["phase7_entry_decision"] == "PASS"
    assert report["details"]["end_to_end_golden_flow"] == "PASS"
    assert report["details"]["evidence_gatekeeping_hard_rules"] == "PASS"
    assert report["details"]["explainability_panel_acceptance"] == "PASS"


def test_repository_and_queue_startup_modes(tmp_path, monkeypatch):
    monkeypatch.setattr(Config, "_db_url_cache", "")
    fs_bundle = create_repository_bundle(Config)
    assert fs_bundle.backend == "filesystem"

    db_path = tmp_path / "phase7.db"
    db_url = f"sqlite:///{db_path}"
    monkeypatch.setattr(Config, "_db_url_cache", db_url)
    sql_bundle = create_repository_bundle(Config)
    assert sql_bundle.backend == "sqlalchemy"

    trace_id = ThreadTaskExecutor().submit(lambda: None, trace_id="trace_thread")
    thread_status = ThreadTaskExecutor().get_status("missing")
    assert trace_id == "trace_thread"
    assert thread_status["trace_id"] == "missing"
    assert thread_status["backend"] == "thread"

    engine = create_engine(db_url)
    metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    sqlite_executor = QueueTaskExecutor(
        backend_name="sqlite",
        backend=SQLiteQueueBackend(session_factory=session_factory),
    )
    queued_trace = sqlite_executor.submit(
        lambda: None,
        trace_id="trace_sqlite",
        task_type="smoke",
        simulation_id="sim_smoke",
        run_id="base",
    )
    queued_status = sqlite_executor.get_status(queued_trace)
    assert queued_status["trace_id"] == "trace_sqlite"
    assert queued_status["backend"] == "sqlite"
    assert queued_status["status"] in {"PENDING", "RUNNING", "SUCCEEDED"}


def test_lock_run_estimate_audit_and_storage_smoke(monkeypatch):
    from app.services.application import audit_chain_service as audit_module
    from app.services.storage import get_storage_backend

    monkeypatch.setattr(Config, "_db_url_cache", "")
    lock_manager = create_lock_manager(Config)
    with lock_manager.acquire("simulation_run_lock", "sim_smoke", timeout_seconds=0):
        pass

    response = _create_app().test_client().post(
        "/api/consumer/simulations/sim_smoke/run-estimate",
        json={"society_max_agents": 20, "max_rounds": 2},
    )
    assert response.status_code == 200
    estimate = response.get_json()["data"]
    assert set(estimate) >= {
        "agents_count",
        "rounds_count",
        "estimated_llm_calls",
        "cost_level",
        "estimated_duration_seconds",
    }

    report = Report(
        report_id="report_smoke",
        simulation_id="sim_smoke",
        graph_id="g1",
        simulation_requirement="req",
        status=ReportStatus.COMPLETED,
    )
    report.audit_chain = {
        "finding_id": "finding_smoke",
        "source_id": "source_smoke",
        "round_snapshot_id": "round_smoke",
        "event_id": "event_smoke",
        "agent_id": "agent_smoke",
        "channel_id": "channel_smoke",
        "task_id": "task_smoke",
        "trace_id": "trace_smoke",
    }

    class StubRepo:
        def get_report(self, report_id):
            return report

    monkeypatch.setattr(
        audit_module,
        "create_repository_bundle",
        lambda: type("Bundle", (), {"report_repo": StubRepo()})(),
    )
    audit_response = _create_app().test_client().get(
        "/api/consumer/reports/report_smoke/audit-chain"
    )
    assert audit_response.status_code == 200
    audit = audit_response.get_json()["data"]
    assert audit["chain"][-1]["resource_id"] == "trace_smoke"

    monkeypatch.setattr(Config, "_storage_backend_cache", "local")
    storage = get_storage_backend(Config)
    assert storage.backend == "local"


def test_production_compose_config_parses():
    completed = subprocess.run(
        ["docker", "compose", "-f", "docker-compose.prod.yml", "config"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr


def test_smoke_consumer_flow_run_smoke_checks():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "smoke_consumer_flow", ROOT / "scripts/smoke_consumer_flow.py"
    )
    scf = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(scf)

    result = scf.run_smoke_checks()
    assert isinstance(result, dict)
    assert "steps" in result
    assert "summary" in result

    required_step_names = {
        "filesystem_repository",
        "sqlite_repository",
        "thread_queue",
        "sqlite_queue",
        "lock_service",
        "run_estimate_api",
        "audit_chain_api",
        "local_storage",
        "production_compose_config",
    }

    step_names = {step["name"] for step in result["steps"]}
    assert required_step_names <= step_names

    for step in result["steps"]:
        assert "status" in step
        assert "trace_id" in step
        assert "repository_backend" in step
        assert "task_status" in step
        assert "response_schema" in step


@pytest.mark.skipif(
    os.environ.get("RUN_DOCKER_SMOKES") != "1" or not _docker_daemon_ready(),
    reason="Set RUN_DOCKER_SMOKES=1 and start Docker daemon to run real Redis smoke.",
)
def test_real_redis_lock_contention_smoke():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "smoke_consumer_flow", ROOT / "scripts/smoke_consumer_flow.py"
    )
    scf = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(scf)

    result = scf.run_real_redis_lock_smoke()

    assert result["summary"]["status"] == "passed"
    assert result["steps"][0]["name"] == "real_redis_lock_contention"
    assert result["steps"][0]["response_schema"]["contention_reason"] == "lock_timeout"


@pytest.mark.skipif(
    os.environ.get("RUN_DOCKER_SMOKES") != "1" or not _docker_daemon_ready(),
    reason="Set RUN_DOCKER_SMOKES=1 and start Docker daemon to run real PostgreSQL EXPLAIN smoke.",
)
def test_postgres_jsonb_gin_explain_smoke():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "smoke_consumer_flow", ROOT / "scripts/smoke_consumer_flow.py"
    )
    scf = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(scf)

    result = scf.run_postgres_explain_smoke()

    assert result["summary"]["status"] == "passed"
    assert result["steps"][0]["name"] == "postgres_jsonb_gin_explain"
    assert result["steps"][0]["response_schema"]["index_name"] == "ix_projects_data_gin"
    assert "ix_projects_data_gin" in result["steps"][0]["response_schema"]["plan"]
