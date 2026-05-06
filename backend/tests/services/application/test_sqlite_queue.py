"""Tests for SQLite-backed durable task queue.

Uses in-memory SQLite so no external DB server is required.
"""

import time
import uuid
from datetime import datetime, timezone, timedelta

import pytest
from sqlalchemy import create_engine, insert, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import Config
from app.repositories.sqlalchemy import metadata, tasks, task_attempts, dead_letters
from app.services.application.sqlite_queue import SQLiteQueueBackend
from app.services.application.queue_task_executor import QueueTaskExecutor
from app.services.application.task_executor import (
    PENDING,
    RUNNING,
    SUCCEEDED,
    FAILED,
    CANCELLED,
    DEAD_LETTER,
    ThreadTaskExecutor,
    create_task_executor,
)


@pytest.fixture
def session_factory():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    metadata.create_all(engine)
    return sessionmaker(bind=engine)


# ─────────────────────────────────────────────────────────────────
# 1. Persistence
# ─────────────────────────────────────────────────────────────────


class TestSQLiteQueueBackendEnqueue:
    def test_enqueue_persists_task_with_trace_id(self, session_factory):
        backend = SQLiteQueueBackend(session_factory=session_factory)
        trace_id = "task_123"

        def dummy_fn():
            pass

        result, created = backend.enqueue(trace_id, dummy_fn)
        assert result == trace_id
        assert created is True

        with session_factory() as session:
            row = (
                session.execute(select(tasks).where(tasks.c.id == trace_id))
                .mappings()
                .fetchone()
            )
            assert row is not None
            assert row["id"] == trace_id
            assert row["status"] == PENDING

    def test_enqueue_persists_task_type_and_payload(self, session_factory):
        backend = SQLiteQueueBackend(session_factory=session_factory)
        trace_id = "task_456"

        def my_task(x, y):
            pass

        tid, created = backend.enqueue(
            trace_id,
            my_task,
            1,
            2,
            task_type="my_task_type",
            simulation_id="sim_1",
            run_id="run_1",
        )
        assert created is True

        with session_factory() as session:
            row = (
                session.execute(select(tasks).where(tasks.c.id == trace_id))
                .mappings()
                .fetchone()
            )
            assert row["task_type"] == "my_task_type"
            assert row["simulation_id"] == "sim_1"
            assert row["run_id"] == "run_1"
            payload = row["payload"]
            assert payload["callable"] == "my_task"
            assert payload["args"] == [1, 2]
            assert payload["kwargs"] == {}

    def test_enqueue_default_simulation_id_and_run_id(self, session_factory):
        backend = SQLiteQueueBackend(session_factory=session_factory)

        _, created = backend.enqueue("t1", lambda: None)
        assert created is True

        with session_factory() as session:
            row = (
                session.execute(select(tasks).where(tasks.c.id == "t1"))
                .mappings()
                .fetchone()
            )
            assert row["simulation_id"] == ""
            assert row["run_id"] == "base"

    def test_enqueue_payload_contains_idempotency_key(self, session_factory):
        backend = SQLiteQueueBackend(session_factory=session_factory)

        _, created = backend.enqueue("t2", lambda: None, idempotency_key="idem_1", task_type="report")
        assert created is True

        with session_factory() as session:
            row = (
                session.execute(select(tasks).where(tasks.c.id == "t2"))
                .mappings()
                .fetchone()
            )
            assert row["payload"]["idempotency_key"] == "idem_1"

    def test_enqueue_payload_has_json_safe_kwargs(self, session_factory):
        backend = SQLiteQueueBackend(session_factory=session_factory)

        def task_fn(a, b=None):
            pass

        _, created = backend.enqueue("t3", task_fn, "hello", b="world", task_type="test")
        assert created is True

        with session_factory() as session:
            row = (
                session.execute(select(tasks).where(tasks.c.id == "t3"))
                .mappings()
                .fetchone()
            )
            assert row["payload"]["args"] == ["hello"]
            assert row["payload"]["kwargs"] == {"b": "world"}


# ─────────────────────────────────────────────────────────────────
# 1b. JSON-safe payload conversion
# ─────────────────────────────────────────────────────────────────


