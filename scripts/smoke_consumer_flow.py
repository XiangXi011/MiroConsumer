"""Phase 7 production smoke helpers.

This script intentionally validates infrastructure readiness without running
external LLM calls. Optional Docker-backed smoke helpers can be enabled with
RUN_DOCKER_SMOKES=1.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

# ---------------------------------------------------------------------------
# Ensure backend is on sys.path so imports work when the script is executed
# from the repo root or imported by tests.
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
BACKEND_PATH = str(ROOT / "backend")
if BACKEND_PATH not in sys.path:
    sys.path.insert(0, BACKEND_PATH)

from app.services.application.infra_smokes import (  # noqa: E402
    run_postgres_explain_smoke,
    run_real_redis_lock_smoke,
)


def run_compose_config() -> dict:
    completed = subprocess.run(
        ["docker", "compose", "-f", "docker-compose.prod.yml", "config"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    return {
        "status": "passed" if completed.returncode == 0 else "failed",
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def _make_trace_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _reset_config_cache() -> None:
    """Reset all Config cached attributes to None so the next access reads from env."""
    from app.config import Config

    Config._db_url_cache = None
    Config._storage_backend_cache = None
    Config._queue_backend_cache = None


def _create_flask_app():
    from flask import Flask
    from app.api import consumer_bp, graph_bp, report_bp, simulation_bp

    app = Flask(__name__)
    app.config["TESTING"] = True
    if hasattr(app, "json") and hasattr(app.json, "ensure_ascii"):
        app.json.ensure_ascii = False
    app.register_blueprint(graph_bp, url_prefix="/api/graph")
    app.register_blueprint(simulation_bp, url_prefix="/api/simulation")
    app.register_blueprint(report_bp, url_prefix="/api/report")
    app.register_blueprint(consumer_bp, url_prefix="/api/consumer")
    return app


def run_smoke_checks() -> dict:
    from app.config import Config
    from app.repositories.factory import create_repository_bundle
    from app.repositories.sqlalchemy import metadata
    from app.services.application.concurrency import create_lock_manager
    from app.services.application.sqlite_queue import SQLiteQueueBackend
    from app.services.application.task_executor import ThreadTaskExecutor
    from app.services.storage import get_storage_backend
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    steps = []
    passed = 0
    failed = 0

    # ------------------------------------------------------------------
    # 1. filesystem_repository
    # ------------------------------------------------------------------
    original_db_url = Config._db_url_cache
    try:
        Config._db_url_cache = ""
        bundle = create_repository_bundle(Config)
        status = "passed" if bundle.backend == "filesystem" else "failed"
        steps.append({
            "name": "filesystem_repository",
            "status": status,
            "trace_id": _make_trace_id("fs_repo"),
            "repository_backend": bundle.backend,
            "task_status": "SUCCEEDED" if status == "passed" else "FAILED",
            "response_schema": {"backend": "filesystem"},
        })
        if status == "passed":
            passed += 1
        else:
            failed += 1
    except Exception as exc:
        steps.append({
            "name": "filesystem_repository",
            "status": "failed",
            "trace_id": _make_trace_id("fs_repo"),
            "repository_backend": "unknown",
            "task_status": "FAILED",
            "response_schema": {"error": str(exc)},
        })
        failed += 1
    finally:
        Config._db_url_cache = original_db_url

    # ------------------------------------------------------------------
    # 2. sqlite_repository
    # ------------------------------------------------------------------
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "smoke.db"
        db_url = f"sqlite:///{db_path}"
        original_db_url = Config._db_url_cache
        try:
            Config._db_url_cache = db_url
            bundle = create_repository_bundle(Config)
            status = "passed" if bundle.backend == "sqlalchemy" else "failed"
            steps.append({
                "name": "sqlite_repository",
                "status": status,
                "trace_id": _make_trace_id("sql_repo"),
                "repository_backend": bundle.backend,
                "task_status": "SUCCEEDED" if status == "passed" else "FAILED",
                "response_schema": {"backend": "sqlalchemy"},
            })
            if status == "passed":
                passed += 1
            else:
                failed += 1
        except Exception as exc:
            steps.append({
                "name": "sqlite_repository",
                "status": "failed",
                "trace_id": _make_trace_id("sql_repo"),
                "repository_backend": "unknown",
                "task_status": "FAILED",
                "response_schema": {"error": str(exc)},
            })
            failed += 1
        finally:
            Config._db_url_cache = original_db_url

    # ------------------------------------------------------------------
    # 3. thread_queue
    # ------------------------------------------------------------------
    try:
        executor = ThreadTaskExecutor()
        trace_id = executor.submit(lambda: None, trace_id="trace_thread_smoke")
        status_info = executor.get_status(trace_id)
        status = "passed" if status_info.get("backend") == "thread" else "failed"
        steps.append({
            "name": "thread_queue",
            "status": status,
            "trace_id": trace_id,
            "repository_backend": "thread",
            "task_status": status_info.get("status", "UNKNOWN"),
            "response_schema": {
                "trace_id": "str",
                "backend": "thread",
                "status": "PENDING|RUNNING|SUCCEEDED",
            },
        })
        if status == "passed":
            passed += 1
        else:
            failed += 1
    except Exception as exc:
        steps.append({
            "name": "thread_queue",
            "status": "failed",
            "trace_id": _make_trace_id("thread"),
            "repository_backend": "thread",
            "task_status": "FAILED",
            "response_schema": {"error": str(exc)},
        })
        failed += 1

    # ------------------------------------------------------------------
    # 4. sqlite_queue
    # ------------------------------------------------------------------
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "queue_smoke.db"
        db_url = f"sqlite:///{db_path}"
        original_db_url = Config._db_url_cache
        engine = None
        try:
            Config._db_url_cache = db_url
            engine = create_engine(db_url)
            metadata.create_all(engine)
            session_factory = sessionmaker(bind=engine)
            queue_backend = SQLiteQueueBackend(session_factory=session_factory)
            trace_id, _created = queue_backend.enqueue(
                "trace_sqlite_smoke",
                lambda: None,
                task_type="smoke",
                simulation_id="sim_smoke",
                run_id="base",
            )
            queue_backend.mark_running(trace_id)
            queue_backend.mark_succeeded(trace_id)
            status_info = queue_backend.get_status(trace_id)
            status = "passed" if status_info.get("backend") == "sqlite" else "failed"
            steps.append({
                "name": "sqlite_queue",
                "status": status,
                "trace_id": trace_id,
                "repository_backend": "sqlite",
                "task_status": status_info.get("status", "UNKNOWN"),
                "response_schema": {
                    "trace_id": "str",
                    "backend": "sqlite",
                    "status": "PENDING|RUNNING|SUCCEEDED",
                },
            })
            if status == "passed":
                passed += 1
            else:
                failed += 1
        except Exception as exc:
            steps.append({
                "name": "sqlite_queue",
                "status": "failed",
                "trace_id": _make_trace_id("sqlite"),
                "repository_backend": "sqlite",
                "task_status": "FAILED",
                "response_schema": {"error": str(exc)},
            })
            failed += 1
        finally:
            if engine is not None:
                engine.dispose()
            Config._db_url_cache = original_db_url

    # ------------------------------------------------------------------
    # 5. lock_service
    # ------------------------------------------------------------------
    original_db_url = Config._db_url_cache
    try:
        Config._db_url_cache = ""
        lock_manager = create_lock_manager(Config)
        with lock_manager.acquire("simulation_run_lock", "sim_smoke", timeout_seconds=0):
            pass
        steps.append({
            "name": "lock_service",
            "status": "passed",
            "trace_id": _make_trace_id("lock"),
            "repository_backend": "file",
            "task_status": "SUCCEEDED",
            "response_schema": {"lock_type": "simulation_run_lock", "resource_id": "sim_smoke", "acquired": True},
        })
        passed += 1
    except Exception as exc:
        steps.append({
            "name": "lock_service",
            "status": "failed",
            "trace_id": _make_trace_id("lock"),
            "repository_backend": "file",
            "task_status": "FAILED",
            "response_schema": {"error": str(exc)},
        })
        failed += 1
    finally:
        Config._db_url_cache = original_db_url

    # ------------------------------------------------------------------
    # 6. run_estimate_api
    # ------------------------------------------------------------------
    try:
        client = _create_flask_app().test_client()
        response = client.post(
            "/api/consumer/simulations/sim_smoke/run-estimate",
            json={"society_max_agents": 20, "max_rounds": 2},
        )
        data = response.get_json() or {}
        estimate = data.get("data") if isinstance(data, dict) else {}
        required_keys = {
            "agents_count",
            "rounds_count",
            "estimated_llm_calls",
            "cost_level",
            "estimated_duration_seconds",
        }
        status = (
            "passed"
            if response.status_code == 200
            and isinstance(estimate, dict)
            and required_keys <= set(estimate)
            else "failed"
        )
        steps.append({
            "name": "run_estimate_api",
            "status": status,
            "trace_id": _make_trace_id("estimate"),
            "repository_backend": "api",
            "task_status": "SUCCEEDED" if status == "passed" else "FAILED",
            "response_schema": {
                "required": sorted(required_keys),
                "observed": sorted(estimate) if isinstance(estimate, dict) else [],
            },
        })
        if status == "passed":
            passed += 1
        else:
            failed += 1
    except Exception as exc:
        steps.append({
            "name": "run_estimate_api",
            "status": "failed",
            "trace_id": _make_trace_id("estimate"),
            "repository_backend": "api",
            "task_status": "FAILED",
            "response_schema": {"error": str(exc)},
        })
        failed += 1

    # ------------------------------------------------------------------
    # 7. audit_chain_api
    # ------------------------------------------------------------------
    try:
        from app.services.application import audit_chain_service as audit_module
        from app.services.report_agent import Report, ReportStatus

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

        original_create_bundle = audit_module.create_repository_bundle
        audit_module.create_repository_bundle = lambda: type(
            "Bundle", (), {"report_repo": StubRepo()}
        )()

        try:
            client = _create_flask_app().test_client()
            response = client.get("/api/consumer/reports/report_smoke/audit-chain")
            data = response.get_json() or {}
            audit = data.get("data") if isinstance(data, dict) else {}
            chain = audit.get("chain") if isinstance(audit, dict) else []
            status = (
                "passed"
                if response.status_code == 200
                and isinstance(chain, list)
                and chain
                and chain[-1].get("resource_id") == "trace_smoke"
                else "failed"
            )
            steps.append({
                "name": "audit_chain_api",
                "status": status,
                "trace_id": _make_trace_id("audit"),
                "repository_backend": "api",
                "task_status": "SUCCEEDED" if status == "passed" else "FAILED",
                "response_schema": {
                    "report_id": "str",
                    "complete": "bool",
                    "chain": "list",
                    "terminal_resource_id": "trace_smoke",
                },
            })
            if status == "passed":
                passed += 1
            else:
                failed += 1
        finally:
            audit_module.create_repository_bundle = original_create_bundle
    except Exception as exc:
        steps.append({
            "name": "audit_chain_api",
            "status": "failed",
            "trace_id": _make_trace_id("audit"),
            "repository_backend": "api",
            "task_status": "FAILED",
            "response_schema": {"error": str(exc)},
        })
        failed += 1

    # ------------------------------------------------------------------
    # 8. local_storage
    # ------------------------------------------------------------------
    original_storage = Config._storage_backend_cache
    try:
        Config._storage_backend_cache = "local"
        storage = get_storage_backend(Config)
        status = "passed" if storage.backend == "local" else "failed"
        steps.append({
            "name": "local_storage",
            "status": status,
            "trace_id": _make_trace_id("storage"),
            "repository_backend": storage.backend,
            "task_status": "SUCCEEDED" if status == "passed" else "FAILED",
            "response_schema": {"backend": "local", "local_paths": "dict"},
        })
        if status == "passed":
            passed += 1
        else:
            failed += 1
    except Exception as exc:
        steps.append({
            "name": "local_storage",
            "status": "failed",
            "trace_id": _make_trace_id("storage"),
            "repository_backend": "unknown",
            "task_status": "FAILED",
            "response_schema": {"error": str(exc)},
        })
        failed += 1
    finally:
        Config._storage_backend_cache = original_storage

    # ------------------------------------------------------------------
    # 9. production_compose_config
    # ------------------------------------------------------------------
    try:
        compose_result = run_compose_config()
        status = "passed" if compose_result["status"] == "passed" else "failed"
        steps.append({
            "name": "production_compose_config",
            "status": status,
            "trace_id": _make_trace_id("compose"),
            "repository_backend": "docker",
            "task_status": "SUCCEEDED" if status == "passed" else "FAILED",
            "response_schema": {"status": "passed|failed", "returncode": "int"},
        })
        if status == "passed":
            passed += 1
        else:
            failed += 1
    except Exception as exc:
        steps.append({
            "name": "production_compose_config",
            "status": "failed",
            "trace_id": _make_trace_id("compose"),
            "repository_backend": "docker",
            "task_status": "FAILED",
            "response_schema": {"error": str(exc)},
        })
        failed += 1

    if os.environ.get("RUN_DOCKER_SMOKES") == "1":
        for smoke_name, smoke_runner in [
            ("real_redis_lock_contention", run_real_redis_lock_smoke),
            ("postgres_jsonb_gin_explain", run_postgres_explain_smoke),
        ]:
            try:
                smoke_result = smoke_runner()
                step = smoke_result["steps"][0]
                steps.append(step)
                if step["status"] == "passed":
                    passed += 1
                else:
                    failed += 1
            except Exception as exc:
                steps.append({
                    "name": smoke_name,
                    "status": "failed",
                    "trace_id": _make_trace_id(smoke_name),
                    "repository_backend": "docker",
                    "task_status": "FAILED",
                    "response_schema": {"error": str(exc)},
                })
                failed += 1

    return {
        "steps": steps,
        "summary": {
            "total": len(steps),
            "passed": passed,
            "failed": failed,
            "status": "passed" if failed == 0 else "failed",
        },
    }


def main() -> None:
    print(json.dumps(run_smoke_checks(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
