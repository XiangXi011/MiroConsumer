from app.services.consumer.persona_pack import load_default_persona_pack
from app.services.consumer.society.consumer_roles import ConsumerRole
from app.services.consumer.society.population_factory import PopulationFactory
from app.services.consumer.society.population_models import ConsumerSocietyRunConfig


def _config(seed: int = 123) -> ConsumerSocietyRunConfig:
    return ConsumerSocietyRunConfig(
        mode="standard",
        core_persona_count=12,
        expanded_persona_count=40,
        shadow_agent_count=200,
        max_rounds=3,
        random_seed=seed,
        llm_budget_limit=20,
        audit_sample_size=8,
    )


def test_population_factory_generates_same_population_for_same_seed():
    personas = load_default_persona_pack()
    first = PopulationFactory().build_population(personas, _config(seed=42))
    second = PopulationFactory().build_population(personas, _config(seed=42))

    assert [agent.to_dict() for agent in first] == [agent.to_dict() for agent in second]


def test_population_factory_generates_different_ids_for_different_seed():
    personas = load_default_persona_pack()
    first = PopulationFactory().build_population(personas, _config(seed=42))
    second = PopulationFactory().build_population(personas, _config(seed=43))

    assert [agent.agent_id for agent in first] != [agent.agent_id for agent in second]


def test_population_factory_preserves_parent_segment_and_role_floor():
    personas = load_default_persona_pack()
    population = PopulationFactory().build_population(personas, _config(seed=5))

    assert len(population) == 252
    assert all(agent.parent_persona_id for agent in population)
    assert all(agent.segment for agent in population)
    assert {agent.layer for agent in population} == {"core", "expanded", "shadow"}

    role_counts = {role.value: 0 for role in ConsumerRole}
    for agent in population:
        role_counts[agent.role.value] += 1

    minimum = int(len(population) * 0.05)
    assert all(count >= minimum for count in role_counts.values())


def test_population_factory_preserves_generated_consumer_profile_traits():
    profiles = [
        {
            "persona_id": "M01",
            "name": "一线城市精致妈妈",
            "age_range": "28-35",
            "city_tier": "一线/新一线",
            "income_level": "中高",
            "family_structure": "有1个3-8岁孩子",
            "purchase_channel": ["小红书", "天猫"],
            "category_usage_frequency": "每周多次",
            "price_sensitivity": 0.42,
            "evidence_sensitivity": 0.81,
            "risk_sensitivities": ["材质安全"],
            "expression_style": "谨慎但愿意尝新",
            "bio": "她关注材质安全。",
            "persona": "家庭消费决策者",
            "source": "hybrid",
        }
    ]
    config = ConsumerSocietyRunConfig(
        mode="quick",
        core_persona_count=1,
        expanded_persona_count=0,
        shadow_agent_count=0,
    )

    population = PopulationFactory().build_population(profiles, config)
    agent = population[0]

    assert agent.segment == "一线城市精致妈妈"
    assert agent.price_sensitivity == 0.42
    assert agent.evidence_sensitivity == 0.81
    assert agent.traits["name"] == "一线城市精致妈妈"
    assert agent.traits["city_tier"] == "一线/新一线"
    assert agent.traits["family_structure"] == "有1个3-8岁孩子"
    assert agent.traits["purchase_channel"] == ["小红书", "天猫"]
