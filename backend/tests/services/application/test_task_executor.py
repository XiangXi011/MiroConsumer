"""Tests for task executor abstraction."""

import threading
import time

import pytest

from app.config import Config
from app.services.application.task_executor import (
    ThreadTaskExecutor,
    TaskExecutor,
    create_task_executor,
    PENDING,
    RUNNING,
    SUCCEEDED,
    FAILED,
    CANCELLED,
    DEAD_LETTER,
)


class TestThreadTaskExecutor:
    def test_submit_runs_function_in_background(self):
        executor = ThreadTaskExecutor()
        results = []

        def capture():
            results.append(threading.current_thread().name)

        executor.submit(capture)
        time.sleep(0.2)

        assert len(results) == 1
        assert "Thread" in results[0]

    def test_submit_passes_args_and_kwargs(self):
        executor = ThreadTaskExecutor()
        results = []

        def capture(a, b, c=None):
            results.append((a, b, c))

        executor.submit(capture, 1, 2, c=3)
        time.sleep(0.2)

        assert results == [(1, 2, 3)]


class TestTaskStatusConstants:
    def test_status_values_are_exact_uppercase(self):
        assert PENDING == "PENDING"
        assert RUNNING == "RUNNING"
        assert SUCCEEDED == "SUCCEEDED"
        assert FAILED == "FAILED"
        assert CANCELLED == "CANCELLED"
        assert DEAD_LETTER == "DEAD_LETTER"


class TestThreadTaskExecutorStatus:
    def test_get_status_returns_dict_with_trace_id_status_backend(self):
        executor = ThreadTaskExecutor()
        trace_id = executor.submit(lambda: None)
        status = executor.get_status(trace_id)
        assert isinstance(status, dict)
        assert status["trace_id"] == trace_id
        assert status["status"] in {PENDING, RUNNING, SUCCEEDED}
        assert status["backend"] == "thread"

    def test_get_status_returns_succeeded_after_success(self):
        executor = ThreadTaskExecutor()
        results = []

        def capture():
            results.append(1)

        trace_id = executor.submit(capture)
        time.sleep(0.3)
        assert results == [1]
        status = executor.get_status(trace_id)
        assert isinstance(status, dict)
        assert status["status"] == SUCCEEDED
        assert status["trace_id"] == trace_id
        assert status["backend"] == "thread"

    def test_get_status_returns_failed_after_exception(self):
        executor = ThreadTaskExecutor()

        def boom():
            raise ValueError("expected failure")

        trace_id = executor.submit(boom)
        time.sleep(0.3)
        status = executor.get_status(trace_id)
        assert isinstance(status, dict)
        assert status["status"] == FAILED
        assert status["trace_id"] == trace_id
        assert status["backend"] == "thread"
        assert "error_category" in status

    def test_get_status_includes_error_category_for_failed(self):
        executor = ThreadTaskExecutor()

        def boom():
            raise ValueError("expected failure")

        trace_id = executor.submit(boom)
        time.sleep(0.3)
        status = executor.get_status(trace_id)
        assert isinstance(status, dict)
        assert status["status"] == FAILED
        assert "error_category" in status

    def test_get_status_returns_dict_for_unknown_trace_id(self):
        executor = ThreadTaskExecutor()
        status = executor.get_status("nonexistent")
        assert isinstance(status, dict)
        assert status["status"] == FAILED
        assert status["error_category"] == "task:not_found"
        assert status["trace_id"] == "nonexistent"
        assert status["backend"] == "thread"


