from pathlib import Path
import sys


BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import pytest

from app.services.consumer.brief_adapter import ConsumerBriefAdapter
from app.services.consumer.models import ConsumerBusinessBrief, ConsumerTaskType, GraphVisibility


def test_concept_test_payload_builds_brief_correctly():
    brief = ConsumerBriefAdapter.from_payload(
        {
            "task_type": "concept_test",
            "product_concept_assets": ["prototype-a.png", "prototype-b.png"],
            "copy_material": ["headline one", "headline two"],
            "target_audience": ["young professionals"],
            "usage_scene": ["social feed", "landing page"],
            "research_goal": "Validate product appeal",
            "optional_background_materials": ["brand notes"],
            "graph_visibility": " Restricted ",
        }
    )

    assert brief.task_type == ConsumerTaskType.ConceptTest
    assert brief.product_concept_assets == ["prototype-a.png", "prototype-b.png"]
    assert brief.copy_material == ["headline one", "headline two"]
    assert brief.target_audience == ["young professionals"]
    assert brief.usage_scene == ["social feed", "landing page"]
    assert brief.research_goal == "Validate product appeal"
    assert brief.optional_background_materials == ["brand notes"]
    assert brief.graph_visibility == GraphVisibility.Restricted


def test_missing_required_fields_raises_value_error():
    with pytest.raises(ValueError, match="required"):
        ConsumerBriefAdapter.from_payload(
            {
                "task_type": "concept_test",
                "copy_material": ["headline"],
                "research_goal": "Measure interest",
            }
        )


def test_non_mapping_payload_rejected():
    with pytest.raises(ValueError, match="mapping"):
        ConsumerBriefAdapter.from_payload(["not", "a", "mapping"])


def test_claims_default_from_copy_material_when_omitted():
    brief = ConsumerBriefAdapter.from_payload(
        {
            "task_type": "copy_feedback",
            "product_concept_assets": ["copy-draft.png"],
            "copy_material": ["Claim A", "Claim B"],
            "research_goal": "Check message clarity",
        }
    )

    assert brief.claims == ["Claim A", "Claim B"]


def test_non_string_elements_in_list_fields_rejected():
    with pytest.raises(ValueError, match="product_concept_assets"):
        ConsumerBriefAdapter.from_payload(
            {
                "task_type": "concept_test",
                "product_concept_assets": ["prototype.png", 123],
                "research_goal": "Understand appeal",
            }
        )


def test_single_string_inputs_normalize_to_one_item_lists():
    brief = ConsumerBriefAdapter.from_payload(
        {
            "task_type": "concept_test",
            "product_concept_assets": "prototype.png",
            "copy_material": "headline",
            "claims": "claim one",
            "target_audience": "students",
            "usage_scene": "mobile app",
            "research_goal": "Understand appeal",
            "optional_background_materials": "background note",
        }
    )

    assert brief.product_concept_assets == ["prototype.png"]
    assert brief.copy_material == ["headline"]
    assert brief.claims == ["claim one"]
    assert brief.target_audience == ["students"]
    assert brief.usage_scene == ["mobile app"]
    assert brief.optional_background_materials == ["background note"]


def test_whitespace_values_trimmed_or_dropped():
    brief = ConsumerBriefAdapter.from_payload(
        {
            "task_type": "copy_feedback",
            "product_concept_assets": ["  prototype.png  ", "   "],
            "copy_material": ["  headline  ", "   "],
            "target_audience": ["  students  ", " "],
            "usage_scene": ["  mobile app  ", ""],
            "research_goal": "  Understand appeal  ",
            "optional_background_materials": ["  note  ", "   "],
        }
    )

    assert brief.product_concept_assets == ["prototype.png"]
    assert brief.copy_material == ["headline"]
    assert brief.claims == ["headline"]
    assert brief.target_audience == ["students"]
    assert brief.usage_scene == ["mobile app"]
    assert brief.optional_background_materials == ["note"]
    assert brief.research_goal == "Understand appeal"


def test_unsupported_task_type_raises_value_error():
    with pytest.raises(ValueError, match="Unsupported task_type"):
        ConsumerBriefAdapter.from_payload(
            {
                "task_type": "pricing_study",
                "product_concept_assets": ["prototype.png"],
                "research_goal": "Understand appeal",
            }
        )


def test_adapter_rejects_invalid_graph_visibility():
    with pytest.raises(ValueError, match="Unsupported graph_visibility"):
        ConsumerBriefAdapter.from_payload(
            {
                "task_type": "concept_test",
                "product_concept_assets": ["prototype.png"],
                "research_goal": "Understand appeal",
                "graph_visibility": "Invisible",
            }
        )


def test_enable_lane_b_defaults_to_false():
    brief = ConsumerBriefAdapter.from_payload(
        {
            "task_type": "concept_test",
            "product_concept_assets": ["prototype.png"],
            "research_goal": "Understand appeal",
        }
    )
    assert brief.enable_lane_b is False


def test_enable_lane_b_true_from_boolean():
    brief = ConsumerBriefAdapter.from_payload(
        {
            "task_type": "concept_test",
            "product_concept_assets": ["prototype.png"],
            "research_goal": "Understand appeal",
            "enable_lane_b": True,
        }
    )
    assert brief.enable_lane_b is True


def test_enable_lane_b_true_from_string():
    brief = ConsumerBriefAdapter.from_payload(
        {
            "task_type": "concept_test",
            "product_concept_assets": ["prototype.png"],
            "research_goal": "Understand appeal",
            "enable_lane_b": "true",
        }
    )
    assert brief.enable_lane_b is True


def test_enable_lane_b_in_summary():
    brief = ConsumerBriefAdapter.from_payload(
        {
            "task_type": "concept_test",
            "product_concept_assets": ["prototype.png"],
            "research_goal": "Understand appeal",
            "enable_lane_b": True,
        }
    )
    summary = brief.to_summary()
    assert summary["enable_lane_b"] is True


def test_model_rejects_invalid_task_type_and_graph_visibility():
    with pytest.raises(ValueError, match="Unsupported task_type"):
        ConsumerBusinessBrief(
            task_type="pricing_study",
            product_concept_assets=["prototype.png"],
            research_goal="Understand appeal",
        )

    with pytest.raises(ValueError, match="Unsupported graph_visibility"):
        ConsumerBusinessBrief(
            task_type=ConsumerTaskType.ConceptTest,
            product_concept_assets=["prototype.png"],
            research_goal="Understand appeal",
            graph_visibility="Hidden",
        )
