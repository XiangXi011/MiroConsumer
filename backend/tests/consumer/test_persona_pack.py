from pathlib import Path
import sys


BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.consumer.persona_pack import (
    can_access_deep_graph,
    load_default_persona_pack,
    map_persona_to_agent_traits,
)


EXPECTED_FIELDS = {
    "persona_id",
    "label",
    "attention_drivers",
    "risk_sensitivities",
    "expression_style",
    "search_propensity",
    "cognition_level",
    "herd_tendency",
    "influence_weight",
}


def test_load_default_persona_pack_returns_phase1_personas():
    personas = load_default_persona_pack()

    assert personas
    assert all(EXPECTED_FIELDS.issubset(persona.keys()) for persona in personas)
    assert {persona["persona_id"] for persona in personas} >= {"M01", "M05", "M08"}


def test_default_pack_includes_deep_graph_eligible_persona():
    personas = load_default_persona_pack()

    assert any(
        persona["search_propensity"] == "high" and persona["cognition_level"] == "high"
        for persona in personas
    )


def test_can_access_deep_graph_requires_high_search_and_cognition():
    assert can_access_deep_graph(
        {"search_propensity": "high", "cognition_level": "high"}
    )
    assert not can_access_deep_graph(
        {"search_propensity": "medium", "cognition_level": "high"}
    )
    assert not can_access_deep_graph(
        {"search_propensity": "high", "cognition_level": "medium"}
    )
    assert not can_access_deep_graph(
        {"search_propensity": "low", "cognition_level": "low"}
    )


def test_mapping_output_exposes_phase1_propagation_traits():
    persona = next(
        persona for persona in load_default_persona_pack() if persona["persona_id"] == "M01"
    )

    traits = map_persona_to_agent_traits(persona)

    assert traits["persona_id"] == "M01"
    assert traits["attention_drivers"]
    assert traits["risk_sensitivities"]
    assert isinstance(traits["influence_weight"], float)
    assert traits["propagation_profile"] == {
        "search_propensity": persona["search_propensity"],
        "cognition_level": persona["cognition_level"],
        "herd_tendency": persona["herd_tendency"],
    }
    assert traits["can_access_deep_graph"] is True