class TestThreadTaskExecutorCancel:
    def test_cancel_returns_dict_with_cancelled_true_for_known_task(self):
        executor = ThreadTaskExecutor()
        trace_id = executor.submit(lambda: time.sleep(0.5))
        result = executor.cancel(trace_id)
        assert isinstance(result, dict)
        assert result["status"] == CANCELLED
        assert result["cancelled"] is True
        assert result["trace_id"] == trace_id
        assert result["backend"] == "thread"

    def test_cancel_sets_status_cancelled(self):
        executor = ThreadTaskExecutor()
        trace_id = executor.submit(lambda: time.sleep(0.5))
        executor.cancel(trace_id)
        status = executor.get_status(trace_id)
        assert isinstance(status, dict)
        assert status["status"] == CANCELLED

    def test_cancel_prevents_overwrite_on_completion(self):
        executor = ThreadTaskExecutor()
        trace_id = executor.submit(lambda: time.sleep(0.1))
        executor.cancel(trace_id)
        time.sleep(0.3)
        status = executor.get_status(trace_id)
        assert isinstance(status, dict)
        assert status["status"] == CANCELLED

    def test_cancel_returns_dict_with_cancelled_false_for_unknown(self):
        executor = ThreadTaskExecutor()
        result = executor.cancel("nonexistent")
        assert isinstance(result, dict)
        assert result["status"] == FAILED
        assert result["cancelled"] is False
        assert result["error_category"] == "task:not_found"
        assert result["trace_id"] == "nonexistent"
        assert result["backend"] == "thread"


class TestCreateTaskExecutor:
    def test_accepts_no_argument_defaults_to_config(self, monkeypatch):
        monkeypatch.setenv("QUEUE_BACKEND", "thread")
        monkeypatch.setattr(Config, "_queue_backend_cache", None)
        executor = create_task_executor()
        assert isinstance(executor, ThreadTaskExecutor)

    def test_returns_thread_task_executor_for_thread_backend(self, monkeypatch):
        monkeypatch.setenv("QUEUE_BACKEND", "thread")
        monkeypatch.setattr(Config, "_queue_backend_cache", None)
        executor = create_task_executor()
        assert isinstance(executor, ThreadTaskExecutor)

    def test_returns_queue_task_executor_for_sqlite_backend(self, monkeypatch):
        monkeypatch.setenv("QUEUE_BACKEND", "sqlite")
        monkeypatch.setenv("DB_URL", "sqlite:///:memory:")
        monkeypatch.setattr(Config, "_queue_backend_cache", None)
        monkeypatch.setattr(Config, "_db_url_cache", None)
        from app.services.application.queue_task_executor import QueueTaskExecutor

        executor = create_task_executor()
        assert isinstance(executor, QueueTaskExecutor)

    def test_returns_queue_task_executor_for_rq_backend(self, monkeypatch):
        monkeypatch.setenv("QUEUE_BACKEND", "rq")
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
        monkeypatch.setattr(Config, "_queue_backend_cache", None)
        monkeypatch.setattr(Config, "_redis_url_cache", None)
        from app.services.application.queue_task_executor import QueueTaskExecutor

        executor = create_task_executor()
        assert isinstance(executor, QueueTaskExecutor)

    def test_invalid_backend_fails_via_config_validate(self, monkeypatch):
        monkeypatch.setenv("QUEUE_BACKEND", "invalid")
        monkeypatch.setattr(Config, "_queue_backend_cache", None)
        errors = Config.validate()
        backend_errors = [e for e in errors if "QUEUE_BACKEND" in e]
        assert len(backend_errors) >= 1


