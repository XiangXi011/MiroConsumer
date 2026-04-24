"""Behavioral guardrail tests for consumer dynamics.

These tests validate the explicit hybrid kernel path (not the legacy
default facade). They prove that:

  1. Quote generation varies across personas when the hybrid kernel
     receives per-agent prior_state.
  2. Attitude dynamics carry memory — accumulated risk exposure in
     prior_state pushes later non-risk rounds negative, while the
     same round without prior_state remains positive.
"""

from __future__ import annotations

from app.services.consumer.hybrid_kernel import HybridSimulationKernel
from app.services.consumer.orchestrator import ConsumerSimulationOrchestrator
from app.services.consumer.persona_pack import (
    load_default_persona_pack,
    map_persona_to_agent_traits,
)
from app.services.consumer.propagation_state import create_initial_state


# ---------------------------------------------------------------------------
# Guardrail 1: Quote variety across personas (explicit hybrid path)
# ---------------------------------------------------------------------------

def test_initial_round_quotes_vary_across_agents():
    """Different personas in round 0 should produce meaningfully varied quotes.

    The hybrid kernel's template-pool path is triggered when prior_state
    is provided.  Selection is seeded by agent_id, so distinct personas
    should receive distinct quotes even with identical visible nodes.
    """
    orchestrator = ConsumerSimulationOrchestrator(
        kernel=HybridSimulationKernel()
    )
    personas = load_default_persona_pack()

    visible_nodes = [
        {"type": "ProductConcept", "visibility": "Initial", "text": "yogurt pouch for breakfast"},
    ]

    quotes: list[str] = []
    for persona in personas:
        profile = map_persona_to_agent_traits(persona)
        agent_id = profile["persona_id"]
        prior_state = create_initial_state(agent_id).to_prior_state_dict()
        snapshot = orchestrator.build_round_snapshot(
            round_num=0,
            agent_traits={
                **profile["propagation_profile"],
                "influence_weight": profile["influence_weight"],
            },
            brief_summary="Pinned BusinessBrief Summary: yogurt pouch for commuters",
            visible_graph_nodes=visible_nodes,
            agent_id=agent_id,
            agent_name=profile["label"],
            prior_state=prior_state,
        )
        quotes.append(snapshot["quote"])

    unique_quotes = set(quotes)
    assert len(unique_quotes) > 1, (
        f"All {len(personas)} personas produced identical round-0 quotes "
        f"through the hybrid kernel. Quotes: {quotes!r}"
    )


# ---------------------------------------------------------------------------
# Guardrail 2: Attitude dynamics under sustained risk exposure
# ---------------------------------------------------------------------------

