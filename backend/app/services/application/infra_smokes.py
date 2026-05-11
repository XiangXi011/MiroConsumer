"""Docker-backed infrastructure smoke helpers for Phase 7."""

from __future__ import annotations

import importlib.util
import json
import socket
import subprocess
import sys
import tempfile
import textwrap
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable

import redis
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import Column, DateTime, Integer, MetaData, String, Table, create_engine, insert, text
from sqlalchemy.dialects.postgresql import JSONB

ROOT = Path(__file__).resolve().parents[4]
MIGRATION_PATH = ROOT / "alembic" / "versions" / "20260508_0003_add_performance_indexes.py"


def _make_trace_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _reserve_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _docker_available() -> None:
    completed = subprocess.run(
        ["docker", "version"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "Docker is required for the real infra smoke tests. "
            f"stderr={completed.stderr.strip()}"
        )


def _docker_run_container(
    image: str,
    name: str,
    *,
    env: Dict[str, str] | None = None,
    ports: Iterable[tuple[int, int]] = (),
    command: list[str] | None = None,
) -> None:
    args = ["docker", "run", "-d", "--name", name]
    for key, value in (env or {}).items():
        args.extend(["-e", f"{key}={value}"])
    for host_port, container_port in ports:
        args.extend(["-p", f"127.0.0.1:{host_port}:{container_port}"])
    args.append(image)
    if command:
        args.extend(command)
    completed = subprocess.run(
        args,
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"Failed to start Docker container {name}: {completed.stderr.strip()}"
        )


def _docker_remove_container(name: str) -> None:
    subprocess.run(
        ["docker", "rm", "-f", name],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def _wait_for_file(path: Path, timeout_seconds: float = 30.0) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if path.exists():
            return
        time.sleep(0.05)
    raise TimeoutError(f"Timed out waiting for file: {path}")


def _wait_for_redis(redis_url: str, timeout_seconds: float = 60.0) -> None:
    client = redis.Redis.from_url(redis_url)
    deadline = time.monotonic() + timeout_seconds
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            client.ping()
            return
        except redis.exceptions.RedisError as exc:
            last_error = exc
            time.sleep(0.2)
    raise RuntimeError(f"Redis did not become ready: {last_error!r}")


def _wait_for_postgres(db_url: str, timeout_seconds: float = 90.0) -> None:
    engine = create_engine(db_url, pool_pre_ping=True)
    deadline = time.monotonic() + timeout_seconds
    last_error: Exception | None = None
    try:
        while time.monotonic() < deadline:
            try:
                with engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                return
            except Exception as exc:  # pragma: no cover - ready loop only
                last_error = exc
                time.sleep(0.5)
    finally:
        engine.dispose()
    raise RuntimeError(f"PostgreSQL did not become ready: {last_error!r}")


def _load_migration_module():
    spec = importlib.util.spec_from_file_location(
        "migration_20260508_0003",
        MIGRATION_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _create_performance_tables(connection) -> Dict[str, Table]:
    metadata = MetaData()
    tables = {
        "projects": Table(
            "projects",
            metadata,
            Column("id", String(36), primary_key=True),
            Column("created_at", DateTime()),
            Column("project_type", String(50)),
            Column("data", JSONB, nullable=False),
        ),
        "simulations": Table(
            "simulations",
            metadata,
            Column("id", String(36), primary_key=True),
            Column("project_id", String(36)),
            Column("status", String(50)),
            Column("created_at", DateTime()),
            Column("data", JSONB, nullable=False),
        ),
        "simulation_runs": Table(
            "simulation_runs",
            metadata,
            Column("id", String(36), primary_key=True),
            Column("simulation_id", String(36)),
            Column("run_id", String(36)),
        ),
        "branches": Table(
            "branches",
            metadata,
            Column("id", String(36), primary_key=True),
            Column("simulation_id", String(36)),
            Column("status", String(50)),
            Column("created_at", DateTime()),
        ),
        "reports": Table(
            "reports",
            metadata,
            Column("id", String(36), primary_key=True),
            Column("simulation_id", String(36)),
            Column("status", String(50)),
            Column("created_at", DateTime()),
            Column("data", JSONB, nullable=False),
        ),
        "tasks": Table(
            "tasks",
            metadata,
            Column("id", String(36), primary_key=True),
            Column("simulation_id", String(36)),
            Column("status", String(50)),
            Column("updated_at", DateTime()),
            Column("data", JSONB, nullable=False),
            Column("payload", JSONB, nullable=False),
        ),
        "task_attempts": Table(
            "task_attempts",
            metadata,
            Column("id", String(36), primary_key=True),
            Column("task_id", String(36)),
            Column("attempt_number", Integer()),
        ),
        "consumer_events": Table(
            "consumer_events",
            metadata,
            Column("id", String(36), primary_key=True),
            Column("payload", JSONB, nullable=False),
        ),
        "research_assets": Table(
            "research_assets",
            metadata,
            Column("id", String(36), primary_key=True),
            Column("payload", JSONB, nullable=False),
        ),
    }
    metadata.create_all(connection)
    return tables


def _write_redis_lock_worker_script(tmpdir: Path) -> Path:
    worker_code = textwrap.dedent(
        """
        import json
        import sys
        import time
        from pathlib import Path

        redis_url = sys.argv[1]
        ready_path = Path(sys.argv[2])
        release_path = Path(sys.argv[3])
        backend_path = sys.argv[4]

        if backend_path not in sys.path:
            sys.path.insert(0, backend_path)

        from app.services.application.concurrency import RedisLockManager, branch_fork_lock

        mgr = RedisLockManager(redis_url, namespace="smoke")
        with mgr.acquire(branch_fork_lock, "branch_smoke", timeout_seconds=5):
            ready_path.write_text(
                json.dumps(
                    {
                        "status": "held",
                        "lock_type": branch_fork_lock,
                        "resource_id": "branch_smoke",
                    }
                ),
                encoding="utf-8",
            )
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline and not release_path.exists():
                time.sleep(0.05)
        """
    ).strip()
    worker_path = tmpdir / "redis_lock_worker.py"
    worker_path.write_text(worker_code, encoding="utf-8")
    return worker_path


def run_real_redis_lock_smoke() -> Dict[str, Any]:
    """Run a real Redis-backed lock contention smoke test."""

    _docker_available()

    container_name = f"miroconsumer-redis-smoke-{uuid.uuid4().hex[:8]}"
    host_port = _reserve_port()
    redis_url = f"redis://127.0.0.1:{host_port}/0"
    step = {
        "name": "real_redis_lock_contention",
        "status": "failed",
        "trace_id": _make_trace_id("redis_smoke"),
        "repository_backend": "redis",
        "task_status": "FAILED",
        "response_schema": {},
    }

    try:
        _docker_run_container(
            "redis:7-alpine",
            container_name,
            ports=[(host_port, 6379)],
            command=["redis-server", "--appendonly", "yes"],
        )
        _wait_for_redis(redis_url)

        from app.contracts.errors import ConcurrencyConflictError
        from app.services.application.concurrency import RedisLockManager, branch_fork_lock

        with tempfile.TemporaryDirectory() as tmpdir_name:
            tmpdir = Path(tmpdir_name)
            ready_path = tmpdir / "ready.json"
            release_path = tmpdir / "release.signal"
            worker_path = _write_redis_lock_worker_script(tmpdir)
            worker_proc = subprocess.Popen(
                [
                    sys.executable,
                    str(worker_path),
                    redis_url,
                    str(ready_path),
                    str(release_path),
                    str(ROOT / "backend"),
                ],
                cwd=ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            try:
                _wait_for_file(ready_path, timeout_seconds=30)
                ready_payload = json.loads(ready_path.read_text(encoding="utf-8"))

                contention_reason = "unexpected_success"
                mgr = RedisLockManager(redis_url, namespace="smoke")
                try:
                    with mgr.acquire(branch_fork_lock, "branch_smoke", timeout_seconds=0):
                        pass
                except ConcurrencyConflictError as exc:
                    contention_reason = exc.to_response()["reason"]

                release_path.write_text("release", encoding="utf-8")
                stdout, stderr = worker_proc.communicate(timeout=30)
                if worker_proc.returncode != 0:
                    raise RuntimeError(
                        "Redis smoke worker failed: "
                        f"stdout={stdout.strip()} stderr={stderr.strip()}"
                    )

                passed = ready_payload.get("status") == "held" and contention_reason == "lock_timeout"
                step["status"] = "passed" if passed else "failed"
                step["task_status"] = "SUCCEEDED" if passed else "FAILED"
                step["response_schema"] = {
                    "redis_url": redis_url,
                    "lock_type": ready_payload.get("lock_type", branch_fork_lock),
                    "resource_id": ready_payload.get("resource_id", "branch_smoke"),
                    "holder_status": ready_payload.get("status"),
                    "contention_reason": contention_reason,
                }
            finally:
                if worker_proc.poll() is None:
                    worker_proc.kill()
                    worker_proc.wait(timeout=10)
    finally:
        _docker_remove_container(container_name)

    return {
        "steps": [step],
        "summary": {
            "total": 1,
            "passed": 1 if step["status"] == "passed" else 0,
            "failed": 0 if step["status"] == "passed" else 1,
            "status": "passed" if step["status"] == "passed" else "failed",
        },
    }


def run_postgres_explain_smoke() -> Dict[str, Any]:
    """Run a real PostgreSQL EXPLAIN smoke for the JSONB GIN indexes."""

    _docker_available()

    container_name = f"miroconsumer-postgres-smoke-{uuid.uuid4().hex[:8]}"
    host_port = _reserve_port()
    db_url = f"postgresql+psycopg://postgres:postgres@127.0.0.1:{host_port}/miroconsumer_smoke"
    step = {
        "name": "postgres_jsonb_gin_explain",
        "status": "failed",
        "trace_id": _make_trace_id("pg_smoke"),
        "repository_backend": "postgresql",
        "task_status": "FAILED",
        "response_schema": {},
    }

    engine = None
    try:
        _docker_run_container(
            "postgres:16-alpine",
            container_name,
            env={
                "POSTGRES_DB": "miroconsumer_smoke",
                "POSTGRES_USER": "postgres",
                "POSTGRES_PASSWORD": "postgres",
            },
            ports=[(host_port, 5432)],
        )
        _wait_for_postgres(db_url)

        migration_module = _load_migration_module()
        engine = create_engine(db_url, future=True)
        with engine.begin() as connection:
            tables = _create_performance_tables(connection)
            context = MigrationContext.configure(connection)
            with Operations.context(context):
                migration_module.upgrade()

            projects = tables["projects"]
            rows = []
            for index in range(200):
                rows.append(
                    {
                        "id": f"project_{index}",
                        "created_at": datetime.now(timezone.utc),
                        "project_type": "consumer",
                        "data": {
                            "audience": "target" if index % 25 == 0 else "other",
                            "bucket": index % 5,
                        },
                    }
                )
            connection.execute(insert(projects), rows)
            connection.execute(text("ANALYZE projects"))
            connection.execute(text("SET enable_seqscan = off"))

            plan_lines = connection.execute(
                text(
                    "EXPLAIN SELECT id FROM projects "
                    "WHERE data @> CAST(:predicate AS JSONB)"
                ),
                {"predicate": json.dumps({"audience": "target"})},
            ).scalars().all()

        plan_text = "\n".join(plan_lines)
        passed = "ix_projects_data_gin" in plan_text and "Bitmap Index Scan" in plan_text
        step["status"] = "passed" if passed else "failed"
        step["task_status"] = "SUCCEEDED" if passed else "FAILED"
        step["response_schema"] = {
            "index_name": "ix_projects_data_gin",
            "plan": plan_text,
            "row_count": 200,
        }
    finally:
        if engine is not None:
            engine.dispose()
        _docker_remove_container(container_name)

    return {
        "steps": [step],
        "summary": {
            "total": 1,
            "passed": 1 if step["status"] == "passed" else 0,
            "failed": 0 if step["status"] == "passed" else 1,
            "status": "passed" if step["status"] == "passed" else "failed",
        },
    }