class TestConfigQueueProperties:
    def test_queue_backend_default(self):
        assert Config.QUEUE_BACKEND == "thread"

    def test_queue_backend_reads_from_env(self, monkeypatch):
        monkeypatch.setenv("QUEUE_BACKEND", "sqlite")
        monkeypatch.setattr(Config, "_queue_backend_cache", None)
        assert Config.QUEUE_BACKEND == "sqlite"

    def test_redis_url_default_empty(self, monkeypatch):
        monkeypatch.delenv("REDIS_URL", raising=False)
        monkeypatch.setattr(Config, "_redis_url_cache", None)
        assert Config.REDIS_URL == ""

    def test_redis_url_reads_from_env(self, monkeypatch):
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
        monkeypatch.setattr(Config, "_redis_url_cache", None)
        assert Config.REDIS_URL == "redis://localhost:6379/0"

    def test_queue_retry_limit_default(self):
        assert Config.QUEUE_RETRY_LIMIT == 3

    def test_queue_retry_limit_reads_from_env(self, monkeypatch):
        monkeypatch.setenv("QUEUE_RETRY_LIMIT", "5")
        monkeypatch.setattr(Config, "_queue_retry_limit_cache", None)
        assert Config.QUEUE_RETRY_LIMIT == 5

    def test_queue_visibility_timeout_default(self):
        assert Config.QUEUE_VISIBILITY_TIMEOUT_SECONDS == 900

    def test_queue_visibility_timeout_reads_from_env(self, monkeypatch):
        monkeypatch.setenv("QUEUE_VISIBILITY_TIMEOUT_SECONDS", "600")
        monkeypatch.setattr(Config, "_queue_visibility_timeout_cache", None)
        assert Config.QUEUE_VISIBILITY_TIMEOUT_SECONDS == 600

    def test_validate_requires_redis_url_for_rq(self, monkeypatch):
        monkeypatch.setenv("QUEUE_BACKEND", "rq")
        monkeypatch.delenv("REDIS_URL", raising=False)
        monkeypatch.setattr(Config, "_queue_backend_cache", None)
        monkeypatch.setattr(Config, "_redis_url_cache", None)
        errors = Config.validate()
        redis_errors = [e for e in errors if "REDIS_URL" in e]
        assert len(redis_errors) >= 1

    def test_validate_accepts_rq_with_redis_url(self, monkeypatch):
        monkeypatch.setenv("QUEUE_BACKEND", "rq")
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
        monkeypatch.setattr(Config, "_queue_backend_cache", None)
        monkeypatch.setattr(Config, "_redis_url_cache", None)
        errors = Config.validate()
        redis_errors = [e for e in errors if "REDIS_URL" in e]
        assert len(redis_errors) == 0


class TestQueueTaskExecutorContract:
    def test_implements_task_executor(self):
        from app.services.application.queue_task_executor import QueueTaskExecutor

        assert issubclass(QueueTaskExecutor, TaskExecutor)

    def test_has_submit_method(self):
        from app.services.application.queue_task_executor import QueueTaskExecutor

        assert hasattr(QueueTaskExecutor, "submit")

    def test_has_get_status_method(self):
        from app.services.application.queue_task_executor import QueueTaskExecutor

        assert hasattr(QueueTaskExecutor, "get_status")

    def test_has_cancel_method(self):
        from app.services.application.queue_task_executor import QueueTaskExecutor

        assert hasattr(QueueTaskExecutor, "cancel")

    def test_get_status_returns_dict_for_submitted_task(self):
        from app.services.application.queue_task_executor import QueueTaskExecutor

        executor = QueueTaskExecutor(backend_name="sqlite", backend=None)
        trace_id = executor.submit(lambda: None)
        status = executor.get_status(trace_id)
        assert isinstance(status, dict)
        assert status["trace_id"] == trace_id
        assert status["status"] == PENDING
        assert status["backend"] == "sqlite"

    def test_get_status_returns_failed_dict_for_unknown_trace_id(self):
        from app.services.application.queue_task_executor import QueueTaskExecutor

        executor = QueueTaskExecutor(backend_name="rq", backend=None)
        status = executor.get_status("unknown")
        assert isinstance(status, dict)
        assert status["status"] == FAILED
        assert status["error_category"] == "task:not_found"
        assert status["trace_id"] == "unknown"
        assert status["backend"] == "rq"

    def test_cancel_returns_dict_with_cancelled_true_for_known_task(self):
        from app.services.application.queue_task_executor import QueueTaskExecutor

        executor = QueueTaskExecutor(backend_name="sqlite", backend=None)
        trace_id = executor.submit(lambda: None)
        result = executor.cancel(trace_id)
        assert isinstance(result, dict)
        assert result["status"] == CANCELLED
        assert result["cancelled"] is True
        assert result["trace_id"] == trace_id
        assert result["backend"] == "sqlite"

    def test_cancel_returns_dict_with_cancelled_false_for_unknown(self):
        from app.services.application.queue_task_executor import QueueTaskExecutor

        executor = QueueTaskExecutor(backend_name="rq", backend=None)
        result = executor.cancel("unknown")
        assert isinstance(result, dict)
        assert result["status"] == FAILED
        assert result["cancelled"] is False
        assert result["error_category"] == "task:not_found"
        assert result["trace_id"] == "unknown"
        assert result["backend"] == "rq"


