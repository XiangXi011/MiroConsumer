"""LLM 治理器 — 预算/熔断/重试"""
import time
import threading
from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class CircuitBreaker:
    """熔断器"""
    failure_threshold: int = 5
    recovery_timeout: float = 60.0  # 秒
    state: str = "closed"  # closed/open/half-open
    failure_count: int = 0
    last_failure_time: float = 0.0

    def record_success(self):
        self.failure_count = 0
        self.state = "closed"

    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = "open"

    def allow_request(self) -> bool:
        if self.state == "closed":
            return True
        if self.state == "open":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "half-open"
                return True
            return False
        return True  # half-open: allow one probe


class LLMGovernor:
    """LLM 治理器"""

    def __init__(self):
        self._budgets = defaultdict(lambda: {"limit": 500, "used": 0})
        self._circuit_breakers = defaultdict(CircuitBreaker)
        self._call_log = []
        self._lock = threading.Lock()

    def set_budget(self, tenant_id: str, limit: int):
        self._budgets[tenant_id]["limit"] = limit

    def check_budget(self, tenant_id: str) -> bool:
        budget = self._budgets[tenant_id]
        return budget["used"] < budget["limit"]

    def record_cost(self, tenant_id: str, tokens: int, cost: float):
        with self._lock:
            self._budgets[tenant_id]["used"] += cost
            self._call_log.append({
                "tenant_id": tenant_id,
                "tokens": tokens,
                "cost": cost,
                "timestamp": time.time()
            })

    def check_circuit(self, service: str) -> bool:
        return self._circuit_breakers[service].allow_request()

    def record_circuit_success(self, service: str):
        self._circuit_breakers[service].record_success()

    def record_circuit_failure(self, service: str):
        self._circuit_breakers[service].record_failure()

    def get_stats(self, tenant_id: str) -> dict:
        budget = self._budgets[tenant_id]
        return {
            "budget_limit": budget["limit"],
            "budget_used": budget["used"],
            "budget_remaining": budget["limit"] - budget["used"],
            "circuit_state": self._circuit_breakers[tenant_id].state,
            "total_calls": len([c for c in self._call_log if c["tenant_id"] == tenant_id])
        }


# 全局单例
governor = LLMGovernor()