class TestSQLiteQueueBackendJsonSafePayload:
    def test_enqueue_converts_datetime_in_args_to_iso_string(self, session_factory):
        backend = SQLiteQueueBackend(session_factory=session_factory)
        dt = datetime(2024, 6, 15, 12, 30, 0, tzinfo=timezone.utc)

        def task_fn(arg):
            pass

        _, created = backend.enqueue("dt_task", task_fn, dt, task_type="test")
        assert created is True

        with session_factory() as session:
            row = (
                session.execute(select(tasks).where(tasks.c.id == "dt_task"))
                .mappings()
                .fetchone()
            )
            payload = row["payload"]
            assert payload["args"] == ["2024-06-15T12:30:00+00:00"]

    def test_enqueue_converts_datetime_in_kwargs_to_iso_string(self, session_factory):
        backend = SQLiteQueueBackend(session_factory=session_factory)
        dt = datetime(2024, 6, 15, 12, 30, 0, tzinfo=timezone.utc)

        def task_fn(when=None):
            pass

        _, created = backend.enqueue("dt_kw_task", task_fn, when=dt, task_type="test")
        assert created is True

        with session_factory() as session:
            row = (
                session.execute(select(tasks).where(tasks.c.id == "dt_kw_task"))
                .mappings()
                .fetchone()
            )
            payload = row["payload"]
            assert payload["kwargs"] == {"when": "2024-06-15T12:30:00+00:00"}

    def test_enqueue_converts_custom_object_to_repr_string(self, session_factory):
        backend = SQLiteQueueBackend(session_factory=session_factory)

        class CustomObj:
            def __repr__(self):
                return "CustomObj(x=42)"

        def task_fn(obj):
            pass

        _, created = backend.enqueue("obj_task", task_fn, CustomObj(), task_type="test")
        assert created is True

        with session_factory() as session:
            row = (
                session.execute(select(tasks).where(tasks.c.id == "obj_task"))
                .mappings()
                .fetchone()
            )
            payload = row["payload"]
            assert payload["args"] == ["CustomObj(x=42)"]


# ─────────────────────────────────────────────────────────────────
# 2. Idempotency
# ─────────────────────────────────────────────────────────────────


class TestSQLiteQueueBackendIdempotency:
    def test_duplicate_enqueue_returns_existing_trace_id_and_created_false(self, session_factory):
        backend = SQLiteQueueBackend(session_factory=session_factory)

        tid1, created1 = backend.enqueue(
            "dup_1", lambda: None, task_type="report", idempotency_key="idem_key"
        )
        tid2, created2 = backend.enqueue(
            "dup_2", lambda: None, task_type="report", idempotency_key="idem_key"
        )

        assert tid1 == tid2
        assert created1 is True
        assert created2 is False

        with session_factory() as session:
            rows = session.execute(select(tasks)).fetchall()
            assert len(rows) == 1
            assert rows[0][0] == tid1

    def test_different_idempotency_keys_insert_separate_tasks(self, session_factory):
        backend = SQLiteQueueBackend(session_factory=session_factory)

        tid1, created1 = backend.enqueue(
            "task_a", lambda: None, task_type="report", idempotency_key="key_a"
        )
        tid2, created2 = backend.enqueue(
            "task_b", lambda: None, task_type="report", idempotency_key="key_b"
        )

        assert tid1 != tid2
        assert tid1 == "task_a"
        assert tid2 == "task_b"
        assert created1 is True
        assert created2 is True

        with session_factory() as session:
            rows = session.execute(select(tasks)).fetchall()
            assert len(rows) == 2

    def test_same_idempotency_key_different_task_type_inserts_separate(
        self, session_factory
    ):
        backend = SQLiteQueueBackend(session_factory=session_factory)

        tid1, created1 = backend.enqueue(
            "task_a", lambda: None, task_type="report", idempotency_key="key"
        )
        tid2, created2 = backend.enqueue(
            "task_b", lambda: None, task_type="simulation", idempotency_key="key"
        )

        assert tid1 != tid2
        assert created1 is True
        assert created2 is True

        with session_factory() as session:
            rows = session.execute(select(tasks)).fetchall()
            assert len(rows) == 2