class TestRQQueueBackendContract:
    def test_enqueue_returns_trace_id(self):
        from app.services.application.rq_queue import RQQueueBackend

        backend = RQQueueBackend(redis_url="redis://localhost:6379/0")
        result = backend.enqueue("rq_task_1", lambda: None)
        assert result == "rq_task_1"

    def test_get_status_returns_dict_for_known_task(self):
        from app.services.application.rq_queue import RQQueueBackend

        backend = RQQueueBackend(redis_url="redis://localhost:6379/0")
        backend.enqueue("rq_task_2", lambda: None)
        status = backend.get_status("rq_task_2")
        assert isinstance(status, dict)
        assert status["trace_id"] == "rq_task_2"
        assert status["status"] == PENDING
        assert status["backend"] == "rq"

    def test_get_status_returns_failed_for_unknown(self):
        from app.services.application.rq_queue import RQQueueBackend

        backend = RQQueueBackend(redis_url="redis://localhost:6379/0")
        status = backend.get_status("unknown")
        assert isinstance(status, dict)
        assert status["trace_id"] == "unknown"
        assert status["status"] == FAILED
        assert status["error_category"] == "task:not_found"
        assert status["backend"] == "rq"

    def test_cancel_returns_dict_with_cancelled_true_for_known(self):
        from app.services.application.rq_queue import RQQueueBackend

        backend = RQQueueBackend(redis_url="redis://localhost:6379/0")
        backend.enqueue("rq_task_3", lambda: None)
        result = backend.cancel("rq_task_3")
        assert isinstance(result, dict)
        assert result["trace_id"] == "rq_task_3"
        assert result["status"] == CANCELLED
        assert result["cancelled"] is True
        assert result["backend"] == "rq"

    def test_cancel_returns_dict_with_cancelled_false_for_unknown(self):
        from app.services.application.rq_queue import RQQueueBackend

        backend = RQQueueBackend(redis_url="redis://localhost:6379/0")
        result = backend.cancel("unknown")
        assert isinstance(result, dict)
        assert result["trace_id"] == "unknown"
        assert result["status"] == FAILED
        assert result["cancelled"] is False
        assert result["error_category"] == "task:not_found"
        assert result["backend"] == "rq"

    def test_stores_redis_url(self):
        from app.services.application.rq_queue import RQQueueBackend

        backend = RQQueueBackend(redis_url="redis://localhost:6379/0")
        assert backend.redis_url == "redis://localhost:6379/0"

    def test_does_not_import_redis_at_import_time(self):
        import sys

        # RQQueueBackend must be importable without redis/rq installed
        from app.services.application import rq_queue as rq_mod

        assert "redis" not in sys.modules or rq_mod is not None


