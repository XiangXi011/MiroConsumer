from pathlib import Path
import sys


BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.consumer.graph_builder import ConsumerGraphBuilder
from app.services.consumer.models import ConsumerBusinessBrief, ConsumerTaskType, GraphVisibility, ResearchFinding


def _build_brief() -> ConsumerBusinessBrief:
    return ConsumerBusinessBrief(
        task_type=ConsumerTaskType.ConceptTest,
        product_concept_assets=["Glow serum stick", "Pocket-size refill pack"],
        copy_material=["Brighter skin in one swipe"],
        claims=["Derm-tested glow boost"],
        target_audience=["busy commuters"],
        usage_scene=["morning commute"],
        research_goal="Understand first-impression appeal",
        optional_background_materials=[
            "Some shoppers may repeat that the finish spreads quickly through group chats.",
        ],
        graph_visibility=GraphVisibility.Initial,
    )


def test_consumer_graph_builder_marks_product_concepts_initial():
    graph = ConsumerGraphBuilder().build(
        brief=_build_brief(),
        background_text="A competitor says the formula is difficult to stabilize at scale.",
        persona_pack=[],
        graph_id="consumer_proj_demo",
    )

    concept_nodes = [node for node in graph["nodes"] if "ProductConcept" in node["labels"]]

    assert concept_nodes
    assert all(node["visibility"] == GraphVisibility.Initial.value for node in concept_nodes)
    assert all(node["attributes"]["visibility"] == GraphVisibility.Initial.value for node in concept_nodes)


def test_background_risk_nodes_are_never_initial():
    graph = ConsumerGraphBuilder().build(
        brief=_build_brief(),
        background_text=(
            "The finish may spread quickly as a hot topic among beauty creators. "
            "There is also a deeper technical contamination risk if manufacturing slips."
        ),
        persona_pack=[],
        graph_id="consumer_proj_risks",
    )

    risk_nodes = [node for node in graph["nodes"] if "RiskPoint" in node["labels"]]

    assert risk_nodes
    assert all(node["visibility"] != GraphVisibility.Initial.value for node in risk_nodes)
    assert any(node["visibility"] == GraphVisibility.Propagation_Only.value for node in risk_nodes)
    assert any(node["visibility"] == GraphVisibility.Restricted.value for node in risk_nodes)


def test_consumer_graph_builder_rejects_malformed_persona_pack_records():
    builder = ConsumerGraphBuilder()

    try:
        builder.build(
            brief=_build_brief(),
            background_text="Background risk.",
            persona_pack=[{"persona_id": "p1", "label": "Bad Persona"}],
            graph_id="consumer_proj_bad_persona",
        )
    except ValueError as exc:
        assert "missing required fields" in str(exc).lower()
    else:
        raise AssertionError("Expected malformed persona pack to raise ValueError")


def test_graph_builder_adds_research_findings_with_visibility():
    graph = ConsumerGraphBuilder().build(
        brief=_build_brief(),
        background_text="Background risk.",
        persona_pack=[],
        graph_id="consumer_proj_research",
        research_findings=[
            ResearchFinding(
                finding_id="r1",
                finding_type="risk_signal",
                summary="Sweetener concern",
                visibility=GraphVisibility.Restricted,
            )
        ],
    )

    research_nodes = [node for node in graph["nodes"] if "ResearchFinding" in node["labels"]]
    assert research_nodes[0]["visibility"] == "Restricted"
    assert research_nodes[0]["attributes"]["provenance"]["source_label"] == "brief_background"


def test_packaging_test_creates_packaging_cue_nodes():
    brief = ConsumerBusinessBrief(
        task_type=ConsumerTaskType.PackagingTest,
        product_concept_assets=[],
        packaging_assets=["box-front.png", "label-detail.png"],
        research_goal="Evaluate shelf appeal",
    )
    graph = ConsumerGraphBuilder().build(
        brief=brief,
        persona_pack=[],
        graph_id="consumer_proj_pkg",
    )

    cue_nodes = [node for node in graph["nodes"] if "PackagingCue" in node["labels"]]
    assert len(cue_nodes) == 2
    assert all(node["visibility"] == GraphVisibility.Initial.value for node in cue_nodes)
    assert all(node["attributes"]["round0_visible"] is True for node in cue_nodes)