# ─────────────────────────────────────────────────────────────────
# 3. get_status
# ─────────────────────────────────────────────────────────────────


class TestSQLiteQueueBackendGetStatus:
    def test_get_status_returns_dict_for_known_task(self, session_factory):
        backend = SQLiteQueueBackend(session_factory=session_factory)
        backend.enqueue("status_1", lambda: None, task_type="report")

        status = backend.get_status("status_1")

        assert isinstance(status, dict)
        assert status["trace_id"] == "status_1"
        assert status["status"] == PENDING
        assert status["backend"] == "sqlite"
        assert status["task_type"] == "report"

    def test_get_status_returns_failed_for_unknown(self, session_factory):
        backend = SQLiteQueueBackend(session_factory=session_factory)

        status = backend.get_status("unknown")

        assert isinstance(status, dict)
        assert status["trace_id"] == "unknown"
        assert status["status"] == FAILED
        assert status["error_category"] == "task:not_found"
        assert status["backend"] == "sqlite"


# ─────────────────────────────────────────────────────────────────
# 4. cancel
# ─────────────────────────────────────────────────────────────────


class TestSQLiteQueueBackendCancel:
    def test_cancel_updates_status_and_returns_dict(self, session_factory):
        backend = SQLiteQueueBackend(session_factory=session_factory)
        backend.enqueue("cancel_1", lambda: None)

        result = backend.cancel("cancel_1")

        assert isinstance(result, dict)
        assert result["trace_id"] == "cancel_1"
        assert result["status"] == CANCELLED
        assert result["cancelled"] is True

        with session_factory() as session:
            row = (
                session.execute(select(tasks).where(tasks.c.id == "cancel_1"))
                .mappings()
                .fetchone()
            )
            assert row["status"] == CANCELLED

    def test_cancel_returns_failed_for_unknown(self, session_factory):
        backend = SQLiteQueueBackend(session_factory=session_factory)

        result = backend.cancel("unknown")

        assert isinstance(result, dict)
        assert result["trace_id"] == "unknown"
        assert result["status"] == FAILED
        assert result["cancelled"] is False
        assert result["error_category"] == "task:not_found"


# ─────────────────────────────────────────────────────────────────
# 6. recover_stale_running
# ─────────────────────────────────────────────────────────────────


