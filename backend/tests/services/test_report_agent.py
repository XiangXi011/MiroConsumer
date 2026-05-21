"""Tests for report_agent core logic."""

from __future__ import annotations

import json
import os
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from app.services.report_agent import (
    Report,
    ReportLogger,
    ReportOutline,
    ReportSection,
    ReportStatus,
    ReportAgent,
)


class TestReportStatus:
    """Test ReportStatus enum."""

    def test_status_values(self):
        """ReportStatus has expected values."""
        assert ReportStatus.PENDING == "pending"
        assert ReportStatus.PLANNING == "planning"
        assert ReportStatus.GENERATING == "generating"
        assert ReportStatus.COMPLETED == "completed"
        assert ReportStatus.FAILED == "failed"


class TestReportSection:
    """Test ReportSection dataclass."""

    def test_to_dict(self):
        """Section serializes to dict correctly."""
        section = ReportSection(title="Test Section", content="Test content")
        d = section.to_dict()
        assert d["title"] == "Test Section"
        assert d["content"] == "Test content"

    def test_to_markdown(self):
        """Section converts to markdown correctly."""
        section = ReportSection(title="Test", content="Content here.")
        md = section.to_markdown()
        assert "## Test" in md
        assert "Content here." in md

    def test_empty_content(self):
        """Section with empty content still produces valid markdown."""
        section = ReportSection(title="Empty")
        md = section.to_markdown()
        assert "## Empty" in md


class TestReportOutline:
    """Test ReportOutline dataclass."""

    def test_to_dict(self):
        """Outline serializes to dict correctly."""
        outline = ReportOutline(
            title="Report Title",
            summary="A summary",
            sections=[
                ReportSection(title="Section 1"),
                ReportSection(title="Section 2"),
            ],
        )
        d = outline.to_dict()
        assert d["title"] == "Report Title"
        assert d["summary"] == "A summary"
        assert len(d["sections"]) == 2

    def test_to_markdown(self):
        """Outline converts to markdown correctly."""
        outline = ReportOutline(
            title="Title",
            summary="Summary",
            sections=[ReportSection(title="Sec1", content="Content")],
        )
        md = outline.to_markdown()
        assert "# Title" in md
        assert "> Summary" in md
        assert "## Sec1" in md
        assert "Content" in md

    def test_empty_sections(self):
        """Outline with no sections is valid."""
        outline = ReportOutline(title="T", summary="S", sections=[])
        d = outline.to_dict()
        assert d["sections"] == []


class TestReport:
    """Test Report dataclass."""

    def test_to_dict(self):
        """Report serializes to dict correctly."""
        report = Report(
            report_id="r_123",
            simulation_id="sim_123",
            graph_id="g_123",
            simulation_requirement="Test requirement",
            status=ReportStatus.PENDING,
            project_type="default",
        )
        d = report.to_dict()
        assert d["report_id"] == "r_123"
        assert d["simulation_id"] == "sim_123"
        assert d["graph_id"] == "g_123"
        assert d["status"] == "pending"
        assert d["project_type"] == "default"

    def test_with_outline(self):
        """Report with outline serializes correctly."""
        outline = ReportOutline(
            title="T",
            summary="S",
            sections=[ReportSection(title="S1")],
        )
        report = Report(
            report_id="r_1",
            simulation_id="s_1",
            graph_id="g_1",
            simulation_requirement="req",
            status=ReportStatus.COMPLETED,
            outline=outline,
        )
        d = report.to_dict()
        assert d["outline"] is not None
        assert d["outline"]["title"] == "T"

    def test_defaults(self):
        """Report has correct default values."""
        report = Report(
            report_id="r1",
            simulation_id="s1",
            graph_id="g1",
            simulation_requirement="req",
            status=ReportStatus.PENDING,
        )
        assert report.markdown_content == ""
        assert report.error is None


