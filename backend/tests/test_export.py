"""导出工具和版本管理测试"""

import json
import pytest
from app.utils.export import export_to_json, export_metrics_to_csv, export_rounds_to_csv
from app.utils.version import get_version_info


class TestExportToJson:
    """export_to_json 测试"""

    def test_valid_json_output(self):
        """输出有效 JSON"""
        data = {"simulation_id": "sim_001", "status": "completed"}
        result = export_to_json(data)
        parsed = json.loads(result)
        assert parsed == data

    def test_chinese_characters_preserved(self):
        """中文字符直接显示，不转义"""
        data = {"name": "仿真测试"}
        result = export_to_json(data)
        assert "仿真测试" in result
        assert "\\u" not in result

    def test_pretty_print(self):
        """输出带缩进的格式化 JSON"""
        data = {"key": "value"}
        result = export_to_json(data)
        assert "\n" in result
        assert "  " in result


class TestExportMetricsToCsv:
    """export_metrics_to_csv 测试"""

    def test_header_and_data(self):
        """包含表头和数据"""
        metrics = [
            {"round": 1, "sentiment": 0.8, "engagement": 150},
            {"round": 2, "sentiment": 0.6, "engagement": 200},
        ]
        result = export_metrics_to_csv(metrics)
        lines = result.strip().split("\n")
        assert len(lines) == 3  # header + 2 rows
        assert "round" in lines[0]
        assert "sentiment" in lines[0]

    def test_empty_input(self):
        """空输入返回空字符串"""
        result = export_metrics_to_csv([])
        assert result == ""


class TestExportRoundsToCsv:
    """export_rounds_to_csv 测试"""

    def test_flatten_nested_data(self):
        """正确展平嵌套数据"""
        rounds = [
            {
                "round": 1,
                "agents": {
                    "agent_0": {"action": "post", "sentiment": 0.9},
                    "agent_1": {"action": "reply", "sentiment": 0.5},
                },
            },
            {
                "round": 2,
                "agents": {
                    "agent_0": {"action": "like", "sentiment": 0.8},
                },
            },
        ]
        result = export_rounds_to_csv(rounds)
        lines = result.strip().split("\n")
        assert len(lines) == 4  # header + 3 rows
        assert "round" in lines[0]
        assert "agent_id" in lines[0]

    def test_empty_rounds(self):
        """空轮次返回空字符串"""
        result = export_rounds_to_csv([])
        assert result == ""

    def test_rounds_with_no_agents(self):
        """没有 agents 的轮次返回空字符串"""
        rounds = [{"round": 1, "agents": {}}]
        result = export_rounds_to_csv(rounds)
        assert result == ""


class TestVersionInfo:
    """版本信息测试"""

    def test_contains_required_fields(self):
        """包含 version 和 phase"""
        info = get_version_info()
        assert "version" in info
        assert "phase" in info
        assert "api_version" in info

    def test_version_format(self):
        """版本号格式正确"""
        info = get_version_info()
        parts = info["version"].split(".")
        assert len(parts) == 3
        assert all(p.isdigit() for p in parts)
