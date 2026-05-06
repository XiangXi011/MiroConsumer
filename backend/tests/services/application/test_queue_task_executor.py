"""Phase7F CI path compatibility tests for QueueTaskExecutor."""

import threading
import time

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.repositories.sqlalchemy import metadata
from app.services.application.sqlite_queue import SQLiteQueueBackend
from app.services.application.queue_task_executor import QueueTaskExecutor
from app.services.application.task_executor import (
    CANCELLED,
    FAILED,
    PENDING,
    RUNNING,
    SUCCEEDED,
)


def _make_memory_session_factory():
    """Return a sessionmaker backed by an in-memory SQLite StaticPool."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    metadata.create_all(engine)
    return sessionmaker(bind=engine)


class TestQueueTaskExecutorSubmit:
    def test_submit_returns_trace_id(self):
        session_factory = _make_memory_session_factory()
        backend = SQLiteQueueBackend(session_factory=session_factory)
        executor = QueueTaskExecutor(backend_name="sqlite", backend=backend)
        tid = executor.submit(lambda: None)
        assert isinstance(tid, str)
        assert tid

    def test_submit_persists_task_to_backend(self):
        session_factory = _make_memory_session_factory()
        backend = SQLiteQueueBackend(session_factory=session_factory)
        executor = QueueTaskExecutor(backend_name="sqlite", backend=backend)
        tid = executor.submit(lambda: None)
        time.sleep(0.2)
        status = backend.get_status(tid)
        assert status["trace_id"] == tid
        assert status["backend"] == "sqlite"

    def test_submit_with_trace_id_uses_provided_id(self):
        session_factory = _make_memory_session_factory()
        backend = SQLiteQueueBackend(session_factory=session_factory)
        executor = QueueTaskExecutor(backend_name="sqlite", backend=backend)
        tid = executor.submit(lambda: None, trace_id="my_custom_trace")
        assert tid == "my_custom_trace"

    def test_submit_without_backend_is_noop_skeleton(self):
        executor = QueueTaskExecutor(backend_name="sqlite", backend=None)
        tid = executor.submit(lambda: None)
        assert isinstance(tid, str)


class TestQueueTaskExecutorGetStatus:
    def test_get_status_returns_dict_for_known_task(self):
        session_factory = _make_memory_session_factory()
        backend = SQLiteQueueBackend(session_factory=session_factory)
        executor = QueueTaskExecutor(backend_name="sqlite", backend=backend)
        tid = executor.submit(lambda: None)
        status = executor.get_status(tid)
        assert isinstance(status, dict)
        assert status["trace_id"] == tid
        assert status["status"] in {PENDING, RUNNING, SUCCEEDED}
        assert status["backend"] == "sqlite"

    def test_get_status_returns_failed_for_unknown(self):
        session_factory = _make_memory_session_factory()
        backend = SQLiteQueueBackend(session_factory=session_factory)
        executor = QueueTaskExecutor(backend_name="sqlite", backend=backend)
        status = executor.get_status("unknown_tid")
        assert isinstance(status, dict)
        assert status["trace_id"] == "unknown_tid"
        assert status["status"] == FAILED
        assert status["error_category"] == "task:not_found"
        assert status["backend"] == "sqlite"

    def test_get_status_reflects_success_after_completion(self):
        session_factory = _make_memory_session_factory()
        backend = SQLiteQueueBackend(session_factory=session_factory)
        executor = QueueTaskExecutor(backend_name="sqlite", backend=backend)
        tid = executor.submit(lambda: None)
        time.sleep(0.3)
        status = executor.get_status(tid)
        assert status["status"] == SUCCEEDED

    def test_get_status_reflects_failure_after_exception(self):
        session_factory = _make_memory_session_factory()
        backend = SQLiteQueueBackend(session_factory=session_factory)
        executor = QueueTaskExecutor(backend_name="sqlite", backend=backend)

        def boom():
            raise ValueError("expected")

        tid = executor.submit(boom)
        time.sleep(0.3)
        status = executor.get_status(tid)
        assert status["status"] == FAILED
        assert "error_category" in status


class TestQueueTaskExecutorCancel:
    def test_cancel_returns_dict_with_cancelled_true(self):
        session_factory = _make_memory_session_factory()
        backend = SQLiteQueueBackend(session_factory=session_factory)
        executor = QueueTaskExecutor(backend_name="sqlite", backend=backend)
        tid = executor.submit(lambda: time.sleep(0.5))
        result = executor.cancel(tid)
        assert isinstance(result, dict)
        assert result["trace_id"] == tid
        assert result["status"] == CANCELLED
        assert result["cancelled"] is True
        assert result["backend"] == "sqlite"

    def test_cancel_updates_backend_status(self):
        session_factory = _make_memory_session_factory()
        backend = SQLiteQueueBackend(session_factory=session_factory)
        executor = QueueTaskExecutor(backend_name="sqlite", backend=backend)

        # Intercept _spawn_worker to prevent a racing worker thread
        original_spawn = executor._spawn_worker
        spawned = {}

        def deferred_spawn(tid, fn, args, kwargs):
            spawned["tid"] = tid
            spawned["fn"] = fn
            spawned["args"] = args
            spawned["kwargs"] = kwargs

        executor._spawn_worker = deferred_spawn

        tid = executor.submit(lambda: time.sleep(0.5))
        result = executor.cancel(tid)
        assert result["cancelled"] is True
        assert result["status"] == CANCELLED

        # Now start the worker after cancel (it should see CANCELLED and skip)
        if "tid" in spawned:
            original_spawn(spawned["tid"], spawned["fn"], spawned["args"], spawned["kwargs"])

        time.sleep(0.2)
        status = backend.get_status(tid)
        assert status["status"] == CANCELLED

    def test_cancel_unknown_returns_dict_with_cancelled_false(self):
        session_factory = _make_memory_session_factory()
        backend = SQLiteQueueBackend(session_factory=session_factory)
        executor = QueueTaskExecutor(backend_name="sqlite", backend=backend)
        result = executor.cancel("unknown_tid")
        assert isinstance(result, dict)
        assert result["trace_id"] == "unknown_tid"
        assert result["status"] == FAILED
        assert result["cancelled"] is False
        assert result["error_category"] == "task:not_found"

    def test_cancel_before_completion_final_status_stays_cancelled(self):
        session_factory = _make_memory_session_factory()
        backend = SQLiteQueueBackend(session_factory=session_factory)
        executor = QueueTaskExecutor(backend_name="sqlite", backend=backend)

        started = threading.Event()
        can_finish = threading.Event()

        def long_work():
            started.set()
            can_finish.wait(timeout=5)

        tid = executor.submit(long_work)
        started.wait(timeout=5)
        executor.cancel(tid)
        can_finish.set()
        time.sleep(0.2)
        status = backend.get_status(tid)
        assert status["status"] == CANCELLED


class TestQueueTaskExecutorIdempotency:
    def test_duplicate_idempotency_key_returns_same_trace_id(self):
        session_factory = _make_memory_session_factory()
        backend = SQLiteQueueBackend(session_factory=session_factory)
        executor = QueueTaskExecutor(backend_name="sqlite", backend=backend)
        tid1 = executor.submit(
            lambda: None,
            trace_id="task_1",
            task_type="test_task",
            idempotency_key="idem_key_1",
        )
        tid2 = executor.submit(
            lambda: None,
            trace_id="task_2",
            task_type="test_task",
            idempotency_key="idem_key_1",
        )
        assert tid1 == tid2

    def test_different_idempotency_keys_get_different_trace_ids(self):
        session_factory = _make_memory_session_factory()
        backend = SQLiteQueueBackend(session_factory=session_factory)
        executor = QueueTaskExecutor(backend_name="sqlite", backend=backend)
        tid1 = executor.submit(
            lambda: None,
            trace_id="task_a",
            task_type="test_task",
            idempotency_key="key_a",
        )
        tid2 = executor.submit(
            lambda: None,
            trace_id="task_b",
            task_type="test_task",
            idempotency_key="key_b",
        )
        assert tid1 != tid2

    def test_duplicate_trace_id_returns_existing_trace_id(self):
        session_factory = _make_memory_session_factory()
        backend = SQLiteQueueBackend(session_factory=session_factory)
        executor = QueueTaskExecutor(backend_name="sqlite", backend=backend)
        tid1 = executor.submit(lambda: None, trace_id="same_tid")
        tid2 = executor.submit(lambda: None, trace_id="same_tid")
        assert tid1 == tid2
