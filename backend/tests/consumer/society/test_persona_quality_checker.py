import pytest

from app.services.consumer.persona_pack import load_default_persona_pack
from app.services.consumer.society.population_factory import PopulationFactory
from app.services.consumer.society.population_models import ConsumerSocietyRunConfig
from app.services.consumer.society.persona_quality_checker import PersonaQualityChecker


def _config(mode="standard") -> ConsumerSocietyRunConfig:
    return ConsumerSocietyRunConfig(
        mode=mode,
        core_persona_count=12,
        expanded_persona_count=40,
        shadow_agent_count=200 if mode != "quick" else 0,
        max_rounds=2,
        random_seed=99,
        llm_budget_limit=12,
        audit_sample_size=4,
    )


def test_persona_quality_checker_accepts_valid_standard_population():
    population = PopulationFactory().build_population(load_default_persona_pack(), _config())

    PersonaQualityChecker().validate(population, _config())


def test_persona_quality_checker_rejects_duplicate_agent_id():
    config = _config()
    population = PopulationFactory().build_population(load_default_persona_pack(), config)
    population[1].agent_id = population[0].agent_id

    with pytest.raises(ValueError, match="agent_id"):
        PersonaQualityChecker().validate(population, config)


def test_persona_quality_checker_requires_shadow_agents_for_standard():
    config = _config()
    population = PopulationFactory().build_population(load_default_persona_pack(), config)
    population = [agent for agent in population if agent.layer != "shadow"]

    with pytest.raises(ValueError, match="shadow"):
        PersonaQualityChecker().validate(population, config)