class TestReportLogger:
    """Test ReportLogger."""

    def test_init(self, tmp_path, monkeypatch):
        """Logger initializes and creates log directory."""
        monkeypatch.setattr(
            "app.services.report_agent.Config.UPLOAD_FOLDER", str(tmp_path)
        )
        logger = ReportLogger("report_123")
        assert logger.report_id == "report_123"
        assert os.path.isdir(os.path.join(str(tmp_path), "reports", "report_123"))

    def test_log(self, tmp_path, monkeypatch):
        """Log writes to file correctly."""
        monkeypatch.setattr(
            "app.services.report_agent.Config.UPLOAD_FOLDER", str(tmp_path)
        )
        logger = ReportLogger("report_456")
        logger.log(action="test", stage="testing", details={"key": "value"})

        log_path = os.path.join(
            str(tmp_path), "reports", "report_456", "agent_log.jsonl"
        )
        assert os.path.exists(log_path)
        with open(log_path, "r", encoding="utf-8") as f:
            entry = json.loads(f.readline())
        assert entry["action"] == "test"
        assert entry["stage"] == "testing"
        assert entry["details"]["key"] == "value"

    def test_log_start(self, tmp_path, monkeypatch):
        """log_start records report start."""
        monkeypatch.setattr(
            "app.services.report_agent.Config.UPLOAD_FOLDER", str(tmp_path)
        )
        logger = ReportLogger("report_start")
        logger.log_start("sim_1", "g_1", "requirement text")

        log_path = os.path.join(
            str(tmp_path), "reports", "report_start", "agent_log.jsonl"
        )
        with open(log_path, "r", encoding="utf-8") as f:
            entry = json.loads(f.readline())
        assert entry["action"] == "report_start"
        assert entry["details"]["simulation_id"] == "sim_1"

    def test_log_planning_start(self, tmp_path, monkeypatch):
        """log_planning_start records planning phase."""
        monkeypatch.setattr(
            "app.services.report_agent.Config.UPLOAD_FOLDER", str(tmp_path)
        )
        logger = ReportLogger("report_plan")
        logger.log_planning_start()

        log_path = os.path.join(
            str(tmp_path), "reports", "report_plan", "agent_log.jsonl"
        )
        with open(log_path, "r", encoding="utf-8") as f:
            entry = json.loads(f.readline())
        assert entry["action"] == "planning_start"
        assert entry["stage"] == "planning"

    def test_log_section_start(self, tmp_path, monkeypatch):
        """log_section_start records section generation."""
        monkeypatch.setattr(
            "app.services.report_agent.Config.UPLOAD_FOLDER", str(tmp_path)
        )
        logger = ReportLogger("report_sec")
        logger.log_section_start("Intro", 1)

        log_path = os.path.join(
            str(tmp_path), "reports", "report_sec", "agent_log.jsonl"
        )
        with open(log_path, "r", encoding="utf-8") as f:
            entry = json.loads(f.readline())
        assert entry["action"] == "section_start"
        assert entry["section_title"] == "Intro"
        assert entry["section_index"] == 1

    def test_log_error(self, tmp_path, monkeypatch):
        """log_error records error correctly."""
        monkeypatch.setattr(
            "app.services.report_agent.Config.UPLOAD_FOLDER", str(tmp_path)
        )
        logger = ReportLogger("report_err")
        logger.log_error("Something failed", stage="generating", section_title="Intro")

        log_path = os.path.join(
            str(tmp_path), "reports", "report_err", "agent_log.jsonl"
        )
        with open(log_path, "r", encoding="utf-8") as f:
            entry = json.loads(f.readline())
        assert entry["action"] == "error"
        assert entry["details"]["error"] == "Something failed"


