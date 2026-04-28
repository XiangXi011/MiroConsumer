from app.services.consumer.society.budget_manager import SocietyBudgetManager
from app.services.consumer.society.population_models import ConsumerSocietyRunConfig


def _config(mode: str, agents: int = 100) -> ConsumerSocietyRunConfig:
    return ConsumerSocietyRunConfig(
        mode=mode,
        core_persona_count=8,
        expanded_persona_count=20,
        shadow_agent_count=max(0, agents - 28),
        max_rounds=4,
        random_seed=1,
        llm_budget_limit=1000,
        audit_sample_size=5,
    )


def test_budget_manager_caps_quick_mode_calls_to_core_times_rounds():
    manager = SocietyBudgetManager(_config("quick", agents=8), population_size=8)

    assert manager.max_llm_calls == 32
    assert manager.allow_llm_call(layer="core") is True
    manager.used_llm_calls = 32
    assert manager.allow_llm_call(layer="core") is False


def test_budget_manager_blocks_shadow_llm_calls():
    manager = SocietyBudgetManager(_config("standard", agents=200), population_size=200)

    assert manager.allow_llm_call(layer="shadow") is False


def test_budget_manager_large_society_less_than_ten_percent():
    manager = SocietyBudgetManager(_config("large_society", agents=1200), population_size=1200)

    assert manager.max_llm_calls < 120