class TestSQLiteQueueBackendRecover:
    def test_recover_finds_stale_running_and_resets_to_pending(self, session_factory):
        backend = SQLiteQueueBackend(session_factory=session_factory)
        now = datetime.now(timezone.utc)
        old_time = now - timedelta(seconds=100)

        with session_factory() as session:
            session.execute(
                insert(tasks).values(
                    id="stale_1",
                    simulation_id="",
                    run_id="base",
                    task_type="test",
                    status=RUNNING,
                    payload={"attempt_count": 0, "callable": "my_fn"},
                    updated_at=old_time,
                )
            )
            session.commit()

        backend.recover_stale_running(
            now, visibility_timeout_seconds=30, retry_limit=3
        )

        with session_factory() as session:
            row = (
                session.execute(select(tasks).where(tasks.c.id == "stale_1"))
                .mappings()
                .fetchone()
            )
            assert row["status"] == PENDING
            payload = row["payload"]
            assert payload["attempt_count"] == 1

            attempts = session.execute(
                select(task_attempts).where(task_attempts.c.task_id == "stale_1")
            ).fetchall()
            assert len(attempts) == 1
            assert attempts[0].attempt_number == 1

    def test_recover_reaches_dead_letter_after_retry_limit(self, session_factory):
        backend = SQLiteQueueBackend(session_factory=session_factory)
        now = datetime.now(timezone.utc)
        old_time = now - timedelta(seconds=100)

        with session_factory() as session:
            session.execute(
                insert(tasks).values(
                    id="stale_dl",
                    simulation_id="",
                    run_id="base",
                    task_type="test",
                    status=RUNNING,
                    payload={"attempt_count": 3, "callable": "my_fn", "args": []},
                    updated_at=old_time,
                )
            )
            session.commit()

        backend.recover_stale_running(
            now, visibility_timeout_seconds=30, retry_limit=3
        )

        with session_factory() as session:
            row = (
                session.execute(select(tasks).where(tasks.c.id == "stale_dl"))
                .mappings()
                .fetchone()
            )
            assert row["status"] == DEAD_LETTER

            # No new task_attempts because limit was already reached
            attempts = session.execute(
                select(task_attempts).where(task_attempts.c.task_id == "stale_dl")
            ).fetchall()
            assert len(attempts) == 0

            dl = (
                session.execute(
                    select(dead_letters).where(dead_letters.c.task_id == "stale_dl")
                )
                .mappings()
                .fetchone()
            )
            assert dl is not None
            assert dl["reason"] is not None
            payload = dl["payload"]
            assert payload["attempt_count"] == 3
            assert "written_at" in payload

    def test_dead_letter_payload_includes_all_required_fields(self, session_factory):
        backend = SQLiteQueueBackend(session_factory=session_factory)
        now = datetime.now(timezone.utc)
        old_time = now - timedelta(seconds=100)
        original_payload = {
            "attempt_count": 2,
            "callable": "my_fn",
            "args": ["hello"],
            "kwargs": {"key": "value"},
        }

        with session_factory() as session:
            session.execute(
                insert(tasks).values(
                    id="stale_dl_full",
                    simulation_id="",
                    run_id="base",
                    task_type="test",
                    status=RUNNING,
                    payload=original_payload,
                    updated_at=old_time,
                )
            )
            session.commit()

        backend.recover_stale_running(
            now, visibility_timeout_seconds=30, retry_limit=2
        )

        with session_factory() as session:
            dl = (
                session.execute(
                    select(dead_letters).where(dead_letters.c.task_id == "stale_dl_full")
                )
                .mappings()
                .fetchone()
            )
            assert dl is not None
            payload = dl["payload"]
            # original_payload must be the task payload before dead-letter mutation
            assert "original_payload" in payload
            assert payload["original_payload"]["callable"] == "my_fn"
            assert payload["original_payload"]["args"] == ["hello"]
            assert payload["original_payload"]["kwargs"] == {"key": "value"}
            # failure_reason must be present
            assert "failure_reason" in payload
            assert payload["failure_reason"] == "max_retries_exceeded"
            # final_attempt_count must reflect the count at dead-letter time
            assert "final_attempt_count" in payload
            assert payload["final_attempt_count"] == 2
            # written_at must be present
            assert "written_at" in payload
            # existing attempt_count must be preserved
            assert payload["attempt_count"] == 2

    def test_recover_ignores_fresh_running_tasks(self, session_factory):
        backend = SQLiteQueueBackend(session_factory=session_factory)
        now = datetime.now(timezone.utc)
        recent_time = now - timedelta(seconds=10)

        with session_factory() as session:
            session.execute(
                insert(tasks).values(
                    id="fresh_1",
                    simulation_id="",
                    run_id="base",
                    task_type="test",
                    status=RUNNING,
                    payload={},
                    updated_at=recent_time,
                )
            )
            session.commit()

        backend.recover_stale_running(
            now, visibility_timeout_seconds=30, retry_limit=3
        )

        with session_factory() as session:
            row = (
                session.execute(select(tasks).where(tasks.c.id == "fresh_1"))
                .mappings()
                .fetchone()
            )
            assert row["status"] == RUNNING

    def test_recover_ignores_non_running_tasks(self, session_factory):
        backend = SQLiteQueueBackend(session_factory=session_factory)
        now = datetime.now(timezone.utc)
        old_time = now - timedelta(seconds=100)

        with session_factory() as session:
            session.execute(
                insert(tasks).values(
                    id="pending_1",
                    simulation_id="",
                    run_id="base",
                    task_type="test",
                    status=PENDING,
                    payload={},
                    updated_at=old_time,
                )
            )
            session.commit()

        backend.recover_stale_running(
            now, visibility_timeout_seconds=30, retry_limit=3
        )

        with session_factory() as session:
            row = (
                session.execute(select(tasks).where(tasks.c.id == "pending_1"))
                .mappings()
                .fetchone()
            )
            assert row["status"] == PENDING