def test_sustained_risk_exposure_moves_attitude_negative():
    """Agents exposed to risk across rounds should trend negative via state memory.

    The hybrid kernel tracks cumulative_risk_exposure in prior_state.
    After two rounds of risk exposure (threshold >= 2), a later round
    with no visible RiskPoint should still be pushed negative because
    the prior_state carries the accumulated exposure.

    We also prove that the same later round WITHOUT prior_state would
    not be negative, isolating the state-memory effect.
    """
    orchestrator = ConsumerSimulationOrchestrator(
        kernel=HybridSimulationKernel()
    )
    personas = load_default_persona_pack()

    product_node = {"type": "ProductConcept", "visibility": "Initial", "text": "yogurt pouch"}
    risk_node = {"type": "RiskPoint", "visibility": "Initial", "text": "sugar content concern"}
    talking_node = {"type": "TalkingPoint", "visibility": "Initial", "text": "great taste"}

    # Pick a single representative persona for the controlled comparison.
    persona = next(p for p in personas if p["persona_id"] == "M01")
    profile = map_persona_to_agent_traits(persona)
    agent_id = profile["persona_id"]
    agent_traits = {
        **profile["propagation_profile"],
        "influence_weight": profile["influence_weight"],
    }

    state = create_initial_state(agent_id)

    # Round 0: no risk → base positive/resonance
    snap0 = orchestrator.build_round_snapshot(
        round_num=0,
        agent_traits=agent_traits,
        brief_summary="Pinned BusinessBrief Summary: sugar content test",
        visible_graph_nodes=[product_node],
        agent_id=agent_id,
        agent_name=profile["label"],
        prior_state=state.to_prior_state_dict(),
    )
    state.update(
        attitude_label=snap0["attitude_label"],
        engagement=snap0["engagement"],
        bucket=snap0["bucket"],
        visible_nodes=snap0.get("visible_nodes", []),
    )

    # Round 1: risk visible → negative/risk (base path); cumulative_risk=1
    snap1 = orchestrator.build_round_snapshot(
        round_num=1,
        agent_traits=agent_traits,
        brief_summary="Pinned BusinessBrief Summary: sugar content test",
        visible_graph_nodes=[product_node, risk_node],
        agent_id=agent_id,
        agent_name=profile["label"],
        prior_state=state.to_prior_state_dict(),
    )
    state.update(
        attitude_label=snap1["attitude_label"],
        engagement=snap1["engagement"],
        bucket=snap1["bucket"],
        visible_nodes=snap1.get("visible_nodes", []),
    )
    assert state.cumulative_risk_exposure == 1

    # Round 2: risk visible again → negative/risk (base path); cumulative_risk=2
    snap2 = orchestrator.build_round_snapshot(
        round_num=2,
        agent_traits=agent_traits,
        brief_summary="Pinned BusinessBrief Summary: sugar content test",
        visible_graph_nodes=[product_node, risk_node],
        agent_id=agent_id,
        agent_name=profile["label"],
        prior_state=state.to_prior_state_dict(),
    )
    state.update(
        attitude_label=snap2["attitude_label"],
        engagement=snap2["engagement"],
        bucket=snap2["bucket"],
        visible_nodes=snap2.get("visible_nodes", []),
    )
    assert state.cumulative_risk_exposure == 2

    # Round 3: no risk visible, only talking node.
    # Base path would yield positive/resonance (round 0, talking node).
    # With prior_state carrying cumulative_risk_exposure=2, hybrid kernel
    # should push positive → negative.
    snap3_with_state = orchestrator.build_round_snapshot(
        round_num=3,
        agent_traits=agent_traits,
        brief_summary="Pinned BusinessBrief Summary: sugar content test",
        visible_graph_nodes=[talking_node],
        agent_id=agent_id,
        agent_name=profile["label"],
        prior_state=state.to_prior_state_dict(),
    )

    # Same round 3 WITHOUT prior_state — should follow the base path.
    snap3_without_state = orchestrator.build_round_snapshot(
        round_num=3,
        agent_traits=agent_traits,
        brief_summary="Pinned BusinessBrief Summary: sugar content test",
        visible_graph_nodes=[talking_node],
        agent_id=agent_id,
        agent_name=profile["label"],
        prior_state=None,
    )

    # With accumulated risk state, a non-risk round should still be negative.
    assert snap3_with_state["attitude_label"] == "negative", (
        f"Expected negative attitude when cumulative_risk_exposure={state.cumulative_risk_exposure} "
        f"but got {snap3_with_state['attitude_label']!r}. Prior state memory is not affecting attitude."
    )

    # Without prior_state, the same round should NOT be negative.
    assert snap3_without_state["attitude_label"] != "negative", (
        f"Expected non-negative attitude without prior_state but got "
        f"{snap3_without_state['attitude_label']!r}. The base path should be unaffected."
    )

    # The contrast proves state memory is the cause of the negative shift.
    assert snap3_with_state["attitude_label"] != snap3_without_state["attitude_label"], (
        f"With and without prior_state should diverge for the same visible nodes. "
        f"Got with_state={snap3_with_state['attitude_label']!r}, "
        f"without_state={snap3_without_state['attitude_label']!r}"
    )
