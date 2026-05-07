"""Phase 7D LLM budget manager tests."""

import pytest

from app.config import Config
from app.contracts.errors import ValidationError


def test_run_estimate_has_fixed_shape_and_cost_level(monkeypatch):
    from app.services.application.llm_budget_manager import LLMBudgetManager

    monkeypatch.setattr(Config, "_llm_budget_limit_cache", 500, raising=False)
    monkeypatch.setattr(Config, "_llm_deep_reasoning_ratio_cache", 0.1, raising=False)
    monkeypatch.setattr(Config, "_max_agents_cache", 1000, raising=False)
    monkeypatch.setattr(Config, "_max_rounds_cache", 10, raising=False)
    monkeypatch.setattr(Config, "_deterministic_fallback_cache", True, raising=False)

    estimate = LLMBudgetManager(Config).estimate_run(
        {
            "society_mode": "standard",
            "society_max_agents": 32,
            "max_rounds": 4,
        }
    )

    assert set(estimate) >= {
        "agents_count",
        "rounds_count",
        "estimated_llm_calls",
        "cost_level",
        "estimated_duration_seconds",
    }
    assert estimate["agents_count"] == 32
    assert estimate["rounds_count"] == 4
    assert estimate["estimated_llm_calls"] == 13
    assert estimate["cost_level"] in {"low", "medium", "high", "blocked"}
    assert estimate["estimated_duration_seconds"] > 0


def test_budget_manager_exposes_all_control_dimensions(monkeypatch):
    from app.services.application.llm_budget_manager import LLMBudgetManager

    monkeypatch.setattr(Config, "_llm_budget_limit_cache", 500, raising=False)
    monkeypatch.setattr(Config, "_llm_deep_reasoning_ratio_cache", 0.1, raising=False)
    monkeypatch.setattr(Config, "_max_agents_cache", 1000, raising=False)
    monkeypatch.setattr(Config, "_max_rounds_cache", 10, raising=False)
    monkeypatch.setattr(Config, "_deterministic_fallback_cache", True, raising=False)

    estimate = LLMBudgetManager(Config).estimate_run(
        {"society_max_agents": 200, "max_rounds": 4}
    )

    controls = estimate["controls"]
    assert controls["per_run_token_estimate"] > 0
    assert controls["per_run_max_llm_calls"] == 500
    assert controls["deep_reasoning_ratio"] == 0.1
    assert controls["max_agents"] == 1000
    assert controls["max_rounds"] == 10
    assert controls["sampling_strategy"] in {"all", "stratified_sample"}
    assert isinstance(controls["early_stop"], bool)
    assert controls["deterministic_fallback"] is True


def test_budget_manager_standard_defaults_to_32_agents(monkeypatch):
    from app.services.application.llm_budget_manager import LLMBudgetManager

    monkeypatch.setattr(Config, "_llm_budget_limit_cache", 500, raising=False)
    monkeypatch.setattr(Config, "_llm_deep_reasoning_ratio_cache", 0.1, raising=False)
    monkeypatch.setattr(Config, "_max_agents_cache", 1000, raising=False)
    monkeypatch.setattr(Config, "_max_rounds_cache", 10, raising=False)

    estimate = LLMBudgetManager(Config).estimate_run(
        {
            "society_mode": "standard",
            "max_rounds": 1,
        }
    )

    assert estimate["agents_count"] == 32
    assert estimate["estimated_llm_calls"] == 4


def test_budget_manager_standard_plus_defaults_to_100_agents(monkeypatch):
    from app.services.application.llm_budget_manager import LLMBudgetManager

    monkeypatch.setattr(Config, "_llm_budget_limit_cache", 500, raising=False)
    monkeypatch.setattr(Config, "_llm_deep_reasoning_ratio_cache", 0.1, raising=False)
    monkeypatch.setattr(Config, "_max_agents_cache", 1000, raising=False)
    monkeypatch.setattr(Config, "_max_rounds_cache", 10, raising=False)

    estimate = LLMBudgetManager(Config).estimate_run(
        {
            "society_mode": "standard_plus",
            "max_rounds": 1,
        }
    )

    assert estimate["agents_count"] == 100
    assert estimate["estimated_llm_calls"] == 10


def test_budget_manager_blocks_when_estimate_exceeds_limit(monkeypatch):
    from app.services.application.llm_budget_manager import LLMBudgetManager

    monkeypatch.setattr(Config, "_llm_budget_limit_cache", 10, raising=False)
    monkeypatch.setattr(Config, "_llm_deep_reasoning_ratio_cache", 0.5, raising=False)
    monkeypatch.setattr(Config, "_max_agents_cache", 1000, raising=False)
    monkeypatch.setattr(Config, "_max_rounds_cache", 10, raising=False)

    manager = LLMBudgetManager(Config)
    estimate = manager.estimate_run({"society_max_agents": 100, "max_rounds": 2})

    assert estimate["estimated_llm_calls"] == 100
    assert estimate["cost_level"] == "blocked"
    with pytest.raises(ValidationError, match="LLM budget exceeded"):
        manager.validate_estimate(estimate)


def test_budget_manager_rejects_agent_and_round_caps(monkeypatch):
    from app.services.application.llm_budget_manager import LLMBudgetManager

    monkeypatch.setattr(Config, "_llm_budget_limit_cache", 500, raising=False)
    monkeypatch.setattr(Config, "_max_agents_cache", 50, raising=False)
    monkeypatch.setattr(Config, "_max_rounds_cache", 3, raising=False)

    manager = LLMBudgetManager(Config)

    assert manager.estimate_run({"society_max_agents": 51})["cost_level"] == "blocked"
    assert manager.estimate_run({"society_max_agents": 10, "max_rounds": 4})["cost_level"] == "blocked"