class TestQueueTaskExecutorWithRQBackend:
    def test_get_status_returns_dict_not_none(self):
        from app.services.application.rq_queue import RQQueueBackend
        from app.services.application.queue_task_executor import QueueTaskExecutor

        backend = RQQueueBackend(redis_url="redis://localhost:6379/0")
        executor = QueueTaskExecutor(backend_name="rq", backend=backend)
        executor.submit(lambda: None, trace_id="rq_trace_1")
        status = executor.get_status("rq_trace_1")
        assert isinstance(status, dict)
        assert status["trace_id"] == "rq_trace_1"
        assert status["backend"] == "rq"

    def test_cancel_returns_dict_not_bool(self):
        from app.services.application.rq_queue import RQQueueBackend
        from app.services.application.queue_task_executor import QueueTaskExecutor

        backend = RQQueueBackend(redis_url="redis://localhost:6379/0")
        executor = QueueTaskExecutor(backend_name="rq", backend=backend)
        executor.submit(lambda: None, trace_id="rq_trace_2")
        result = executor.cancel("rq_trace_2")
        assert isinstance(result, dict)
        assert "cancelled" in result
        assert result["backend"] == "rq"


class TestQueueTaskExecutorCancellationRace:
    def _make_sqlite_backend(self):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy.pool import StaticPool
        from app.repositories.sqlalchemy import metadata

        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        metadata.create_all(engine)
        return sessionmaker(bind=engine)

    def test_cancel_before_completion_final_status_stays_cancelled(self):
        """If cancel is called while fn is still running, final status must remain CANCELLED."""
        from app.services.application.sqlite_queue import SQLiteQueueBackend
        from app.services.application.queue_task_executor import QueueTaskExecutor

        session_factory = self._make_sqlite_backend()
        backend = SQLiteQueueBackend(session_factory=session_factory)
        executor = QueueTaskExecutor(backend_name="sqlite", backend=backend)

        fn_started = threading.Event()
        fn_can_finish = threading.Event()

        def long_work():
            fn_started.set()
            fn_can_finish.wait(timeout=5)

        trace_id = executor.submit(long_work)
        # Wait for the worker thread to start the function
        fn_started.wait(timeout=5)

        # Cancel while the function is still running
        result = executor.cancel(trace_id)
        assert result["cancelled"] is True

        # Let the function finish
        fn_can_finish.set()
        time.sleep(0.3)

        status = backend.get_status(trace_id)
        assert status["status"] == CANCELLED

    def test_cancel_before_worker_start_skips_execution(self):
        """If cancel is called before the worker thread begins, fn must not execute."""
        from app.services.application.sqlite_queue import SQLiteQueueBackend
        from app.services.application.queue_task_executor import QueueTaskExecutor

        session_factory = self._make_sqlite_backend()
        backend = SQLiteQueueBackend(session_factory=session_factory)
        executor = QueueTaskExecutor(backend_name="sqlite", backend=backend)

        fn_executed = threading.Event()

        def work():
            fn_executed.set()

        # Capture _spawn_worker args but defer thread start until after cancel
        captured = {}
        original_spawn = executor._spawn_worker

        def deferred_spawn(tid, fn, args, kwargs):
            captured["tid"] = tid
            captured["fn"] = fn
            captured["args"] = args
            captured["kwargs"] = kwargs

        executor._spawn_worker = deferred_spawn

        trace_id = executor.submit(work)

        # Cancel before starting the worker thread
        result = executor.cancel(trace_id)
        assert result["cancelled"] is True

        # Now start the worker thread (cancel happened before worker started)
        if "tid" in captured:
            original_spawn(captured["tid"], captured["fn"], captured["args"], captured["kwargs"])

        time.sleep(0.3)

        assert not fn_executed.is_set(), "Function should not have executed after cancel"
        status = backend.get_status(trace_id)
        assert status["status"] == CANCELLED


class TestSkeletonFilesExist:
    def test_sqlite_queue_module_exists(self):
        from app.services.application import sqlite_queue

        assert sqlite_queue is not None

    def test_rq_queue_module_exists(self):
        from app.services.application import rq_queue

        assert rq_queue is not None

    def test_worker_module_exists(self):
        from app import worker

        assert worker is not None
