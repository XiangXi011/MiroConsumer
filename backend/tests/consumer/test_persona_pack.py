from pathlib import Path
import sys
import json

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.consumer import persona_pack
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
    "source_basis",
}

SOURCE_BASIS_FIELDS = {
    "psychology_theory",
    "data_sources",
    "sample_characteristics",
}

SAMPLE_CHARACTERISTICS_FIELDS = {
    "age_range",
    "region",
    "income_level",
}


def test_load_default_persona_pack_returns_phase1_personas():
    personas = load_default_persona_pack()

    assert personas
    assert len(personas) == 16
    assert all(EXPECTED_FIELDS.issubset(persona.keys()) for persona in personas)
    assert {persona["persona_id"] for persona in personas} >= {"M01", "M05", "M08"}


def test_default_personas_include_research_source_basis():
    personas = load_default_persona_pack()

    for persona in personas:
        basis = persona["source_basis"]

        assert SOURCE_BASIS_FIELDS.issubset(basis.keys()), persona["persona_id"]
        assert basis["psychology_theory"].strip(), persona["persona_id"]
        assert basis["data_sources"], persona["persona_id"]
        assert all(source.strip() for source in basis["data_sources"])

        sample = basis["sample_characteristics"]
        assert SAMPLE_CHARACTERISTICS_FIELDS.issubset(sample.keys()), persona["persona_id"]
        assert all(str(sample[field]).strip() for field in SAMPLE_CHARACTERISTICS_FIELDS)


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


def test_load_default_persona_pack_rejects_non_list_payload(tmp_path, monkeypatch):
    payload_path = tmp_path / "default_personas.json"
    payload_path.write_text(json.dumps({"persona_id": "M01"}), encoding="utf-8")
    monkeypatch.setattr(persona_pack, "_DEFAULT_PERSONA_PATH", payload_path)

    with pytest.raises(ValueError, match="top-level JSON payload must be a list"):
        load_default_persona_pack()


def test_load_default_persona_pack_rejects_duplicate_persona_ids(tmp_path, monkeypatch):
    payload_path = tmp_path / "default_personas.json"
    payload_path.write_text(
        json.dumps(
            [
                {
                    "persona_id": "M01",
                    "label": "One",
                    "attention_drivers": ["trust"],
                    "risk_sensitivities": ["sugar"],
                    "expression_style": "practical",
                    "search_propensity": "high",
                    "cognition_level": "high",
                    "herd_tendency": "medium",
                    "influence_weight": 0.8,
                },
                {
                    "persona_id": "M01",
                    "label": "Two",
                    "attention_drivers": ["value"],
                    "risk_sensitivities": ["overclaim"],
                    "expression_style": "direct",
                    "search_propensity": "low",
                    "cognition_level": "low",
                    "herd_tendency": "medium",
                    "influence_weight": 0.4,
                },
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(persona_pack, "_DEFAULT_PERSONA_PATH", payload_path)

    with pytest.raises(ValueError, match="duplicate persona_id: M01"):
        load_default_persona_pack()


@pytest.mark.parametrize("bad_weight", [True, -0.1, 1.1])
def test_mapping_rejects_invalid_influence_weight(bad_weight):
    with pytest.raises(ValueError, match="influence_weight"):
        map_persona_to_agent_traits(
            {
                "persona_id": "M99",
                "label": "Invalid",
                "attention_drivers": ["trust"],
                "risk_sensitivities": ["sugar"],
                "expression_style": "practical",
                "search_propensity": "high",
                "cognition_level": "high",
                "herd_tendency": "medium",
                "influence_weight": bad_weight,
            }
        )


def test_mapping_rejects_missing_required_fields():
    with pytest.raises(ValueError, match="missing required fields: label"):
        map_persona_to_agent_traits(
            {
                "persona_id": "M99",
                "attention_drivers": ["trust"],
                "risk_sensitivities": ["sugar"],
                "expression_style": "practical",
                "search_propensity": "high",
                "cognition_level": "high",
                "herd_tendency": "medium",
                "influence_weight": 0.5,
            }
        )


def test_mapping_rejects_invalid_propagation_level():
    with pytest.raises(ValueError, match="search_propensity must be one of"):
        map_persona_to_agent_traits(
            {
                "persona_id": "M99",
                "label": "Invalid level",
                "attention_drivers": ["trust"],
                "risk_sensitivities": ["sugar"],
                "expression_style": "practical",
                "search_propensity": "very_high",
                "cognition_level": "high",
                "herd_tendency": "medium",
                "influence_weight": 0.5,
            }
        )
