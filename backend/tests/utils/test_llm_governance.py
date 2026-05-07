"""Tests for LLM output governance."""

import pytest

from app.utils.llm_governance import validate_llm_output, get_fallback_response


class TestValidateLLMOutput:
    """validate_llm_output 测试套件"""

    def test_empty_output_returns_invalid(self):
        result = validate_llm_output("")
        assert result["valid"] is False
        assert any("空内容" in i for i in result["issues"])

    def test_none_output_returns_invalid(self):
        result = validate_llm_output(None)
        assert result["valid"] is False
        assert any("空内容" in i for i in result["issues"])

    def test_whitespace_only_returns_invalid(self):
        result = validate_llm_output("   \n\t  ")
        assert result["valid"] is False

    def test_short_output_returns_invalid(self):
        result = validate_llm_output("太短了")
        assert result["valid"] is False
        assert any("过短" in i for i in result["issues"])

    def test_anti_math_pattern_detected(self):
        texts = [
            "精确计算后结果为42.5%",
            "经计算可得利润率为15%",
            "通过公式计算得出结论",
            "数学推导如下：首先...",
        ]
        for text in texts:
            result = validate_llm_output(text)
            assert result["valid"] is False, f"应检测到数学推断: {text}"
            assert any("数学推断" in i for i in result["issues"])

    def test_normal_long_text_returns_valid(self):
        text = "这是一段正常的LLM输出文本，包含了对消费者行为的分析和描述，不涉及任何数学计算或重复内容。"
        result = validate_llm_output(text)
        assert result["valid"] is True
        assert result["issues"] == []

    def test_repetition_detected(self):
        # 构造重复内容：同一句话重复多次
        sentence = "消费者对该产品持正面态度"
        text = (sentence + "。") * 10
        result = validate_llm_output(text)
        assert result["valid"] is False
        assert any("重复" in i for i in result["issues"])

    def test_context_passed_through(self):
        result = validate_llm_output("ok", context="test_ctx")
        assert result["context"] == "test_ctx"

    def test_output_length_reported(self):
        text = "这是一段足够长的文本用于测试输出长度字段"
        result = validate_llm_output(text)
        assert result["output_length"] == len(text)

    def test_short_text_below_threshold_not_flagged_as_repetitive(self):
        # 短文本不应触发重复检查（len <= 100）
        text = "短文本重复。短文本重复。"
        result = validate_llm_output(text)
        # 不应有重复相关issue
        assert not any("重复" in i for i in result["issues"])


class TestGetFallbackResponse:
    """get_fallback_response 测试套件"""

    def test_opinion_fallback(self):
        assert "观点" in get_fallback_response("opinion")

    def test_decision_fallback(self):
        assert "维持现状" in get_fallback_response("decision")

    def test_expression_fallback(self):
        assert "未生成" in get_fallback_response("expression")

    def test_report_fallback(self):
        assert "报告" in get_fallback_response("report")

    def test_unknown_type_fallback(self):
        result = get_fallback_response("unknown_task")
        assert "不可用" in result or "稍后重试" in result

    def test_empty_type_fallback(self):
        result = get_fallback_response("")
        assert "不可用" in result or "稍后重试" in result
