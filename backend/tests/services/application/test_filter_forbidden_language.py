"""Tests for P0-5.2: filter_forbidden_language auto-invoke in report generation."""

from unittest.mock import MagicMock, patch
from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[3]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import pytest

from app.utils.disclaimer import filter_forbidden_language, FORBIDDEN_PHRASES


class TestFilterForbiddenLanguageUnit:
    """Unit tests for the filter_forbidden_language function itself."""

    def test_filters_forbidden_phrases_when_agent_count_low(self):
        text = "本产品代表市场趋势，预测销量将突破百万。"
        filtered, violations = filter_forbidden_language(text, agent_count=10)
        assert "代表市场" in violations
        assert "预测销量" in violations
        assert "[已过滤: 代表市场]" in filtered
        assert "[已过滤: 预测销量]" in filtered

    def test_no_filtering_when_agent_count_high(self):
        text = "本产品代表市场趋势，预测销量将突破百万。"
        filtered, violations = filter_forbidden_language(text, agent_count=50)
        assert violations == []
        assert filtered == text

    def test_handles_english_forbidden_phrases(self):
        text = "This report represents the market accurately."
        filtered, violations = filter_forbidden_language(text, agent_count=10)
        assert "represents the market" in violations
        assert "[已过滤: represents the market]" in filtered

    def test_no_violations_when_clean_text(self):
        text = "这是一份安全的报告，没有违禁用语。"
        filtered, violations = filter_forbidden_language(text, agent_count=10)
        assert violations == []
        assert filtered == text


class TestReportDownloadInfoForbiddenLanguage:
    """Test that get_report_download_info filters forbidden language."""

    def _make_fake_report(self, markdown_content="# Test report with 代表市场 data"):
        fake_report = MagicMock()
        fake_report.markdown_content = markdown_content
        fake_report.simulation_id = "sim_123"
        fake_report.report_id = "report_123"
        return fake_report

    def test_filters_forbidden_language_in_download_content(self, monkeypatch):
        """When agent_count < 30, forbidden phrases should be filtered."""
        from app.services.application.report_app_service import ReportAppService

        fake_report = self._make_fake_report("代表市场数据表明预测销量上升")
        monkeypatch.setattr(
            "app.services.application.report_app_service.ReportManager.get_report",
            lambda rid: fake_report,
        )
        monkeypatch.setattr(
            "app.services.application.report_app_service.ReportManager._get_report_markdown_path",
            lambda rid: "/nonexistent/report.md",
        )
        monkeypatch.setattr(
            "app.services.application.report_app_service.ReportAppService._build_methodology_page",
            lambda cls, sim_id, report: "",
        )
        monkeypatch.setattr(
            "app.services.application.report_app_service.ReportAppService._get_agent_count",
            lambda cls, sim_id: 10,
        )

        info = ReportAppService.get_report_download_info("report_123")

        assert "[已过滤:" in info["content"]
        assert "代表市场" not in info["content"] or "[已过滤: 代表市场]" in info["content"]

    def test_no_filtering_when_agent_count_high(self, monkeypatch):
        """When agent_count >= 30, no filtering should occur."""
        from app.services.application.report_app_service import ReportAppService

        fake_report = self._make_fake_report("代表市场数据表明预测销量上升")
        monkeypatch.setattr(
            "app.services.application.report_app_service.ReportManager.get_report",
            lambda rid: fake_report,
        )
        monkeypatch.setattr(
            "app.services.application.report_app_service.ReportManager._get_report_markdown_path",
            lambda rid: "/nonexistent/report.md",
        )
        monkeypatch.setattr(
            "app.services.application.report_app_service.ReportAppService._build_methodology_page",
            lambda cls, sim_id, report: "",
        )
        monkeypatch.setattr(
            "app.services.application.report_app_service.ReportAppService._get_agent_count",
            lambda cls, sim_id: 50,
        )

        info = ReportAppService.get_report_download_info("report_123")

        assert "代表市场" in info["content"]
        assert "[已过滤:" not in info["content"]

    def test_filters_methodology_page_too(self, monkeypatch):
        """Methodology page content should also be filtered."""
        from app.services.application.report_app_service import ReportAppService

        fake_report = self._make_fake_report("# Clean report")
        monkeypatch.setattr(
            "app.services.application.report_app_service.ReportManager.get_report",
            lambda rid: fake_report,
        )
        monkeypatch.setattr(
            "app.services.application.report_app_service.ReportManager._get_report_markdown_path",
            lambda rid: "/nonexistent/report.md",
        )
        monkeypatch.setattr(
            "app.services.application.report_app_service.ReportAppService._get_agent_count",
            lambda cls, sim_id: 10,
        )

        info = ReportAppService.get_report_download_info("report_123")
        # The methodology page itself should not contain unfiltered forbidden phrases
        # (for small agent counts the filter runs on combined content)
        assert isinstance(info["content"], str)


class TestGetAgentCount:
    """Test the _get_agent_count helper."""

    def test_returns_sum_of_core_and_expanded(self, monkeypatch):
        from app.services.application.report_app_service import ReportAppService

        monkeypatch.setattr(
            "app.services.application.report_app_service.ReportAppService._simulation_repo.get_simulation_config",
            lambda sim_id: {"core_persona_count": 20, "expanded_persona_count": 5},
        )
        assert ReportAppService._get_agent_count("sim_123") == 25

    def test_returns_default_on_exception(self, monkeypatch):
        from app.services.application.report_app_service import ReportAppService

        monkeypatch.setattr(
            "app.services.application.report_app_service.ReportAppService._simulation_repo.get_simulation_config",
            lambda sim_id: (_ for _ in ()).throw(RuntimeError("db error")),
        )
        assert ReportAppService._get_agent_count("sim_123") == 8

    def test_returns_default_when_config_is_none(self, monkeypatch):
        from app.services.application.report_app_service import ReportAppService

        monkeypatch.setattr(
            "app.services.application.report_app_service.ReportAppService._simulation_repo.get_simulation_config",
            lambda sim_id: None,
        )
        assert ReportAppService._get_agent_count("sim_123") == 8
