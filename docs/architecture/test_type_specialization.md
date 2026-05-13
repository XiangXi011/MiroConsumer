# Test Type Specialization Architecture

P1-012 moves test-type differentiation from prompt-only behavior into explicit runtime signals. The implementation is intentionally small and deterministic so it can be verified in unit and integration tests.

## Profile Layer

`TestTypeProfile` is defined in `backend/app/services/consumer/domain/test_type_profiles.py`. Each profile includes:

- `focus_line` for backward-compatible prompts
- `PerceptionParams` for perception-layer behavior
- `DecisionParams` for decision-layer behavior
- scoring weights for downstream reporting and confidence summaries

Unknown task types fall back to `concept_test`.

## Perception layer

The Perception layer is implemented in `backend/app/services/consumer/society/perception_layer.py`.

- Packaging Test enables visual attention and outputs `visual_attention_heatmap`, `visual_attention_score`, and `shelf_context_simulated`.
- Copy Test outputs independent element attention for headline, body, and CTA.
- Other tests use `generic_perception` to preserve existing behavior.

## Decision layer

The Decision layer is implemented in `backend/app/services/consumer/society/decision_layer.py`.

- Price Test uses the `gabor_granger` mode, price sensitivity category, reference price comparison, acceptance probability, and elasticity signal.
- A/B Test uses `paired_comparison`, variant scores, ranking, preference strength, and choice-set independence check.
- Other tests use `generic_decision`.

## Orchestrator data flow

`ConsumerSimulationOrchestrator.build_round_snapshot()` resolves the profile, computes perception and decision signals, then stores these fields in every snapshot:

- `test_type_profile`
- `perception_signals`
- `decision_signals`

The legacy kernel still produces attitude, bucket, quote, and engagement so concept-test regression behavior remains stable while richer profile signals become available to reports and later simulation kernels.