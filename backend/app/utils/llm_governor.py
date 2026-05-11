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

    def set_budget(self, tenant_id: str = None, user_id: str = None,
                   project_id: str = None, limit: int = 500):
        key = self._budget_key(tenant_id, user_id, project_id)
        self._budgets[key]["limit"] = limit

    def check_budget(self, tenant_id: str = None, user_id: str = None,
                     project_id: str = None) -> bool:
        for key in self._budget_keys(tenant_id, user_id, project_id):
            budget = self._budgets[key]
            if budget["used"] >= budget["limit"]:
                return False
        return True

    def record_cost(self, tenant_id: str = None, user_id: str = None,
                    project_id: str = None, tokens: int = 0, cost: float = 0):
        with self._lock:
            for key in self._budget_keys(tenant_id, user_id, project_id):
                self._budgets[key]["used"] += cost
            self._call_log.append({
                "tenant_id": tenant_id or "default",
                "user_id": user_id,
                "project_id": project_id,
                "tokens": tokens,
                "cost": cost,
                "timestamp": time.time()
            })

    def _budget_key(self, tenant_id, user_id, project_id):
        if project_id:
            return f"project:{project_id}"
        if user_id:
            return f"user:{user_id}"
        return f"tenant:{tenant_id or 'default'}"

    def _budget_keys(self, tenant_id, user_id, project_id):
        """返回所有需要检查的预算维度"""
        keys = []
        if tenant_id:
            keys.append(f"tenant:{tenant_id}")
        if user_id:
            keys.append(f"user:{user_id}")
        if project_id:
            keys.append(f"project:{project_id}")
        return keys if keys else ["tenant:default"]

    def check_circuit(self, service: str) -> bool:
        return self._circuit_breakers[service].allow_request()

    def record_circuit_success(self, service: str):
        self._circuit_breakers[service].record_success()

    def record_circuit_failure(self, service: str):
        self._circuit_breakers[service].record_failure()

    def get_stats(self, tenant_id: str = None, user_id: str = None,
                  project_id: str = None) -> dict:
        key = self._budget_key(tenant_id, user_id, project_id)
        budget = self._budgets[key]
        tid = tenant_id or "default"
        return {
            "budget_key": key,
            "budget_limit": budget["limit"],
            "budget_used": budget["used"],
            "budget_remaining": budget["limit"] - budget["used"],
            "circuit_state": self._circuit_breakers[tid].state,
            "total_calls": len([c for c in self._call_log if c.get("tenant_id") == tid])
        }


# 全局单例
governor = LLMGovernor()
