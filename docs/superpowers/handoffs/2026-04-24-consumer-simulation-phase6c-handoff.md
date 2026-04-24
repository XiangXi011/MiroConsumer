# Consumer Simulation Phase 6C Handoff - Preserve-First Kernel Upgrade

**Date:** 2026-04-24
**Branch:** `codex/phase5-closure`
**Implementation Scope:** backend consumer simulation kernel/runtime only; this closeout commit is docs-only.

---

## 1. Phase 6C Outcome and Scope

Phase 6C fixed the two core consumer simulation deficiencies identified in Phase 6B:

1. **Template-heavy output with near-zero quote diversity** - the legacy `_generate_response()` selected from ~4 hardcoded f-strings, producing near-identical quotes across agents and rounds.
2. **Near-zero cross-round propagation dynamics** - no per-agent round state was maintained between rounds, so agents reacted only to the current round's visible nodes.

The solution introduced a kernel adapter interface with three layers:
- `SimulationKernelAdapter` ABC + `SimulationKernelResult` typed output
- `LegacySimulationKernel` - byte-for-byte deterministic fallback preserving pre-Phase6C behavior
- `HybridSimulationKernel` - uses prior-round state, persona traits, finding diversity, and topology signals to produce varied quotes and meaningful attitude movement
- `PropagationState` - per-agent round-to-round mutable state (attitude history, engagement history, cumulative risk exposure, social reinforcement count)

All downstream typed outputs (`attitude_label`, `bucket`, `quote`, `engagement`, `visible_finding_ids`, `propagation_events`, consumer summary, report context, replay JSONL) remain identical in shape. No frontend, API routes, or persistence changes were made.

---

## 2. Commit List / Major Implementation Chunks

| Commit | Message |
|--------|---------|
| `634be6b` | `refactor: introduce kernel adapter ABC and legacy deterministic kernel fallback` - `SimulationKernelAdapter`, `SimulationKernelResult`, `LegacySimulationKernel`, contract tests |
| `f400085` | `feat: add PropagationState model for consumer round-to-round memory` - per-agent state tracking across rounds |
| `bc1dcea` | `feat: add HybridSimulationKernel with preserve-first quote variety and parity tests` - pooled quote templates, cross-round attitude adjustments, deterministic seeded RNG |
| `825340b` | `test: add hybrid kernel threshold and anti-overfit coverage` - cumulative-risk threshold, reinforcement threshold, propagation-only patience limit, negative-trigger scenarios |
| `aeab6aa` | `feat: wire hybrid consumer kernel into runner paths with stateful branch replay` - `_run_consumer_simulation()` and `run_branch_simulation()` maintain `agent_states` dict, pass prior state, reconstruct branch state from pre-fork seed rounds |

---

## 3. Six Strengthening Points and Coverage

| Strengthening Point | Where Covered |
|---------------------|---------------|
| `SimulationKernelResult.engagement` validates 1..10 | `test_kernel_adapter.py::TestSimulationKernelResult::test_engagement_must_be_in_bounds` |
| Legacy byte-for-byte coverage: RiskPoint, round-0 non-risk, round>=1 herd high/medium, empty visible_nodes | `test_kernel_adapter.py` legacy parity tests; `test_orchestrator.py` existing contract tests |
| Hybrid quote deterministic diversity includes detail hash to reduce collisions | `hybrid_kernel.py` `_seeded_rng()` seeds from `agent_id:round_num:bucket` + SHA256; `test_hybrid_kernel.py::test_quotes_vary_across_agents_same_round` |
| `prior_state=None` parity is explicitly tested | `test_kernel_adapter.py` - legacy callers omitting `prior_state` get identical behavior |
| Branch/fork state reconstructs `PropagationState` from pre-fork seed rounds | `simulation_runner.py` `run_branch_simulation()` replays parent rounds into fresh `PropagationState` before forked rounds begin |
| Negative-trigger and anti-overfit no-RiskPoint scenarios are tested | `test_hybrid_kernel.py` threshold tests; `test_consumer_dynamics.py` guardrails |

---

## 4. Verification Run by Codex Audit

| Suite | Command | Result |
|-------|---------|--------|
| Targeted backend (new kernel files) | `python -m pytest tests/consumer/test_hybrid_kernel.py tests/consumer/test_kernel_adapter.py tests/consumer/test_consumer_dynamics.py tests/consumer/test_orchestrator.py -v` | **84 passed, 1 warning** |
| Consumer + API + contracts | `python -m pytest tests/consumer/ tests/api/test_consumer_routes.py tests/api/test_consumer_canonical_routes.py tests/contracts/test_consumer_contracts.py tests/api/test_consumer_interventions.py -v` | **568 passed, 1 warning** |
| Full backend | `python -m pytest tests/ --tb=short -q` | **717 passed, 1 warning in 121.94s** |

The single warning is the existing `zep_cloud`/Pydantic v1 compatibility warning on Python 3.14 - unrelated to this phase.

---

## 5. Smoke / Manual End-to-End

Intentionally deferred per user instruction until the whole phase is complete.

---

## 6. Residual Risks / Next Tasks

1. **Manual smoke test** - run a full end-to-end simulation via the API or script and visually inspect quote variety and attitude distribution.
2. **Monitor real-output attitude distribution** - in production or staging, verify that attitude labels are not artificially skewed; tune `_RISK_CUMULATIVE_NEGATIVE_THRESHOLD`, `_REINFORCEMENT_POSITIVE_THRESHOLD`, and `_PROPAGATION_ONLY_PATIENCE_LIMIT` if needed.
3. **Optional cleanup** - a few comments/docstrings in `hybrid_kernel.py` and `test_hybrid_kernel.py` contain garbled encoding artifacts. These are cosmetic and can be cleaned up in a follow-up if desired.
