from pathlib import Path
import sys


BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import pytest

from app.services.consumer.models import ConsumerBusinessBrief, ConsumerTaskType, GraphVisibility


def test_packaging_test_requires_packaging_assets():
    brief = ConsumerBusinessBrief(
        task_type=ConsumerTaskType.PackagingTest,
        product_concept_assets=[],
        packaging_assets=["box-v1.png", "label-v1.png"],
        research_goal="Evaluate shelf appeal",
    )
    assert brief.task_type == ConsumerTaskType.PackagingTest
    assert brief.packaging_assets == ["box-v1.png", "label-v1.png"]


def test_packaging_test_missing_packaging_assets_raises():
    with pytest.raises(ValueError, match="packaging_assets"):
        ConsumerBusinessBrief(
            task_type=ConsumerTaskType.PackagingTest,
            product_concept_assets=[],
            research_goal="Evaluate shelf appeal",
        )


def test_ab_test_requires_at_least_two_variants():
    brief = ConsumerBusinessBrief(
        task_type=ConsumerTaskType.ABTest,
        product_concept_assets=[],
        variants=["Variant A headline", "Variant B headline"],
        research_goal="Compare messaging",
    )
    assert brief.task_type == ConsumerTaskType.ABTest
    assert len(brief.variants) == 2


def test_ab_test_accepts_structured_test_variants():
    brief = ConsumerBusinessBrief(
        task_type=ConsumerTaskType.ABTest,
        product_concept_assets=[],
        test_variants=[
            {"variant_id": "control", "label": "Variant A", "copy_material": ["A"]},
            {"variant_id": "treatment", "label": "Variant B", "copy_material": ["B"]},
        ],
        research_goal="Compare messaging",
    )
    assert len(brief.test_variants) == 2
    assert brief.test_variants[0].variant_id == "control"
    assert brief.test_variants[1].label == "Variant B"


def test_ab_test_with_one_variant_raises():
    with pytest.raises(ValueError, match="at least 2 variants"):
        ConsumerBusinessBrief(
            task_type=ConsumerTaskType.ABTest,
            product_concept_assets=[],
            variants=["Only one"],
            research_goal="Compare messaging",
        )


def test_ab_test_with_no_variants_raises():
    with pytest.raises(ValueError, match="at least 2 variants"):
        ConsumerBusinessBrief(
            task_type=ConsumerTaskType.ABTest,
            product_concept_assets=[],
            research_goal="Compare messaging",
        )


def test_price_test_requires_at_least_one_price_point():
    brief = ConsumerBusinessBrief(
        task_type=ConsumerTaskType.PriceTest,
        product_concept_assets=[],
        price_points=["$9.99"],
        research_goal="Test price sensitivity",
    )
    assert brief.task_type == ConsumerTaskType.PriceTest
    assert brief.price_points == ["$9.99"]


def test_price_test_keeps_price_context():
    brief = ConsumerBusinessBrief(
        task_type=ConsumerTaskType.PriceTest,
        product_concept_assets=[],
        price_points=["$9.99"],
        price_context="subscription monthly",
        research_goal="Test price sensitivity",
    )
    assert brief.price_context == "subscription monthly"


def test_price_test_missing_price_points_raises():
    with pytest.raises(ValueError, match="price_points"):
        ConsumerBusinessBrief(
            task_type=ConsumerTaskType.PriceTest,
            product_concept_assets=[],
            research_goal="Test price sensitivity",
        )


def test_concept_test_still_requires_product_concept_assets():
    with pytest.raises(ValueError, match="product_concept_assets"):
        ConsumerBusinessBrief(
            task_type=ConsumerTaskType.ConceptTest,
            product_concept_assets=[],
            research_goal="Test appeal",
        )


def test_copy_feedback_still_requires_product_concept_assets():
    with pytest.raises(ValueError, match="product_concept_assets"):
        ConsumerBusinessBrief(
            task_type=ConsumerTaskType.CopyFeedback,
            product_concept_assets=[],
            research_goal="Test clarity",
        )


def test_concept_test_backward_compatible():
    brief = ConsumerBusinessBrief(
        task_type=ConsumerTaskType.ConceptTest,
        product_concept_assets=["proto.png"],
        copy_material=["Great product"],
        claims=["Best in class"],
        target_audience=["millennials"],
        usage_scene=["home"],
        research_goal="Test appeal",
        optional_background_materials=["notes"],
        graph_visibility=GraphVisibility.Initial,
    )
    summary = brief.to_summary()
    assert summary["task_type"] == "concept_test"
    assert summary["product_concept_assets"] == ["proto.png"]
    assert summary["packaging_assets"] == []
    assert summary["variants"] == []
    assert summary["price_points"] == []


def test_new_task_types_in_supported_set():
    assert ConsumerTaskType.PackagingTest in ConsumerBusinessBrief.supported_task_types
    assert ConsumerTaskType.ABTest in ConsumerBusinessBrief.supported_task_types
    assert ConsumerTaskType.PriceTest in ConsumerBusinessBrief.supported_task_types


def test_brief_normalizes_legacy_variants_to_test_variants():
    brief = ConsumerBusinessBrief(
        task_type=ConsumerTaskType.ABTest,
        product_concept_assets=[],
        variants=["Legacy A", "Legacy B"],
        research_goal="Compare messaging",
    )
    assert len(brief.test_variants) == 2
    assert brief.test_variants[0].label == "Legacy A"
    assert brief.test_variants[0].variant_id == "v1"
    assert brief.test_variants[1].label == "Legacy B"
    assert brief.test_variants[1].variant_id == "v2"


def test_brief_preserves_structured_test_variants():
    from app.services.consumer.models import TestVariant
    brief = ConsumerBusinessBrief(
        task_type=ConsumerTaskType.ABTest,
        product_concept_assets=[],
        test_variants=[
            TestVariant(variant_id="control", label="Variant A", concept_assets=[], copy_material=[], claims=[]),
            TestVariant(variant_id="treatment", label="Variant B", concept_assets=[], copy_material=[], claims=[]),
        ],
        research_goal="Compare messaging",
    )
    assert len(brief.test_variants) == 2
    assert brief.test_variants[0].variant_id == "control"
    assert brief.test_variants[1].label == "Variant B"


def test_test_variants_takes_precedence_over_legacy_variants_in_model():
    from app.services.consumer.models import TestVariant
    brief = ConsumerBusinessBrief(
        task_type=ConsumerTaskType.ABTest,
        product_concept_assets=[],
        test_variants=[
            TestVariant(variant_id="new1", label="New A", concept_assets=[], copy_material=[], claims=[]),
            TestVariant(variant_id="new2", label="New B", concept_assets=[], copy_material=[], claims=[]),
        ],
        variants=["Legacy A", "Legacy B"],
        research_goal="Compare messaging",
    )
    assert len(brief.test_variants) == 2
    assert brief.test_variants[0].label == "New A"
    assert brief.test_variants[1].label == "New B"


def test_brief_price_context_stored_and_summarized():
    brief = ConsumerBusinessBrief(
        task_type=ConsumerTaskType.PriceTest,
        product_concept_assets=[],
        price_points=["$9.99"],
        price_context="Competitor benchmark: $8-$12",
        research_goal="Test price sensitivity",
    )
    assert brief.price_context == "Competitor benchmark: $8-$12"
    summary = brief.to_summary()
    assert summary["price_context"] == "Competitor benchmark: $8-$12"