# ─────────────────────────────────────────────────────────────────
# 7. list_dead_letters
# ─────────────────────────────────────────────────────────────────


class TestSQLiteQueueBackendListDeadLetters:
    def test_list_dead_letters_returns_records(self, session_factory):
        backend = SQLiteQueueBackend(session_factory=session_factory)

        with session_factory() as session:
            session.execute(
                insert(dead_letters).values(
                    id="dl_1",
                    simulation_id="",
                    run_id="base",
                    task_id="task_1",
                    reason="max retries",
                    payload={"attempt_count": 3},
                )
            )
            session.commit()

        records = backend.list_dead_letters()
        assert len(records) == 1
        assert records[0]["task_id"] == "task_1"
        assert records[0]["reason"] == "max retries"


# ─────────────────────────────────────────────────────────────────
# 2. QueueTaskExecutor.submit metadata forwarding
# ─────────────────────────────────────────────────────────────────


class TestQueueTaskExecutorWithSQLiteBackend:
    def test_submit_passes_metadata_to_backend(self, session_factory):
        backend = SQLiteQueueBackend(session_factory=session_factory)
        executor = QueueTaskExecutor(backend_name="sqlite", backend=backend)

        trace_id = executor.submit(
            lambda: time.sleep(0.5),
            task_type="report",
            idempotency_key="idem_1",
            simulation_id="sim_1",
            run_id="run_1",
        )

        assert trace_id is not None

        status = backend.get_status(trace_id)
        # Task may already be RUNNING by the time we check; assert it was enqueued
        assert status["status"] in {PENDING, RUNNING}
        assert status["task_type"] == "report"

    def test_submit_uses_backend_return_value_as_trace_id(self, session_factory):
        backend = SQLiteQueueBackend(session_factory=session_factory)
        executor = QueueTaskExecutor(backend_name="sqlite", backend=backend)

        trace_id = executor.submit(
            lambda: None, task_type="report", idempotency_key="shared_key"
        )
        trace_id2 = executor.submit(
            lambda: None, task_type="report", idempotency_key="shared_key"
        )

        assert trace_id == trace_id2


# ─────────────────────────────────────────────────────────────────
# 2. ThreadTaskExecutor metadata tolerance
# ─────────────────────────────────────────────────────────────────


class TestThreadTaskExecutorMetadata:
    def test_thread_executor_ignores_metadata_kwargs(self):
        executor = ThreadTaskExecutor()
        results = []

        def capture(a):
            results.append(a)

        executor.submit(
            capture,
            "hello",
            task_type="report",
            idempotency_key="k",
            simulation_id="s",
        )
        time.sleep(0.2)

        assert results == ["hello"]


# ─────────────────────────────────────────────────────────────────
# 8. create_task_executor for sqlite backend
# ─────────────────────────────────────────────────────────────────


class TestCreateTaskExecutorSQLite:
    def test_create_task_executor_sqlite_with_db_url(self, monkeypatch):
        monkeypatch.setenv("QUEUE_BACKEND", "sqlite")
        monkeypatch.setenv("DB_URL", "sqlite:///:memory:")
        monkeypatch.setattr(Config, "_queue_backend_cache", None)
        monkeypatch.setattr(Config, "_db_url_cache", None)

        executor = create_task_executor()
        assert isinstance(executor, QueueTaskExecutor)
        assert isinstance(executor.backend, SQLiteQueueBackend)

    def test_create_task_executor_sqlite_raises_when_db_url_empty(self, monkeypatch):
        monkeypatch.setenv("QUEUE_BACKEND", "sqlite")
        monkeypatch.delenv("DB_URL", raising=False)
        monkeypatch.setattr(Config, "_queue_backend_cache", None)
        monkeypatch.setattr(Config, "_db_url_cache", None)

        with pytest.raises(ValueError) as exc_info:
            create_task_executor()
        assert "DB_URL" in str(exc_info.value)


# ─────────────────────────────────────────────────────────────────
# 9. Task table default status uppercase PENDING
# ─────────────────────────────────────────────────────────────────


