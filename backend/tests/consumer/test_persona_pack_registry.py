from pathlib import Path
import sys
import json


BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import pytest

from app.services.consumer.persona_pack_registry import (
    PersonaPackClass,
    PersonaPackMetadata,
    PersonaPackRegistry,
    PersonaPackSelection,
    get_registry,
    list_builtin_persona_packs,
    load_persona_pack_by_id,
    _parse_and_validate_persona_pack_json,
)
from app.services.consumer.models import _normalize_persona_pack_selection


def test_list_builtin_packs_returns_at_least_default():
    packs = list_builtin_persona_packs()
    assert len(packs) >= 1
    pack_ids = {p.pack_id for p in packs}
    assert "default_persona_pack" in pack_ids


def test_list_builtin_includes_tech_early_adopters():
    packs = list_builtin_persona_packs()
    pack_ids = {p.pack_id for p in packs}
    assert "tech_early_adopters" in pack_ids
    tech = next(p for p in packs if p.pack_id == "tech_early_adopters")
    assert tech.pack_class == PersonaPackClass.Industry
    assert tech.persona_count > 0
    assert tech.source == "builtin"
    assert tech.pack_origin == "industry_pack"


def test_registry_get_pack_builtin():
    registry = get_registry()
    default = registry.get_pack("default_persona_pack")
    assert default is not None
    assert default.pack_id == "default_persona_pack"
    assert default.source == "builtin"


def test_registry_get_pack_unknown_returns_none():
    registry = get_registry()
    assert registry.get_pack("nonexistent_pack") is None


def test_registry_load_default_returns_personas():
    registry = get_registry()
    personas = registry.load_default()
    assert isinstance(personas, list)
    assert len(personas) > 0
    assert all("persona_id" in p for p in personas)


def test_registry_load_pack_by_id():
    personas = load_persona_pack_by_id("default_persona_pack")
    assert len(personas) > 0


def test_registry_resolve_selection_with_none_returns_default():
    registry = get_registry()
    personas = registry.resolve_selection(None)
    assert len(personas) > 0


def test_registry_resolve_selection_with_empty_pack_id_returns_default():
    registry = get_registry()
    selection = PersonaPackSelection(pack_id="")
    personas = registry.resolve_selection(selection)
    assert len(personas) > 0


def test_registry_resolve_selection_unknown_pack_falls_back():
    registry = get_registry()
    selection = PersonaPackSelection(pack_id="nonexistent")
    personas = registry.resolve_selection(selection)
    assert len(personas) > 0


def test_registry_resolve_selection_tech_pack():
    registry = get_registry()
    selection = PersonaPackSelection(pack_id="tech_early_adopters")
    personas = registry.resolve_selection(selection)
    assert len(personas) > 0


def test_register_custom_pack_validates_json():
    registry = PersonaPackRegistry(project_persona_dir=Path("/tmp/test_packs"))
    valid_json = json.dumps([
        {
            "persona_id": "C01",
            "label": "Custom One",
            "attention_drivers": ["trust"],
            "risk_sensitivities": ["price"],
            "expression_style": "practical",
            "search_propensity": "high",
            "cognition_level": "high",
            "herd_tendency": "medium",
            "influence_weight": 0.7,
        }
    ])
    meta = registry.register_custom_pack(valid_json, label="My Custom Pack")
    assert meta.pack_id.startswith("custom_")
    assert meta.label == "My Custom Pack"
    assert meta.pack_class == PersonaPackClass.Custom
    assert meta.persona_count == 1
    assert meta.source == "custom"
    assert meta.pack_origin == "uploaded_persona_pack"


def test_register_custom_pack_rejects_invalid_json():
    registry = PersonaPackRegistry(project_persona_dir=Path("/tmp/test_packs"))
    with pytest.raises(ValueError, match="Invalid JSON"):
        registry.register_custom_pack("not json")


def test_register_custom_pack_rejects_non_list():
    registry = PersonaPackRegistry(project_persona_dir=Path("/tmp/test_packs"))
    with pytest.raises(ValueError, match="must be a JSON list"):
        registry.register_custom_pack(json.dumps({"persona_id": "X"}))


def test_register_custom_pack_rejects_empty_list():
    registry = PersonaPackRegistry(project_persona_dir=Path("/tmp/test_packs"))
    with pytest.raises(ValueError, match="at least one persona"):
        registry.register_custom_pack(json.dumps([]))


def test_register_custom_pack_rejects_duplicate_ids():
    registry = PersonaPackRegistry(project_persona_dir=Path("/tmp/test_packs"))
    payload = json.dumps([
        {
            "persona_id": "C01",
            "label": "One",
            "attention_drivers": ["trust"],
            "risk_sensitivities": ["price"],
            "expression_style": "practical",
            "search_propensity": "high",
            "cognition_level": "high",
            "herd_tendency": "medium",
            "influence_weight": 0.7,
        },
        {
            "persona_id": "C01",
            "label": "Two",
            "attention_drivers": ["trust"],
            "risk_sensitivities": ["price"],
            "expression_style": "practical",
            "search_propensity": "high",
            "cognition_level": "high",
            "herd_tendency": "medium",
            "influence_weight": 0.5,
        },
    ])
    with pytest.raises(ValueError, match="duplicate persona_id"):
        registry.register_custom_pack(payload)