class TestReportAgentTools:
    """Test ReportAgent tool definitions."""

    def test_tool_names(self):
        """Agent defines expected tools."""
        with patch("app.services.report_agent.LLMClient") as mock_llm, patch(
            "app.services.report_agent.ZepToolsService"
        ) as mock_zep:
            mock_llm_instance = MagicMock()
            mock_llm.return_value = mock_llm_instance
            mock_zep_instance = MagicMock()
            mock_zep.return_value = mock_zep_instance

            agent = ReportAgent(
                graph_id="g1",
                simulation_id="s1",
                simulation_requirement="test",
            )
            tool_names = set(agent.tools.keys())
            assert "insight_forge" in tool_names
            assert "panorama_search" in tool_names
            assert "quick_search" in tool_names
            assert "interview_agents" in tool_names

    def test_valid_tool_names_set(self):
        """VALID_TOOL_NAMES contains expected entries."""
        expected = {"insight_forge", "panorama_search", "quick_search", "interview_agents"}
        with patch("app.services.report_agent.LLMClient") as mock_llm, patch(
            "app.services.report_agent.ZepToolsService"
        ) as mock_zep:
            mock_llm.return_value = MagicMock()
            mock_zep.return_value = MagicMock()
            agent = ReportAgent(
                graph_id="g1",
                simulation_id="s1",
                simulation_requirement="test",
            )
            assert agent.VALID_TOOL_NAMES == expected

    def test_parse_tool_calls_empty(self):
        """Parsing empty response returns empty list."""
        with patch("app.services.report_agent.LLMClient") as mock_llm, patch(
            "app.services.report_agent.ZepToolsService"
        ) as mock_zep:
            mock_llm.return_value = MagicMock()
            mock_zep.return_value = MagicMock()
            agent = ReportAgent(
                graph_id="g1",
                simulation_id="s1",
                simulation_requirement="test",
            )
            calls = agent._parse_tool_calls("")
            assert calls == []

    def test_parse_tool_calls_xml_format(self):
        """Parsing XML-style tool calls."""
        with patch("app.services.report_agent.LLMClient") as mock_llm, patch(
            "app.services.report_agent.ZepToolsService"
        ) as mock_zep:
            mock_llm.return_value = MagicMock()
            mock_zep.return_value = MagicMock()
            agent = ReportAgent(
                graph_id="g1",
                simulation_id="s1",
                simulation_requirement="test",
            )
            response = '<tool_call>{"name": "quick_search", "parameters": {"query": "test"}}</tool_call>'
            calls = agent._parse_tool_calls(response)
            assert len(calls) == 1
            assert calls[0]["name"] == "quick_search"

    def test_is_valid_tool_call(self):
        """Valid tool call detection."""
        with patch("app.services.report_agent.LLMClient") as mock_llm, patch(
            "app.services.report_agent.ZepToolsService"
        ) as mock_zep:
            mock_llm.return_value = MagicMock()
            mock_zep.return_value = MagicMock()
            agent = ReportAgent(
                graph_id="g1",
                simulation_id="s1",
                simulation_requirement="test",
            )
            assert agent._is_valid_tool_call({"name": "quick_search", "parameters": {}}) is True
            assert agent._is_valid_tool_call({"name": "unknown_tool", "parameters": {}}) is False
            assert agent._is_valid_tool_call({}) is False

    def test_get_tools_description(self):
        """Tools description is non-empty string."""
        with patch("app.services.report_agent.LLMClient") as mock_llm, patch(
            "app.services.report_agent.ZepToolsService"
        ) as mock_zep:
            mock_llm.return_value = MagicMock()
            mock_zep.return_value = MagicMock()
            agent = ReportAgent(
                graph_id="g1",
                simulation_id="s1",
                simulation_requirement="test",
            )
            desc = agent._get_tools_description()
            assert isinstance(desc, str)
            assert len(desc) > 0
            assert "insight_forge" in desc

    def test_plan_outline_fallback(self):
        """plan_outline returns fallback on LLM error."""
        with patch("app.services.report_agent.LLMClient") as mock_llm, patch(
            "app.services.report_agent.ZepToolsService"
        ) as mock_zep:
            mock_llm_instance = MagicMock()
            mock_llm_instance.chat_json.side_effect = Exception("LLM API error")
            mock_llm.return_value = mock_llm_instance
            mock_zep_instance = MagicMock()
            mock_zep_instance.get_simulation_context.return_value = {
                "graph_statistics": {"total_nodes": 10, "total_edges": 5, "entity_types": {}},
                "total_entities": 10,
                "related_facts": [],
            }
            mock_zep.return_value = mock_zep_instance

            agent = ReportAgent(
                graph_id="g1",
                simulation_id="s1",
                simulation_requirement="test",
            )
            outline = agent.plan_outline()
            assert outline is not None
            assert len(outline.sections) == 3