class TestTaskTableDefaultStatus:
    def test_task_status_default_is_uppercase_pending(self, session_factory):
        backend = SQLiteQueueBackend(session_factory=session_factory)
        _, created = backend.enqueue("default_status_task", lambda: None)
        assert created is True

        with session_factory() as session:
            row = (
                session.execute(
                    select(tasks).where(tasks.c.id == "default_status_task")
                )
                .mappings()
                .fetchone()
            )
            assert row["status"] == "PENDING"


# ─────────────────────────────────────────────────────────────────
# 10. Enqueue created/duplicate signal
# ─────────────────────────────────────────────────────────────────


class TestSQLiteQueueBackendEnqueueSignal:
    def test_enqueue_returns_created_true_for_new_task(self, session_factory):
        backend = SQLiteQueueBackend(session_factory=session_factory)
        tid, created = backend.enqueue("new_task", lambda: None, task_type="report")
        assert tid == "new_task"
        assert created is True

    def test_enqueue_returns_created_false_for_duplicate_idempotency_key(self, session_factory):
        backend = SQLiteQueueBackend(session_factory=session_factory)
        tid1, created1 = backend.enqueue(
            "first", lambda: None, task_type="report", idempotency_key="idem_key"
        )
        tid2, created2 = backend.enqueue(
            "second", lambda: None, task_type="report", idempotency_key="idem_key"
        )
        assert tid1 == tid2
        assert created1 is True
        assert created2 is False

    def test_enqueue_returns_created_false_for_duplicate_trace_id(self, session_factory):
        backend = SQLiteQueueBackend(session_factory=session_factory)
        tid1, created1 = backend.enqueue("same_id", lambda: None)
        tid2, created2 = backend.enqueue("same_id", lambda: None)
        assert tid1 == "same_id"
        assert tid2 == "same_id"
        assert created1 is True
        assert created2 is False


# ─────────────────────────────────────────────────────────────────
# 11. Lifecycle methods: mark_running, mark_succeeded, mark_failed
# ─────────────────────────────────────────────────────────────────