def test_register_custom_pack_requires_project_dir():
    registry = PersonaPackRegistry(project_persona_dir=None)
    with pytest.raises(ValueError, match="Project persona directory is required"):
        registry.register_custom_pack(json.dumps([]))


def test_custom_pack_discovery(tmp_path):
    project_dir = tmp_path / "persona_packs"
    project_dir.mkdir()
    pack_path = project_dir / "my_custom.json"
    pack_path.write_text(json.dumps([
        {
            "persona_id": "D01",
            "label": "Discovered",
            "attention_drivers": ["trust"],
            "risk_sensitivities": ["price"],
            "expression_style": "practical",
            "search_propensity": "high",
            "cognition_level": "high",
            "herd_tendency": "medium",
            "influence_weight": 0.7,
        }
    ]))
    registry = PersonaPackRegistry(project_persona_dir=project_dir)
    packs = registry.list_packs()
    custom = [p for p in packs if p.pack_id == "my_custom"]
    assert len(custom) == 1
    assert custom[0].source == "custom"
    assert custom[0].persona_count == 1


def test_custom_pack_load_after_register(tmp_path):
    project_dir = tmp_path / "persona_packs"
    registry = PersonaPackRegistry(project_persona_dir=project_dir)
    raw = json.dumps([
        {
            "persona_id": "E01",
            "label": "Loadable",
            "attention_drivers": ["trust"],
            "risk_sensitivities": ["price"],
            "expression_style": "practical",
            "search_propensity": "high",
            "cognition_level": "high",
            "herd_tendency": "medium",
            "influence_weight": 0.7,
        }
    ])
    meta = registry.register_custom_pack(raw, pack_id="loadable_pack")
    personas = registry.load_pack("loadable_pack")
    assert len(personas) == 1
    assert personas[0]["persona_id"] == "E01"


def test_parse_and_validate_persona_pack_json():
    raw = json.dumps([
        {
            "persona_id": "V01",
            "label": "Valid",
            "attention_drivers": ["trust"],
            "risk_sensitivities": ["price"],
            "expression_style": "practical",
            "search_propensity": "high",
            "cognition_level": "high",
            "herd_tendency": "medium",
            "influence_weight": 0.7,
        }
    ])
    personas = _parse_and_validate_persona_pack_json(raw)
    assert len(personas) == 1


def test_persona_pack_metadata_to_summary():
    meta = PersonaPackMetadata(
        pack_id="test",
        label="Test Pack",
        description="A test pack",
        pack_class=PersonaPackClass.Industry,
        persona_count=5,
        tags=["tag1"],
        source="builtin",
    )
    summary = meta.to_summary()
    assert summary["pack_id"] == "test"
    assert summary["pack_class"] == "industry"
    assert summary["persona_count"] == 5
    assert summary["pack_origin"] == "default_rule_pack"


def test_register_custom_pack_accepts_business_pack_origin(tmp_path):
    registry = PersonaPackRegistry(project_persona_dir=tmp_path / "persona_packs")
    raw = json.dumps([
        {
            "persona_id": "R01",
            "label": "Research Derived",
            "attention_drivers": ["proof"],
            "risk_sensitivities": ["safety"],
            "expression_style": "careful",
            "search_propensity": "high",
            "cognition_level": "high",
            "herd_tendency": "low",
            "influence_weight": 0.6,
        }
    ])

    meta = registry.register_custom_pack(raw, pack_origin="research_derived_pack")

    assert meta.pack_origin == "research_derived_pack"
    assert meta.to_summary()["pack_origin"] == "research_derived_pack"


def test_persona_pack_selection_to_summary():
    sel = PersonaPackSelection(pack_id="my_pack", pack_class=PersonaPackClass.Category, custom_upload=True)
    summary = sel.to_summary()
    assert summary["pack_id"] == "my_pack"
    assert summary["pack_class"] == "category"
    assert summary["custom_upload"] is True


def test_normalize_persona_pack_selection_defaults():
    result = _normalize_persona_pack_selection(None)
    assert result.pack_id == "default_persona_pack"
    assert result.pack_class == PersonaPackClass.Generic
    assert result.custom_upload is False


def test_normalize_persona_pack_selection_from_dict():
    result = _normalize_persona_pack_selection({"pack_id": "tech", "pack_class": "industry", "custom_upload": True})
    assert result.pack_id == "tech"
    assert result.pack_class == PersonaPackClass.Industry
    assert result.custom_upload is True


def test_normalize_persona_pack_selection_invalid_class_falls_back():
    result = _normalize_persona_pack_selection({"pack_id": "x", "pack_class": "invalid"})
    assert result.pack_class == PersonaPackClass.Generic
