"""Phase 7D LLM budget estimation and enforcement."""

from __future__ import annotations

import math
from typing import Any, Dict

from ...config import Config
from ...contracts.errors import ValidationError

COST_LEVELS = {"low", "medium", "high", "blocked"}


class LLMBudgetManager:
    """Estimate and enforce per-run LLM usage before simulation startup."""

    def __init__(self, config: type[Config] = Config):
        self.config = config

    def estimate_run(self, payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
        payload = payload or {}
        agents_count = self._agents_count(payload)
        rounds_count = self._rounds_count(payload)
        ratio = float(self.config.LLM_DEEP_REASONING_RATIO)
        estimated_llm_calls = int(math.ceil(agents_count * rounds_count * ratio))
        blocked = (
            agents_count > int(self.config.MAX_AGENTS)
            or rounds_count > int(self.config.MAX_ROUNDS)
            or estimated_llm_calls > int(self.config.LLM_BUDGET_LIMIT)
        )
        cost_level = self._cost_level(estimated_llm_calls, blocked)
        estimated_duration_seconds = int(rounds_count * 60 + estimated_llm_calls * 3)
        controls = {
            "per_run_token_estimate": estimated_llm_calls * 800,
            "per_run_max_llm_calls": int(self.config.LLM_BUDGET_LIMIT),
            "deep_reasoning_ratio": ratio,
            "max_agents": int(self.config.MAX_AGENTS),
            "max_rounds": int(self.config.MAX_ROUNDS),
            "sampling_strategy": "all" if agents_count <= 50 else "stratified_sample",
            "early_stop": cost_level in {"high", "blocked"},
            "deterministic_fallback": bool(self.config.ENABLE_DETERMINISTIC_FALLBACK),
        }
        return {
            "agents_count": agents_count,
            "rounds_count": rounds_count,
            "estimated_llm_calls": estimated_llm_calls,
            "cost_level": cost_level,
            "estimated_duration_seconds": estimated_duration_seconds,
            "controls": controls,
        }

    def validate_estimate(self, estimate: Dict[str, Any]) -> None:
        if estimate.get("cost_level") == "blocked":
            raise ValidationError(
                "LLM budget exceeded: run estimate is blocked by Phase 7D budget manager"
            )

    def validate_run(self, payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
        estimate = self.estimate_run(payload)
        self.validate_estimate(estimate)
        return estimate

    def _agents_count(self, payload: Dict[str, Any]) -> int:
        if payload.get("society_max_agents") is not None:
            return int(payload["society_max_agents"])
        mode = str(payload.get("society_mode") or "quick")
        if mode == "large_society":
            return 1000
        if mode == "standard_plus":
            return 100
        if mode == "standard":
            return 32
        return 8

    def _rounds_count(self, payload: Dict[str, Any]) -> int:
        if payload.get("max_rounds") is not None:
            return int(payload["max_rounds"])
        return int(self.config.MAX_ROUNDS)

    def _cost_level(self, estimated_llm_calls: int, blocked: bool) -> str:
        if blocked:
            return "blocked"
        limit = max(int(self.config.LLM_BUDGET_LIMIT), 1)
        ratio = estimated_llm_calls / limit
        if ratio <= 0.25:
            return "low"
        if ratio <= 0.75:
            return "medium"
        return "high"
