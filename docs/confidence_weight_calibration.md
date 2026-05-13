# Confidence Weight Calibration Methodology

Status: pending_expert_review
Last updated: 2026-05-12

MiroConsumer computes finding confidence with four explicit weights:

| Component | Weight | Rationale |
| --- | ---: | --- |
| Source quality | 0.35 | Rewards trusted uploaded or first-party evidence. |
| Evidence sufficiency | 0.35 | Rewards findings that are directly backed by retrieved snippets. |
| Signal consistency | 0.20 | Rewards agreement among findings of the same type. |
| Replay alignment | 0.10 | Rewards stability across benchmark or replay runs. |

The current weights are accepted as the production baseline only when benchmark
history is too small for a statistically meaningful refit. The calibration
script produces a machine-readable report and is designed to be rerun when a
JSONL file of labelled findings is available.

## Calibration Procedure

1. Collect labelled findings with `source`, `evidence`, `signal`, `replay`, and
   `is_correct` fields.
2. Run `uv run python scripts/calibrate_confidence_weights.py --input <jsonl>`.
3. Review the resulting weight distribution, accuracy, and expected calibration
   error.
4. Keep the baseline weights if the sample has fewer than 50 labelled findings
   or if the fitted weights differ by less than 10 percent.
5. Require three-person expert review before replacing the production baseline.

## Expert Review Checklist

- Consumer research expert validates source and evidence weighting.
- Market analysis expert validates signal consistency interpretation.
- Data science reviewer validates calibration sample size and error metrics.
- Reviewers confirm that replay alignment is based on non-placeholder scores.
