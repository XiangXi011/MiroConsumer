from pathlib import Path
import sys


BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.consumer.graph_builder import ConsumerGraphBuilder
from app.services.consumer.models import ConsumerBusinessBrief, ConsumerTaskType, GraphVisibility


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