class TestSQLiteQueueBackendLifecycleMethods:
    def test_mark_running_updates_status_to_running(self, session_factory):
        backend = SQLiteQueueBackend(session_factory=session_factory)
        backend.enqueue("lifecycle_1", lambda: None, task_type="report")

        ok = backend.mark_running("lifecycle_1")
        assert ok is True

        with session_factory() as session:
            row = (
                session.execute(select(tasks).where(tasks.c.id == "lifecycle_1"))
                .mappings()
                .fetchone()
            )
            assert row["status"] == RUNNING

    def test_mark_running_preserves_payload(self, session_factory):
        backend = SQLiteQueueBackend(session_factory=session_factory)

        def my_fn(a, b):
            pass

        backend.enqueue("lifecycle_2", my_fn, 1, 2, task_type="report")
        backend.mark_running("lifecycle_2")

        with session_factory() as session:
            row = (
                session.execute(select(tasks).where(tasks.c.id == "lifecycle_2"))
                .mappings()
                .fetchone()
            )
            payload = row["payload"]
            assert payload["callable"] == "my_fn"
            assert payload["args"] == [1, 2]
            assert payload["kwargs"] == {}

    def test_mark_running_returns_false_for_unknown_task(self, session_factory):
        backend = SQLiteQueueBackend(session_factory=session_factory)
        ok = backend.mark_running("unknown")
        assert ok is False

    def test_mark_succeeded_updates_status_to_succeeded(self, session_factory):
        backend = SQLiteQueueBackend(session_factory=session_factory)
        backend.enqueue("succ_1", lambda: None)
        backend.mark_running("succ_1")

        ok = backend.mark_succeeded("succ_1")
        assert ok is True

        with session_factory() as session:
            row = (
                session.execute(select(tasks).where(tasks.c.id == "succ_1"))
                .mappings()
                .fetchone()
            )
            assert row["status"] == SUCCEEDED

    def test_mark_succeeded_stores_result_in_payload(self, session_factory):
        backend = SQLiteQueueBackend(session_factory=session_factory)
        backend.enqueue("succ_2", lambda: None)
        backend.mark_running("succ_2")

        backend.mark_succeeded("succ_2", result={"output": "hello"})

        with session_factory() as session:
            row = (
                session.execute(select(tasks).where(tasks.c.id == "succ_2"))
                .mappings()
                .fetchone()
            )
            payload = row["payload"]
            assert payload["result"] == {"output": "hello"}

    def test_mark_succeeded_preserves_existing_payload(self, session_factory):
        backend = SQLiteQueueBackend(session_factory=session_factory)
        backend.enqueue("succ_3", lambda: None, task_type="report")
        backend.mark_running("succ_3")

        backend.mark_succeeded("succ_3", result=42)

        with session_factory() as session:
            row = (
                session.execute(select(tasks).where(tasks.c.id == "succ_3"))
                .mappings()
                .fetchone()
            )
            payload = row["payload"]
            assert payload["result"] == 42
            assert payload["callable"] == "<lambda>"

    def test_mark_succeeded_returns_false_for_unknown_task(self, session_factory):
        backend = SQLiteQueueBackend(session_factory=session_factory)
        ok = backend.mark_succeeded("unknown")
        assert ok is False

    def test_mark_failed_updates_status_to_failed(self, session_factory):
        backend = SQLiteQueueBackend(session_factory=session_factory)
        backend.enqueue("fail_1", lambda: None)
        backend.mark_running("fail_1")

        ok = backend.mark_failed("fail_1", error_category="biz:validation", error="bad input")
        assert ok is True

        with session_factory() as session:
            row = (
                session.execute(select(tasks).where(tasks.c.id == "fail_1"))
                .mappings()
                .fetchone()
            )
            assert row["status"] == FAILED

    def test_mark_failed_stores_error_category_and_error_in_payload(self, session_factory):
        backend = SQLiteQueueBackend(session_factory=session_factory)
        backend.enqueue("fail_2", lambda: None)
        backend.mark_running("fail_2")

        backend.mark_failed("fail_2", error_category="infra:external", error="connection refused")

        with session_factory() as session:
            row = (
                session.execute(select(tasks).where(tasks.c.id == "fail_2"))
                .mappings()
                .fetchone()
            )
            payload = row["payload"]
            assert payload["error_category"] == "infra:external"
            assert payload["error"] == "connection refused"

    def test_mark_failed_preserves_existing_payload(self, session_factory):
        backend = SQLiteQueueBackend(session_factory=session_factory)
        backend.enqueue("fail_3", lambda: None, task_type="report")
        backend.mark_running("fail_3")

        backend.mark_failed("fail_3", error_category="uncategorized:RuntimeError", error="boom")

        with session_factory() as session:
            row = (
                session.execute(select(tasks).where(tasks.c.id == "fail_3"))
                .mappings()
                .fetchone()
            )
            payload = row["payload"]
            assert payload["error_category"] == "uncategorized:RuntimeError"
            assert payload["callable"] == "<lambda>"

    def test_mark_failed_returns_false_for_unknown_task(self, session_factory):
        backend = SQLiteQueueBackend(session_factory=session_factory)
        ok = backend.mark_failed("unknown", error_category="test", error="test")
        assert ok is False

    def test_mark_succeeded_does_not_overwrite_cancelled(self, session_factory):
        backend = SQLiteQueueBackend(session_factory=session_factory)
        backend.enqueue("cancel_then_succ", lambda: None)
        backend.cancel("cancel_then_succ")

        ok = backend.mark_succeeded("cancel_then_succ", result="should_not_store")

        assert ok is False
        status = backend.get_status("cancel_then_succ")
        assert status["status"] == CANCELLED

        with session_factory() as session:
            row = (
                session.execute(select(tasks).where(tasks.c.id == "cancel_then_succ"))
                .mappings()
                .fetchone()
            )
            assert row["status"] == CANCELLED
            assert "should_not_store" not in str(row["payload"])

    def test_mark_failed_does_not_overwrite_cancelled(self, session_factory):
        backend = SQLiteQueueBackend(session_factory=session_factory)
        backend.enqueue("cancel_then_fail", lambda: None)
        backend.cancel("cancel_then_fail")

        ok = backend.mark_failed("cancel_then_fail", error_category="test", error="should_not_store")

        assert ok is False
        status = backend.get_status("cancel_then_fail")
        assert status["status"] == CANCELLED

        with session_factory() as session:
            row = (
                session.execute(select(tasks).where(tasks.c.id == "cancel_then_fail"))
                .mappings()
                .fetchone()
            )
            assert row["status"] == CANCELLED
            assert "should_not_store" not in str(row["payload"])


