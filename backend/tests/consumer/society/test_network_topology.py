from app.services.consumer.persona_pack import load_default_persona_pack
from app.services.consumer.society.network_topology import (
    GRAPH_KEYS,
    build_consumer_network_topology,
)
from app.services.consumer.society.population_factory import PopulationFactory
from app.services.consumer.society.population_models import ConsumerSocietyRunConfig


def _population():
    config = ConsumerSocietyRunConfig(
        mode="standard",
        core_persona_count=8,
        expanded_persona_count=16,
        shadow_agent_count=8,
        random_seed=11,
        llm_budget_limit=12,
        enabled_channels=["xiaohongshu", "wechat_group", "ecommerce_review"],
    )
    return PopulationFactory().build_population(load_default_persona_pack(), config)


def test_network_topology_contains_required_graphs_and_edge_fields():
    population = _population()
    assignments = {
        "xiaohongshu": [agent.agent_id for agent in population[:10]],
        "wechat_group": [agent.agent_id for agent in population[10:20]],
        "ecommerce_review": [agent.agent_id for agent in population[20:]],
    }

    topology = build_consumer_network_topology(population, assignments, seed=11)

    assert topology["topology_version"] == "phase7g_p2_v1"
    assert topology["node_count"] == len(population)
    assert topology["edge_count"] > 0
    assert set(topology["graphs"]) == set(GRAPH_KEYS)
    edge = topology["edges"][0]
    assert set(edge) >= {
        "source_agent_id",
        "target_agent_id",
        "graph_type",
        "trust_weight",
        "influence_weight",
        "exposure_frequency",
        "misread_probability",
    }
    assert 0 <= edge["trust_weight"] <= 1
    assert 0 <= edge["misread_probability"] <= 1


def test_network_topology_is_deterministic_for_same_seed():
    population = _population()
    first = build_consumer_network_topology(population, seed=7)
    second = build_consumer_network_topology(population, seed=7)

    assert first["edges"] == second["edges"]
