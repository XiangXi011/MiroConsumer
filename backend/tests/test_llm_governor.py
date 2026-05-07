"""LLM Governor 单元测试"""
import time
import pytest
from unittest.mock import patch

from app.utils.llm_governor import CircuitBreaker, LLMGovernor


class TestCircuitBreaker:
    """熔断器测试"""

    def test_closed_state_allows_requests(self):
        cb = CircuitBreaker()
        assert cb.state == "closed"
        assert cb.allow_request() is True

    def test_opens_after_threshold_failures(self):
        cb = CircuitBreaker(failure_threshold=3)
        for _ in range(3):
            cb.record_failure()
        assert cb.state == "open"
        assert cb.allow_request() is False

    def test_half_open_after_recovery_timeout(self):
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "open"
        assert cb.allow_request() is False

        time.sleep(0.15)
        assert cb.allow_request() is True
        assert cb.state == "half-open"

    def test_success_resets_state(self):
        cb = CircuitBreaker(failure_threshold=2)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "open"

        # Simulate recovery timeout
        cb.last_failure_time = time.time() - 100
        cb.allow_request()  # transitions to half-open
        cb.record_success()
        assert cb.state == "closed"
        assert cb.failure_count == 0

    def test_half_open_allows_one_probe(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.01)
        cb.record_failure()
        assert cb.state == "open"

        time.sleep(0.02)
        assert cb.allow_request() is True  # half-open probe
        assert cb.state == "half-open"


class TestLLMGovernor:
    """LLM 治理器测试"""

    def test_check_budget_pass(self):
        gov = LLMGovernor()
        gov.set_budget("t1", 100)
        assert gov.check_budget("t1") is True

    def test_check_budget_reject_after_exhaustion(self):
        gov = LLMGovernor()
        gov.set_budget("t1", 10)
        gov.record_cost("t1", tokens=100, cost=10.0)
        assert gov.check_budget("t1") is False

    def test_budget_accumulation(self):
        gov = LLMGovernor()
        gov.set_budget("t1", 100)
        gov.record_cost("t1", tokens=50, cost=40.0)
        assert gov.check_budget("t1") is True
        gov.record_cost("t1", tokens=50, cost=40.0)
        assert gov.check_budget("t1") is True
        gov.record_cost("t1", tokens=50, cost=21.0)
        assert gov.check_budget("t1") is False

    def test_check_circuit(self):
        gov = LLMGovernor()
        assert gov.check_circuit("svc1") is True

    def test_circuit_opens_on_failures(self):
        gov = LLMGovernor()
        for _ in range(5):
            gov.record_circuit_failure("svc1")
        assert gov.check_circuit("svc1") is False

    def test_circuit_recovery(self):
        gov = LLMGovernor()
        for _ in range(5):
            gov.record_circuit_failure("svc1")

        # Force recovery timeout
        gov._circuit_breakers["svc1"].last_failure_time = time.time() - 120
        assert gov.check_circuit("svc1") is True
        gov.record_circuit_success("svc1")
        assert gov.check_circuit("svc1") is True

    def test_get_stats(self):
        gov = LLMGovernor()
        gov.set_budget("t1", 200)
        gov.record_cost("t1", tokens=50, cost=30.0)
        stats = gov.get_stats("t1")
        assert stats["budget_limit"] == 200
        assert stats["budget_used"] == 30.0
        assert stats["budget_remaining"] == 170.0
        assert stats["total_calls"] == 1

    def test_default_budget(self):
        gov = LLMGovernor()
        # 默认 budget limit = 500
        assert gov.check_budget("unknown_tenant") is True
