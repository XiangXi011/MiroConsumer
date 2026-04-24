# Phase6D Smoke-Readiness Gate

## Purpose

No new feature work. This gate documents acceptance criteria and artefacts for the
full-phase smoke that will run after Phase6D closes. The smoke itself remains
deferred until the full phase is complete per user instruction.

## Scope

- Backend consumer simulation kernel / runtime
- Consumer API / reporting contract (snapshot schema, attitude / bucket / engagement domain)
- Branch / fork replay (fork_round > 0 with pre-fork PropagationState)
- Legacy fallback path (default kernel, no prior_state)
- Outputs and artefacts (JSONL, summary / report payloads, logs)

## Smoke Scenarios (deferred)

Run the following scenarios during the whole-phase smoke. Do not run them now.

a. **Normal end-to-end consumer run**
   - `consumer_rounds.jsonl` is created.
   - Summary / report data stays shaped correctly (keys, types, valid domains).

b. **Sustained-risk scenario**
   - Produces at least one negative attitude.
   - Does not collapse to all neutral.

c. **No-RiskPoint scenario**
   - Does not show abnormal negative drift.
   - Base positive / neutral paths remain stable.

d. **Quote diversity**
   - Repeated deterministic templates are reduced.
   - Uniqueness is inspected per agent / round.

e. **Cross-round propagation**
   - Cumulative risk, social reinforcement, and propagation-only / misread paths are
     observable in the output.

f. **Branch / fork at fork_round > 0**
   - Carries pre-fork PropagationState into the forked branch.
   - Divergence occurs only after the fork round.

g. **Legacy fallback / parity**
   - Remains available through `ConsumerSimulationOrchestrator` default kernel with
     no `prior_state`.
   - Output matches the standalone `LegacySimulationKernel` byte-for-byte.

## Suggested Artefacts to Capture

| Artefact | What to verify |
|---|---|
| `consumer_rounds.jsonl` | Valid JSONL, all expected keys, types correct, engagement 1..10 |
| Branch round JSONL | Divergence only after fork, pre-fork state carried forward |
| Consumer summary / report payload | Schema stability, no missing fields |
| Attitude distribution table | At least one negative in sustained-risk, no all-neutral collapse |
| Quote uniqueness sample | Templates vary across agents / rounds when hybrid path is active |
| Failure logs | No unhandled exceptions, no schema violations |

## Gate Outcome Levels

- **PASS** - All scenarios produce expected artefacts and no regressions.
- **WARN** - Minor divergence in quote diversity or edge-case engagement values;
  documented and triaged before the next phase.
- **FAIL** - Schema breakage, legacy parity loss, or abnormal negative drift;
  blocks Phase6 close.

## Deferral Note

Manual smoke execution remains deferred until the full phase is complete per user
instruction. This document defines the criteria only.
