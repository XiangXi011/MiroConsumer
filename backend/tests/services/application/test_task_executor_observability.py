"""Tests for task-executor observability improvements."""

import threading
import time
import warnings

import pytest

from app.contracts.errors import NotFoundError, ValidationError
from app.services.application.task_executor import ThreadTaskExecutor, _categorize_error


class TestCategorizeError:
    def test_canonical_not_found(self):
        exc = NotFoundError("sim missing")
        assert _categorize_error(exc) == "canonical:not_found"

    def test_canonical_validation(self):
        exc = ValidationError("bad input")
        assert _categorize_error(exc) == "canonical:validation_error"

    def test_plain_value_error(self):
        exc = ValueError("something wrong")
        assert _categorize_error(exc) == "biz:validation"

    def test_generic_exception(self):
        exc = RuntimeError("boom")
        assert _categorize_error(exc) == "uncategorized:RuntimeError"


class TestThreadTaskExecutorObservability:
    def test_submit_returns_trace_id(self):
        executor = ThreadTaskExecutor()
        trace_id = executor.submit(lambda: None)
        assert trace_id.startswith("trace_")
        assert len(trace_id) == 18  # "trace_" + 12 hex chars

    def test_submit_accepts_custom_trace_id(self):
        executor = ThreadTaskExecutor()
        trace_id = executor.submit(lambda: None, trace_id="custom_123")
        assert trace_id == "custom_123"

    def test_submitted_work_runs_in_background(self):
        executor = ThreadTaskExecutor()
        result = {"ran": False}

        def mark():
            result["ran"] = True

        executor.submit(mark)
        time.sleep(0.1)
        assert result["ran"] is True

    def test_exception_in_background_does_not_crash(self):
        executor = ThreadTaskExecutor()

        def boom():
            raise ValueError("expected failure")

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            executor.submit(boom)
            time.sleep(0.1)

        unhandled = [
            x for x in w if "UnhandledThreadExceptionWarning" in x.message.__class__.__name__
        ]
        assert len(unhandled) == 0, "Background exception should not emit unhandled-thread warning"

    def test_trace_id_propagated_to_report_app_service(self, monkeypatch):
        from app.services.application.report_app_service import ReportAppService

        captured = {}

        class TracingExecutor:
            def submit(self, fn, *args, trace_id=None, **kwargs):
                captured["trace_id"] = trace_id
                # Run synchronously so we can assert without waiting
                fn(*args, **kwargs)
                return trace_id or "trace_fallback"

        # Minimal stubs so generate_report reaches the executor.submit call
        from unittest.mock import MagicMock

        fake_state = MagicMock()
        fake_state.project_id = "proj_1"
        fake_state.graph_id = "g1"

        fake_project = MagicMock()
        fake_project.graph_id = "g1"
        fake_project.simulation_requirement = "test req"
        fake_project.project_type = "default"

        monkeypatch.setattr(
            ReportAppService._simulation_repo, "get_simulation", lambda sid: fake_state
        )
        monkeypatch.setattr(
            ReportAppService._project_repo, "get_project", lambda pid: fake_project
        )
        monkeypatch.setattr(
            ReportAppService._report_repo, "get_report_by_simulation", lambda sid: None
        )

        # Patch task manager to avoid DB
        class FakeTaskManager:
            def create_task(self, **kw):
                return "task_123"

            def update_task(self, *a, **kw):
                pass

            def complete_task(self, *a, **kw):
                pass

            def fail_task(self, *a, **kw):
                pass

        monkeypatch.setattr(
            "app.services.application.report_app_service.TaskManager", FakeTaskManager
        )

        # Patch agent to avoid heavy work
        class FakeAgent:
            def generate_report(self, **kw):
                from app.services.report_agent import ReportStatus

                class FakeReport:
                    status = ReportStatus.COMPLETED
                    report_id = "report_123"
                    error = None

                return FakeReport()

        monkeypatch.setattr(
            "app.services.application.report_app_service.ReportAgent", lambda **kw: FakeAgent()
        )

        original_executor = ReportAppService._executor
        try:
            ReportAppService._executor = TracingExecutor()
            result = ReportAppService.generate_report("sim_1")
            assert result["status"] == "generating"
            assert "trace_id" in captured
            assert captured["trace_id"].startswith("report_")
        finally:
            ReportAppService._executor = original_executor
