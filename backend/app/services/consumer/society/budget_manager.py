"""LLM budget control for the consumer society runtime."""

from __future__ import annotations

from .population_models import ConsumerSocietyRunConfig


class SocietyBudgetManager:
    """Enforce Phase 6G LLM budget boundaries."""

    def __init__(self, config: ConsumerSocietyRunConfig, population_size: int):
        self.config = config
        self.population_size = max(int(population_size or 0), 1)
        self.used_llm_calls = 0
        self.max_llm_calls = self._compute_max_llm_calls()

    def _compute_max_llm_calls(self) -> int:
        if self.config.mode == "quick":
            return int(self.config.core_persona_count * self.config.max_rounds)
        if self.config.mode == "large_society":
            return max(0, min(int(self.config.llm_budget_limit), max(0, int(self.population_size * 0.1) - 1)))
        return max(0, int(self.config.llm_budget_limit))

    def allow_llm_call(self, layer: str) -> bool:
        if layer == "shadow":
            return False
        if self.used_llm_calls >= self.max_llm_calls:
            return False
        return True

    def record_llm_call(self, layer: str) -> bool:
        if not self.allow_llm_call(layer):
            return False
        self.used_llm_calls += 1
        return True

    def to_dict(self) -> dict:
        return {
            "max_llm_calls": self.max_llm_calls,
            "used_llm_calls": self.used_llm_calls,
            "early_stop_round": None,
        }


__all__ = ["SocietyBudgetManager"]
