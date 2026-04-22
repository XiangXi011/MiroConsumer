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


def test_packaging_test_payload_builds_brief_correctly():
    brief = ConsumerBriefAdapter.from_payload(
        {
            "task_type": "packaging_test",
            "packaging_assets": ["box-front.png", "label-detail.png"],
            "research_goal": "Evaluate shelf appeal",
        }
    )
    assert brief.task_type == ConsumerTaskType.PackagingTest
    assert brief.packaging_assets == ["box-front.png", "label-detail.png"]


def test_ab_test_payload_builds_brief_correctly():
    brief = ConsumerBriefAdapter.from_payload(
        {
            "task_type": "ab_test",
            "variants": ["Headline A", "Headline B"],
            "research_goal": "Compare messaging effectiveness",
        }
    )
    assert brief.task_type == ConsumerTaskType.ABTest
    assert brief.variants == ["Headline A", "Headline B"]


def test_ab_test_payload_prefers_structured_test_variants():
    brief = ConsumerBriefAdapter.from_payload(
        {
            "task_type": "ab_test",
            "test_variants": [
                {"variant_id": "control", "label": "Headline A", "copy_material": ["A copy"]},
                {"variant_id": "treatment", "label": "Headline B", "copy_material": ["B copy"]},
            ],
            "research_goal": "Compare messaging effectiveness",
        }
    )
    assert brief.task_type == ConsumerTaskType.ABTest
    assert len(brief.test_variants) == 2
    assert brief.test_variants[0].variant_id == "control"
    assert brief.test_variants[1].label == "Headline B"


def test_price_test_payload_builds_brief_correctly():
    brief = ConsumerBriefAdapter.from_payload(
        {
            "task_type": "price_test",
            "price_points": ["$9.99", "$12.99"],
            "research_goal": "Test price sensitivity",
        }
    )
    assert brief.task_type == ConsumerTaskType.PriceTest
    assert brief.price_points == ["$9.99", "$12.99"]


def test_price_test_payload_preserves_price_context():
    brief = ConsumerBriefAdapter.from_payload(
        {
            "task_type": "price_test",
            "price_points": ["$9.99", "$12.99"],
            "price_context": "subscription monthly",
            "research_goal": "Test price sensitivity",
        }
    )
    assert brief.price_context == "subscription monthly"


def test_packaging_test_missing_assets_raises():
    with pytest.raises(ValueError, match="packaging_assets"):
        ConsumerBriefAdapter.from_payload(
            {
                "task_type": "packaging_test",
                "research_goal": "Evaluate shelf appeal",
            }
        )


def test_ab_test_insufficient_variants_raises():
    with pytest.raises(ValueError, match="at least 2 variants"):
        ConsumerBriefAdapter.from_payload(
            {
                "task_type": "ab_test",
                "variants": ["Only one"],
                "research_goal": "Compare messaging",
            }
        )


def test_price_test_missing_price_points_raises():
    with pytest.raises(ValueError, match="price_points"):
        ConsumerBriefAdapter.from_payload(
            {
                "task_type": "price_test",
                "research_goal": "Test price sensitivity",
            }
        )


def test_new_task_types_include_fields_in_summary():
    brief = ConsumerBriefAdapter.from_payload(
        {
            "task_type": "ab_test",
            "variants": ["A", "B", "C"],
            "research_goal": "Compare",
        }
    )
    summary = brief.to_summary()
    assert summary["task_type"] == "ab_test"
    assert summary["variants"] == ["A", "B", "C"]
    assert summary["packaging_assets"] == []
    assert summary["price_points"] == []


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


def test_ab_test_payload_with_test_variants_objects():
    brief = ConsumerBriefAdapter.from_payload(
        {
            "task_type": "ab_test",
            "test_variants": [
                {
                    "variant_id": "v1",
                    "label": "Headline A",
                    "concept_assets": ["img-a.png"],
                    "copy_material": ["Copy A"],
                    "claims": ["Claim A"],
                },
                {
                    "variant_id": "v2",
                    "label": "Headline B",
                    "concept_assets": ["img-b.png"],
                    "copy_material": ["Copy B"],
                    "claims": ["Claim B"],
                },
            ],
            "research_goal": "Compare messaging effectiveness",
        }
    )
    assert brief.task_type == ConsumerTaskType.ABTest
    assert len(brief.test_variants) == 2
    assert brief.test_variants[0].label == "Headline A"
    assert brief.test_variants[0].variant_id == "v1"
    assert brief.test_variants[1].label == "Headline B"
    assert brief.test_variants[1].variant_id == "v2"


def test_price_test_payload_with_price_context():
    brief = ConsumerBriefAdapter.from_payload(
        {
            "task_type": "price_test",
            "price_points": ["$9.99", "$12.99"],
            "price_context": "Competitor prices range from $8 to $15",
            "research_goal": "Test price sensitivity",
        }
    )
    assert brief.task_type == ConsumerTaskType.PriceTest
    assert brief.price_points == ["$9.99", "$12.99"]
    assert brief.price_context == "Competitor prices range from $8 to $15"


def test_legacy_variants_normalize_to_test_variants():
    brief = ConsumerBriefAdapter.from_payload(
        {
            "task_type": "ab_test",
            "variants": ["Legacy A", "Legacy B"],
            "research_goal": "Compare messaging",
        }
    )
    assert len(brief.test_variants) == 2
    assert brief.test_variants[0].label == "Legacy A"
    assert brief.test_variants[0].variant_id == "v1"
    assert brief.test_variants[1].label == "Legacy B"
    assert brief.test_variants[1].variant_id == "v2"


def test_test_variants_takes_precedence_over_legacy_variants():
    brief = ConsumerBriefAdapter.from_payload(
        {
            "task_type": "ab_test",
            "test_variants": [
                {"variant_id": "new1", "label": "New A", "concept_assets": [], "copy_material": [], "claims": []},
                {"variant_id": "new2", "label": "New B", "concept_assets": [], "copy_material": [], "claims": []},
            ],
            "variants": ["Legacy A", "Legacy B"],
            "research_goal": "Compare messaging",
        }
    )
    assert len(brief.test_variants) == 2
    assert brief.test_variants[0].label == "New A"
    assert brief.test_variants[1].label == "New B"


def test_price_context_in_summary():
    brief = ConsumerBriefAdapter.from_payload(
        {
            "task_type": "price_test",
            "price_points": ["$9.99"],
            "price_context": "Competitor benchmark: $8-$12",
            "research_goal": "Test price sensitivity",
        }
    )
    summary = brief.to_summary()
    assert summary["price_context"] == "Competitor benchmark: $8-$12"


def test_test_variants_in_summary():
    brief = ConsumerBriefAdapter.from_payload(
        {
            "task_type": "ab_test",
            "test_variants": [
                {"variant_id": "v1", "label": "Variant A", "concept_assets": [], "copy_material": [], "claims": []},
                {"variant_id": "v2", "label": "Variant B", "concept_assets": [], "copy_material": [], "claims": []},
            ],
            "research_goal": "Compare messaging",
        }
    )
    summary = brief.to_summary()
    assert len(summary["test_variants"]) == 2
    assert summary["test_variants"][0]["label"] == "Variant A"
    assert summary["test_variants"][0]["variant_id"] == "v1"
    assert summary["test_variants"][1]["variant_id"] == "v2"
