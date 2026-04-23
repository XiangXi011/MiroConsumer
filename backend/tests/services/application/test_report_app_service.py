"""Focused regression tests for ReportAppService orchestration methods."""

from unittest.mock import MagicMock
from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[3]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import pytest

from app.contracts.errors import NotFoundError, ValidationError
from app.services.application.report_app_service import ReportAppService
from app.services.report_agent import ReportStatus
from app.utils.locale import set_locale

set_locale("en")


class TestReportAppServiceGetGenerateStatus:
    def test_returns_completed_when_simulation_has_completed_report(self, monkeypatch):
        fake_report = MagicMock()
        fake_report.status = ReportStatus.COMPLETED
        fake_report.report_id = "report_123"

        monkeypatch.setattr(
            "app.services.application.report_app_service.ReportManager.get_report_by_simulation",
            lambda sim_id: fake_report,
        )

        result = ReportAppService.get_generate_status(simulation_id="sim_123", task_id=None)

        assert result["status"] == "completed"
        assert result["progress"] == 100
        assert result["already_completed"] is True
        assert result["report_id"] == "report_123"

    def test_raises_when_neither_simulation_nor_task_provided(self):
        with pytest.raises(ValidationError):
            ReportAppService.get_generate_status(simulation_id=None, task_id=None)

    def test_returns_task_dict_when_task_exists(self, monkeypatch):
        fake_task = MagicMock()
        fake_task.to_dict.return_value = {"task_id": "task_123", "status": "processing"}

        class FakeTaskManager:
            def get_task(self, task_id):
                return fake_task

        monkeypatch.setattr(
            "app.services.application.report_app_service.TaskManager",
            FakeTaskManager,
        )
        monkeypatch.setattr(
            "app.services.application.report_app_service.ReportManager.get_report_by_simulation",
            lambda sim_id: None,
        )

        result = ReportAppService.get_generate_status(simulation_id=None, task_id="task_123")

        assert result["task_id"] == "task_123"
        assert result["status"] == "processing"

    def test_raises_when_task_not_found(self, monkeypatch):
        class FakeTaskManager:
            def get_task(self, task_id):
                return None

        monkeypatch.setattr(
            "app.services.application.report_app_service.TaskManager",
            FakeTaskManager,
        )
        monkeypatch.setattr(
            "app.services.application.report_app_service.ReportManager.get_report_by_simulation",
            lambda sim_id: None,
        )

        with pytest.raises(NotFoundError):
            ReportAppService.get_generate_status(simulation_id=None, task_id="task_missing")


class TestReportAppServiceChatWithReportAgent:
    def test_raises_when_simulation_not_found(self, monkeypatch):
        monkeypatch.setattr(
            "app.services.application.report_app_service.SimulationManager.get_simulation",
            lambda self, sim_id: None,
        )

        with pytest.raises(NotFoundError):
            ReportAppService.chat_with_report_agent(
                simulation_id="sim_missing",
                message="hello",
            )

    def test_raises_when_project_not_found(self, monkeypatch):
        fake_state = MagicMock()
        fake_state.project_id = "proj_missing"
        fake_state.graph_id = "g1"

        monkeypatch.setattr(
            "app.services.application.report_app_service.SimulationManager.get_simulation",
            lambda self, sim_id: fake_state,
        )
        monkeypatch.setattr(
            "app.services.application.report_app_service.ProjectManager.get_project",
            lambda pid: None,
        )

        with pytest.raises(NotFoundError):
            ReportAppService.chat_with_report_agent(
                simulation_id="sim_123",
                message="hello",
            )

    def test_raises_when_graph_id_missing(self, monkeypatch):
        fake_state = MagicMock()
        fake_state.project_id = "proj_123"
        fake_state.graph_id = None

        fake_project = MagicMock()
        fake_project.graph_id = None
        fake_project.simulation_requirement = ""

        monkeypatch.setattr(
            "app.services.application.report_app_service.SimulationManager.get_simulation",
            lambda self, sim_id: fake_state,
        )
        monkeypatch.setattr(
            "app.services.application.report_app_service.ProjectManager.get_project",
            lambda pid: fake_project,
        )

        with pytest.raises(ValidationError):
            ReportAppService.chat_with_report_agent(
                simulation_id="sim_123",
                message="hello",
            )

    def test_returns_agent_chat_result(self, monkeypatch):
        fake_state = MagicMock()
        fake_state.project_id = "proj_123"
        fake_state.graph_id = "g1"

        fake_project = MagicMock()
        fake_project.graph_id = "g1"
        fake_project.simulation_requirement = "test req"

        monkeypatch.setattr(
            "app.services.application.report_app_service.SimulationManager.get_simulation",
            lambda self, sim_id: fake_state,
        )
        monkeypatch.setattr(
            "app.services.application.report_app_service.ProjectManager.get_project",
            lambda pid: fake_project,
        )

        fake_agent = MagicMock()
        fake_agent.chat.return_value = {"response": "hi", "tool_calls": []}

        monkeypatch.setattr(
            "app.services.application.report_app_service.ReportAgent",
            lambda **kwargs: fake_agent,
        )

        result = ReportAppService.chat_with_report_agent(
            simulation_id="sim_123",
            message="hello",
            chat_history=[],
        )

        assert result["response"] == "hi"
        fake_agent.chat.assert_called_once_with(message="hello", chat_history=[])