def test_ab_test_creates_variant_nodes():
    brief = ConsumerBusinessBrief(
        task_type=ConsumerTaskType.ABTest,
        product_concept_assets=[],
        variants=["Headline A", "Headline B"],
        research_goal="Compare messaging",
    )
    graph = ConsumerGraphBuilder().build(
        brief=brief,
        persona_pack=[],
        graph_id="consumer_proj_ab",
    )

    variant_nodes = [node for node in graph["nodes"] if "Variant" in node["labels"]]
    assert len(variant_nodes) == 2
    assert all(node["visibility"] == GraphVisibility.Initial.value for node in variant_nodes)
    assert all(node["attributes"]["round0_visible"] is True for node in variant_nodes)


def test_price_test_creates_price_point_nodes():
    brief = ConsumerBusinessBrief(
        task_type=ConsumerTaskType.PriceTest,
        product_concept_assets=[],
        price_points=["$9.99", "$12.99", "$14.99"],
        research_goal="Test price sensitivity",
    )
    graph = ConsumerGraphBuilder().build(
        brief=brief,
        persona_pack=[],
        graph_id="consumer_proj_price",
    )

    price_nodes = [node for node in graph["nodes"] if "PricePoint" in node["labels"]]
    assert len(price_nodes) == 3
    assert all(node["visibility"] == GraphVisibility.Initial.value for node in price_nodes)
    assert all(node["attributes"]["round0_visible"] is True for node in price_nodes)


def test_new_task_types_generate_secondary_topics():
    brief = ConsumerBusinessBrief(
        task_type=ConsumerTaskType.ABTest,
        product_concept_assets=[],
        variants=["Headline A variant text", "Headline B variant text"],
        copy_material=["Main body copy"],
        research_goal="Compare messaging",
    )
    graph = ConsumerGraphBuilder().build(
        brief=brief,
        persona_pack=[],
        graph_id="consumer_proj_ab_topics",
    )

    talking_nodes = [node for node in graph["nodes"] if "TalkingPoint" in node["labels"]]
    assert any("Main body copy" in node["name"] for node in talking_nodes)
    assert any("Headline A variant text" in node["name"] for node in talking_nodes)
    assert all(node["visibility"] == GraphVisibility.Propagation_Only.value for node in talking_nodes)


def test_ab_test_with_test_variant_objects_creates_variant_nodes():
    from app.services.consumer.models import TestVariant
    brief = ConsumerBusinessBrief(
        task_type=ConsumerTaskType.ABTest,
        product_concept_assets=[],
        test_variants=[
            TestVariant(variant_id="v1", label="Variant A", concept_assets=[], copy_material=[], claims=[]),
            TestVariant(variant_id="v2", label="Variant B", concept_assets=[], copy_material=[], claims=[]),
        ],
        research_goal="Compare messaging",
    )
    graph = ConsumerGraphBuilder().build(
        brief=brief,
        persona_pack=[],
        graph_id="consumer_proj_ab_obj",
    )

    variant_nodes = [node for node in graph["nodes"] if "Variant" in node["labels"]]
    assert len(variant_nodes) == 2
    assert any(node["name"] == "Variant A" for node in variant_nodes)
    assert any(node["name"] == "Variant B" for node in variant_nodes)
    assert all(node["visibility"] == GraphVisibility.Initial.value for node in variant_nodes)


def test_price_test_with_price_context_builds_graph():
    brief = ConsumerBusinessBrief(
        task_type=ConsumerTaskType.PriceTest,
        product_concept_assets=[],
        price_points=["$9.99", "$12.99"],
        price_context="Competitor range: $8-$15",
        research_goal="Test price sensitivity",
    )
    graph = ConsumerGraphBuilder().build(
        brief=brief,
        persona_pack=[],
        graph_id="consumer_proj_price_ctx",
    )

    price_nodes = [node for node in graph["nodes"] if "PricePoint" in node["labels"]]
    assert len(price_nodes) == 2
    assert any(node["name"] == "$9.99" for node in price_nodes)
    assert any(node["name"] == "$12.99" for node in price_nodes)
