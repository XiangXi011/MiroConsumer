"""error_codes 模块测试"""

import pytest
from app.utils.error_codes import ErrorCodes, error_response


class TestErrorCodes:
    """错误码常量测试"""

    def test_all_codes_have_three_elements(self):
        """所有错误码都应包含 (code, message, status) 三个元素"""
        codes = [
            attr
            for attr in dir(ErrorCodes)
            if not attr.startswith("_") and not callable(getattr(ErrorCodes, attr))
        ]
        assert len(codes) > 0
        for name in codes:
            value = getattr(ErrorCodes, name)
            assert isinstance(value, tuple), f"{name} 不是 tuple"
            assert len(value) == 3, f"{name} 应有 3 个元素，实际有 {len(value)}"

    def test_status_codes_are_integers(self):
        """所有状态码应为整数"""
        codes = [
            attr
            for attr in dir(ErrorCodes)
            if not attr.startswith("_") and not callable(getattr(ErrorCodes, attr))
        ]
        for name in codes:
            _, _, status = getattr(ErrorCodes, name)
            assert isinstance(status, int), f"{name} 的状态码不是整数"


class TestErrorResponse:
    """error_response 函数测试"""

    def test_basic_response_format(self):
        """返回正确的格式：(dict, int)"""
        resp, status = error_response(ErrorCodes.NOT_FOUND)
        assert isinstance(resp, dict)
        assert isinstance(status, int)
        assert status == 404

    def test_response_contains_required_fields(self):
        """响应包含 success, error, message 字段"""
        resp, status = error_response(ErrorCodes.INTERNAL_ERROR)
        assert resp["success"] is False
        assert resp["error"] == "INTERNAL_ERROR"
        assert resp["message"] == "内部服务器错误"
        assert status == 500

    def test_details_not_present_when_none(self):
        """details 为 None 时不包含该字段"""
        resp, _ = error_response(ErrorCodes.INVALID_REQUEST)
        assert "details" not in resp

    def test_details_passed_correctly(self):
        """details 参数正确传递"""
        details = {"field": "topic", "reason": "不能为空"}
        resp, status = error_response(ErrorCodes.SIMULATION_INVALID_PARAMS, details)
        assert resp["details"] == details
        assert status == 400

    def test_details_can_be_any_truthy_value(self):
        """details 可以是任意 truthy 值"""
        resp, _ = error_response(ErrorCodes.LLM_ERROR, "connection refused")
        assert resp["details"] == "connection refused"

    def test_simulation_error_codes(self):
        """仿真相关错误码状态正确"""
        _, status = error_response(ErrorCodes.SIMULATION_NOT_FOUND)
        assert status == 404

        _, status = error_response(ErrorCodes.SIMULATION_ALREADY_RUNNING)
        assert status == 409

        _, status = error_response(ErrorCodes.SIMULATION_FAILED)
        assert status == 500

    def test_llm_error_codes(self):
        """LLM 相关错误码状态正确"""
        _, status = error_response(ErrorCodes.LLM_ERROR)
        assert status == 502

        _, status = error_response(ErrorCodes.LLM_QUOTA_EXCEEDED)
        assert status == 429

        _, status = error_response(ErrorCodes.LLM_TIMEOUT)
        assert status == 504

    def test_report_error_codes(self):
        """报告相关错误码状态正确"""
        _, status = error_response(ErrorCodes.REPORT_NOT_FOUND)
        assert status == 404

        _, status = error_response(ErrorCodes.REPORT_GENERATION_FAILED)
        assert status == 500