class TestReportAppServiceGetReportSections:
    def test_returns_sections_and_completion_status(self, monkeypatch):
        monkeypatch.setattr(
            "app.services.application.report_app_service.ReportManager.get_generated_sections",
            lambda rid: [{"filename": "s01.md"}],
        )

        fake_report = MagicMock()
        fake_report.status = ReportStatus.COMPLETED

        monkeypatch.setattr(
            "app.services.application.report_app_service.ReportManager.get_report",
            lambda rid: fake_report,
        )

        result = ReportAppService.get_report_sections("report_123")

        assert result["report_id"] == "report_123"
        assert result["total_sections"] == 1
        assert result["is_complete"] is True

    def test_returns_not_complete_when_report_missing(self, monkeypatch):
        monkeypatch.setattr(
            "app.services.application.report_app_service.ReportManager.get_generated_sections",
            lambda rid: [],
        )
        monkeypatch.setattr(
            "app.services.application.report_app_service.ReportManager.get_report",
            lambda rid: None,
        )

        result = ReportAppService.get_report_sections("report_123")

        assert result["is_complete"] is False
        assert result["total_sections"] == 0


class TestReportAppServiceCheckReportStatus:
    def test_returns_unlocked_when_report_completed(self, monkeypatch):
        fake_report = MagicMock()
        fake_report.status = ReportStatus.COMPLETED
        fake_report.report_id = "report_123"

        monkeypatch.setattr(
            "app.services.application.report_app_service.ReportManager.get_report_by_simulation",
            lambda sim_id: fake_report,
        )

        result = ReportAppService.check_report_status("sim_123")

        assert result["has_report"] is True
        assert result["report_status"] == "completed"
        assert result["interview_unlocked"] is True

    def test_returns_locked_when_no_report(self, monkeypatch):
        monkeypatch.setattr(
            "app.services.application.report_app_service.ReportManager.get_report_by_simulation",
            lambda sim_id: None,
        )

        result = ReportAppService.check_report_status("sim_123")

        assert result["has_report"] is False
        assert result["report_status"] is None
        assert result["interview_unlocked"] is False


class TestReportAppServiceGetReportDownloadInfo:
    def test_raises_when_report_not_found(self, monkeypatch):
        monkeypatch.setattr(
            "app.services.application.report_app_service.ReportManager.get_report",
            lambda rid: None,
        )

        with pytest.raises(NotFoundError):
            ReportAppService.get_report_download_info("report_missing")

    def test_returns_path_when_markdown_exists(self, monkeypatch, tmp_path):
        fake_report = MagicMock()
        fake_report.markdown_content = "# Test"

        monkeypatch.setattr(
            "app.services.application.report_app_service.ReportManager.get_report",
            lambda rid: fake_report,
        )

        md_path = tmp_path / "report_123.md"
        md_path.write_text("# Test", encoding="utf-8")

        monkeypatch.setattr(
            "app.services.application.report_app_service.ReportManager._get_report_markdown_path",
            lambda rid: str(md_path),
        )

        info = ReportAppService.get_report_download_info("report_123")

        assert info["is_temp"] is False
        assert info["path"] == str(md_path)
        assert info["download_name"] == "report_123.md"

    def test_returns_temp_when_markdown_missing(self, monkeypatch):
        fake_report = MagicMock()
        fake_report.markdown_content = "# Test"

        monkeypatch.setattr(
            "app.services.application.report_app_service.ReportManager.get_report",
            lambda rid: fake_report,
        )
        monkeypatch.setattr(
            "app.services.application.report_app_service.ReportManager._get_report_markdown_path",
            lambda rid: "/nonexistent/report_123.md",
        )

        info = ReportAppService.get_report_download_info("report_123")

        assert info["is_temp"] is True
        assert info["content"] == "# Test"
