"""Behavioral guardrail tests for consumer dynamics.

These tests encode the EXPECTED behavior that a kernel adapter should
deliver. They intentionally FAIL against the current orchestrator to
expose two gaps:

  1. Quote generation is template-heavy — different personas with
     distinct expression styles, risk sensitivities, and herd tendencies
     produce identical quote text when seeing the same graph nodes.
  2. Attitude dynamics are too flat — the current stateless
     _generate_response treats attitude as a binary function of current
     node visibility, ignoring accumulated exposure history and
     persona-specific risk tolerance.

Both tests fail for the correct behavioral reason (not import/syntax).
"""

from __future__ import annotations

from app.services.consumer.orchestrator import ConsumerSimulationOrchestrator
from app.services.consumer.persona_pack import (
    load_default_persona_pack,
    map_persona_to_agent_traits,
)


# ---------------------------------------------------------------------------
# Guardrail 1: Quote variety across personas
# ---------------------------------------------------------------------------

def test_initial_round_quotes_vary_across_agents():
    """Different personas in round 0 should produce meaningfully varied quotes.

    A well-designed consumer kernel maps persona traits (expression_style,
    herd_tendency, risk_sensitivities, attention_drivers) to distinct
    quote language.  Today all agents receive the same template sentence
    because _generate_response ignores every persona-specific trait
    except herd_tendency — and even herd_tendency only gates on the
    round_num >= 1 branch, so round 0 quotes are always identical.

    EXPECTED:  len(set(quotes)) > 1
    ACTUAL:    len(set(quotes)) == 1   (FAIL)
    """
    orchestrator = ConsumerSimulationOrchestrator()
    personas = load_default_persona_pack()

    # All agents see the same non-risk graph context in round 0
    visible_nodes = [
        {"type": "ProductConcept", "visibility": "Initial", "text": "yogurt pouch for breakfast"},
    ]

    quotes: list[str] = []
    for persona in personas:
        profile = map_persona_to_agent_traits(persona)
        snapshot = orchestrator.build_round_snapshot(
            round_num=0,
            agent_traits={
                **profile["propagation_profile"],
                "influence_weight": profile["influence_weight"],
            },
            brief_summary="Pinned BusinessBrief Summary: yogurt pouch for commuters",
            visible_graph_nodes=visible_nodes,
            agent_id=profile["persona_id"],
            agent_name=profile["label"],
        )
        quotes.append(snapshot["quote"])

    # At minimum, distinct persona archetypes (analytical vs. emphatic vs.
    # brief) should NOT generate byte-identical quote strings.
    unique_quotes = set(quotes)
    assert len(unique_quotes) > 1, (
        f"All {len(personas)} personas produced identical round-0 quotes "
        f"because _generate_response uses a fixed template instead of "
        f"persona-specific expression traits.  Quote: {quotes[0]!r}"
    )


# ---------------------------------------------------------------------------
# Guardrail 2: Attitude dynamics under sustained risk exposure
# ---------------------------------------------------------------------------

def test_sustained_risk_exposure_moves_attitude_negative():
    """Agents exposed to risk across rounds should trend negative.

    A realistic consumer simulation should track cumulative risk exposure:
    agents that repeatedly encounter risk signals should show attitude
    drift toward negative, and this drift should vary by persona risk
    tolerance (risk_sensitivities, skepticism traits).

    The current orchestrator is stateless — _generate_response bases
    attitude solely on the current round's visible nodes.  This means:
      - Round 0 (no risk visible) → positive  (same for every persona)
      - Round 1 (risk visible)    → negative  (same for every persona)
      - Round 2 (risk visible)    → negative  (identical to round 1)

    The attitude never *moves* across rounds for a given visibility state;
    it is a pure function of node type, not accumulated exposure history.

    EXPECTED:  attitude sequence shows cross-round drift (round-2 attitude
               reflects prolonged exposure, not just current visibility)
    ACTUAL:    attitude is identical in round 1 and round 2 for every
               persona — no exposure memory exists                   (FAIL)
    """
    orchestrator = ConsumerSimulationOrchestrator()
    personas = load_default_persona_pack()

    product_node = {"type": "ProductConcept", "visibility": "Initial", "text": "yogurt pouch"}
    risk_node = {"type": "RiskPoint", "visibility": "Initial", "text": "sugar content concern"}

    # Simulate 3 rounds for every persona
    round_attitudes: dict[str, list[str]] = {p["persona_id"]: [] for p in personas}

    for round_num in range(3):
        # Risk is visible in every round >= 1 (sustained exposure)
        visible_nodes = [product_node]
        if round_num >= 1:
            visible_nodes.append(risk_node)

        for persona in personas:
            profile = map_persona_to_agent_traits(persona)
            snapshot = orchestrator.build_round_snapshot(
                round_num=round_num,
                agent_traits={
                    **profile["propagation_profile"],
                    "influence_weight": profile["influence_weight"],
                },
                brief_summary="Pinned BusinessBrief Summary: sugar content test",
                visible_graph_nodes=visible_nodes,
                agent_id=profile["persona_id"],
                agent_name=profile["label"],
            )
            round_attitudes[profile["persona_id"]].append(snapshot["attitude_label"])

    # --- Structural assertion ---
    # Every persona should NOT have an identical attitude value in
    # round 1 (first exposure) and round 2 (continued exposure), because
    # sustained exposure should compound the effect.
    for persona_id, attitudes in round_attitudes.items():
        assert attitudes[0] != attitudes[1], (
            f"Persona {persona_id}: round 0 attitude ({attitudes[0]!r}) should "
            f"differ from round 1 attitude ({attitudes[1]!r}) when risk appears."
        )

    # --- Exposure-memory assertion ---
    # The critical gap: if _generate_response had exposure memory,
    # round-2 attitudes would reflect *prolonged* risk contact and
    # differ from the round-1 first-reaction.  Today they are identical.
    all_identical_after_exposure = all(
        attitudes[1] == attitudes[2]
        for attitudes in round_attitudes.values()
    )
    assert not all_identical_after_exposure, (
        "Round 1 and round 2 attitudes are identical for every persona — "
        "_generate_response is stateless and has no exposure memory. "
        "Sustained risk contact should produce attitude drift (e.g. "
        "'neutral' → 'negative' for risk-tolerant personas), but the "
        "current code returns the same value regardless of exposure history. "
        f"Attitudes: {round_attitudes}"
    )