# ─────────────────────────────────────────────────────────────────
# 12. QueueTaskExecutor execution lifecycle with SQLite backend
# ─────────────────────────────────────────────────────────────────


class TestQueueTaskExecutorExecutionLifecycle:
    def test_executes_submitted_fn_asynchronously(self, session_factory):
        import threading
        backend = SQLiteQueueBackend(session_factory=session_factory)
        executor = QueueTaskExecutor(backend_name="sqlite", backend=backend)
        results = []

        def capture():
            results.append(threading.current_thread().name)

        trace_id = executor.submit(capture)
        time.sleep(0.3)

        assert len(results) == 1
        assert "Thread" in results[0]

    def test_updates_status_running_then_succeeded(self, session_factory):
        backend = SQLiteQueueBackend(session_factory=session_factory)
        executor = QueueTaskExecutor(backend_name="sqlite", backend=backend)

        def work():
            pass

        trace_id = executor.submit(work)
        time.sleep(0.3)

        status = backend.get_status(trace_id)
        assert status["status"] == SUCCEEDED

    def test_updates_status_failed_when_fn_raises(self, session_factory):
        backend = SQLiteQueueBackend(session_factory=session_factory)
        executor = QueueTaskExecutor(backend_name="sqlite", backend=backend)

        def boom():
            raise ValueError("expected failure")

        trace_id = executor.submit(boom)
        time.sleep(0.3)

        status = backend.get_status(trace_id)
        assert status["status"] == FAILED

    def test_failed_status_includes_error_category(self, session_factory):
        backend = SQLiteQueueBackend(session_factory=session_factory)
        executor = QueueTaskExecutor(backend_name="sqlite", backend=backend)

        def boom():
            raise ValueError("expected failure")

        trace_id = executor.submit(boom)
        time.sleep(0.3)

        status = backend.get_status(trace_id)
        assert status["status"] == FAILED
        assert "error_category" in status

    def test_does_not_pass_metadata_kwargs_to_fn(self, session_factory):
        backend = SQLiteQueueBackend(session_factory=session_factory)
        executor = QueueTaskExecutor(backend_name="sqlite", backend=backend)
        received = {}

        def capture(**kwargs):
            received.update(kwargs)

        trace_id = executor.submit(
            capture,
            task_type="report",
            idempotency_key="k",
            simulation_id="s",
            run_id="r",
        )
        time.sleep(0.3)

        assert "task_type" not in received
        assert "idempotency_key" not in received
        assert "simulation_id" not in received
        assert "run_id" not in received

    def test_duplicate_idempotency_returns_existing_trace_id(self, session_factory):
        backend = SQLiteQueueBackend(session_factory=session_factory)
        executor = QueueTaskExecutor(backend_name="sqlite", backend=backend)

        trace_id1 = executor.submit(
            lambda: None, task_type="report", idempotency_key="idem_dup"
        )
        trace_id2 = executor.submit(
            lambda: None, task_type="report", idempotency_key="idem_dup"
        )

        assert trace_id1 == trace_id2

    def test_duplicate_idempotency_does_not_execute_fn_again(self, session_factory):
        backend = SQLiteQueueBackend(session_factory=session_factory)
        executor = QueueTaskExecutor(backend_name="sqlite", backend=backend)
        call_count = [0]

        def count():
            call_count[0] += 1

        trace_id1 = executor.submit(
            count, task_type="report", idempotency_key="idem_count"
        )
        trace_id2 = executor.submit(
            count, task_type="report", idempotency_key="idem_count"
        )
        time.sleep(0.3)

        assert trace_id1 == trace_id2
        assert call_count[0] == 1
