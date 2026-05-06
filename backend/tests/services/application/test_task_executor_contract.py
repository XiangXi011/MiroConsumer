"""Phase7F CI path compatibility tests for TaskExecutor contract."""

import inspect
import threading
import time

import pytest

from app.services.application.task_executor import (
    CANCELLED,
    FAILED,
    PENDING,
    RUNNING,
    SUCCEEDED,
    TaskExecutor,
    ThreadTaskExecutor,
)


class TestTaskExecutorContract:
    """Verify the abstract TaskExecutor interface shape."""

    def test_is_abstract_base_class(self):
        assert inspect.isabstract(TaskExecutor)

    def test_has_abstract_submit(self):
        assert hasattr(TaskExecutor, "submit")
        assert getattr(TaskExecutor.submit, "__isabstractmethod__", False)

    def test_has_abstract_get_status(self):
        assert hasattr(TaskExecutor, "get_status")
        assert getattr(TaskExecutor.get_status, "__isabstractmethod__", False)

    def test_has_abstract_cancel(self):
        assert hasattr(TaskExecutor, "cancel")
        assert getattr(TaskExecutor.cancel, "__isabstractmethod__", False)

    def test_thread_executor_is_concrete_subclass(self):
        assert issubclass(ThreadTaskExecutor, TaskExecutor)
        assert not inspect.isabstract(ThreadTaskExecutor)


class TestThreadTaskExecutorStatusShape:
    """Verify ThreadTaskExecutor.get_status returns consistent dict shapes."""

    def test_get_status_pending_has_required_keys(self):
        executor = ThreadTaskExecutor()
        tid = executor.submit(lambda: time.sleep(0.5))
        status = executor.get_status(tid)
        assert isinstance(status, dict)
        assert status["trace_id"] == tid
        assert status["status"] in {PENDING, RUNNING}
        assert status["backend"] == "thread"

    def test_get_status_succeeded_has_required_keys(self):
        executor = ThreadTaskExecutor()
        tid = executor.submit(lambda: None)
        time.sleep(0.2)
        status = executor.get_status(tid)
        assert isinstance(status, dict)
        assert status["trace_id"] == tid
        assert status["status"] == SUCCEEDED
        assert status["backend"] == "thread"
        assert "error_category" not in status

    def test_get_status_failed_has_error_category(self):
        executor = ThreadTaskExecutor()

        def boom():
            raise ValueError("boom")

        tid = executor.submit(boom)
        time.sleep(0.2)
        status = executor.get_status(tid)
        assert isinstance(status, dict)
        assert status["trace_id"] == tid
        assert status["status"] == FAILED
        assert status["backend"] == "thread"
        assert "error_category" in status
        assert isinstance(status["error_category"], str)

    def test_get_status_not_found_has_error_category(self):
        executor = ThreadTaskExecutor()
        status = executor.get_status("missing_tid")
        assert isinstance(status, dict)
        assert status["trace_id"] == "missing_tid"
        assert status["status"] == FAILED
        assert status["backend"] == "thread"
        assert status["error_category"] == "task:not_found"

    def test_cancel_returns_dict_shape(self):
        executor = ThreadTaskExecutor()
        tid = executor.submit(lambda: time.sleep(0.5))
        result = executor.cancel(tid)
        assert isinstance(result, dict)
        assert result["trace_id"] == tid
        assert result["status"] == CANCELLED
        assert result["cancelled"] is True
        assert result["backend"] == "thread"

    def test_cancel_unknown_returns_dict_shape(self):
        executor = ThreadTaskExecutor()
        result = executor.cancel("missing_tid")
        assert isinstance(result, dict)
        assert result["trace_id"] == "missing_tid"
        assert result["status"] == FAILED
        assert result["cancelled"] is False
        assert result["backend"] == "thread"
        assert result["error_category"] == "task:not_found"

    def test_status_progression_pending_to_succeeded(self):
        executor = ThreadTaskExecutor()
        started = threading.Event()
        can_finish = threading.Event()

        def work():
            started.set()
            can_finish.wait(timeout=5)

        tid = executor.submit(work)
        # Wait for the worker to start so we observe an in-flight status
        started.wait(timeout=5)
        immediate = executor.get_status(tid)
        assert immediate["status"] in {PENDING, RUNNING}
        can_finish.set()
        time.sleep(0.2)
        final = executor.get_status(tid)
        assert final["status"] == SUCCEEDED

    def test_status_progression_pending_to_failed(self):
        executor = ThreadTaskExecutor()

        def work():
            raise RuntimeError("expected")

        tid = executor.submit(work)
        time.sleep(0.2)
        status = executor.get_status(tid)
        assert status["status"] == FAILED
        assert "error_category" in status
