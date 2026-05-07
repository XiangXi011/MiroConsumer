"""Tests for methodology limits and forbidden language filtering."""

import pytest
from app.utils.disclaimer import (
    get_methodology_limits,
    filter_forbidden_language,
    FORBIDDEN_PHRASES,
)


class TestGetMethodologyLimits:
    """Test get_methodology_limits function."""

    def test_returns_random_seed_and_evidence_support(self):
        result = get_methodology_limits(
            agent_count=50, run_count=20, mode="standard",
            random_seed=42, evidence_support="partial"
        )
        assert result["random_seed"] == 42
        assert result["evidence_support"] == "partial"

    def test_default_random_seed_is_none(self):
        result = get_methodology_limits(agent_count=10, run_count=1, mode="quick")
        assert result["random_seed"] is None
        assert result["evidence_support"] == "none"

    def test_existing_fields_preserved(self):
        result = get_methodology_limits(agent_count=50, run_count=20, mode="standard")
        assert result["agent_count"] == 50
        assert result["run_count"] == 20
        assert result["simulation_mode"] == "standard"
        assert result["can_do_statistical_inference"] is True
        assert result["confidence_level"] == "medium"
        assert "display_label" in result
        assert "forbidden_language" in result
        assert "limits" in result

    def test_low_sample_forbidden_language_true(self):
        result = get_methodology_limits(agent_count=10, run_count=1, mode="quick")
        assert result["forbidden_language"] is True
        assert result["can_do_statistical_inference"] is False
        assert result["confidence_level"] == "low"

    def test_high_sample_forbidden_language_false(self):
        result = get_methodology_limits(agent_count=100, run_count=30, mode="standard")
        assert result["forbidden_language"] is False
        assert result["can_do_statistical_inference"] is True
        assert result["confidence_level"] == "high"


class TestFilterForbiddenLanguage:
    """Test filter_forbidden_language function."""

    def test_filters_when_agent_count_below_30(self):
        text = "该产品代表市场趋势，可以预测销量增长。"
        filtered, violations = filter_forbidden_language(text, agent_count=10)
        assert len(violations) > 0
        assert "代表市场" in violations
        assert "预测销量" in violations
        assert "[已过滤: 代表市场]" in filtered
        assert "[已过滤: 预测销量]" in filtered

    def test_no_filter_when_agent_count_gte_30(self):
        text = "该产品代表市场趋势，可以预测销量增长。"
        filtered, violations = filter_forbidden_language(text, agent_count=30)
        assert violations == []
        assert filtered == text

    def test_no_filter_when_agent_count_above_30(self):
        text = "统计显著的结果代表市场真实情况。"
        filtered, violations = filter_forbidden_language(text, agent_count=100)
        assert violations == []
        assert filtered == text

    def test_empty_text(self):
        filtered, violations = filter_forbidden_language("", agent_count=5)
        assert filtered == ""
        assert violations == []

    def test_no_forbidden_phrases(self):
        text = "这是一个普通的报告内容。"
        filtered, violations = filter_forbidden_language(text, agent_count=5)
        assert filtered == text
        assert violations == []

    def test_english_forbidden_phrases_filtered(self):
        text = "This result statistically significant represents the market."
        filtered, violations = filter_forbidden_language(text, agent_count=10)
        assert "statistically significant" in violations
        assert "represents the market" in violations
        assert "[已过滤: statistically significant]" in filtered
        assert "[已过滤: represents the market]" in filtered

    def test_english_phrases_not_filtered_at_high_sample(self):
        text = "This result statistically significant represents the market."
        filtered, violations = filter_forbidden_language(text, agent_count=50)
        assert violations == []
        assert filtered == text

    def test_case_insensitive_matching(self):
        text = "Statistically Significant findings."
        filtered, violations = filter_forbidden_language(text, agent_count=5)
        assert "statistically significant" in violations

    def test_multiple_violations_collected(self):
        text = "代表市场真实数据，确定性结论，100%准确。"
        filtered, violations = filter_forbidden_language(text, agent_count=5)
        assert "代表市场" in violations
        assert "确定性结论" in violations
        assert "100%准确" in violations
        assert len(violations) == 3
