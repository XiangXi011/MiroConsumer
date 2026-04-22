# Consumer Simulation Phase 4A Credibility Upgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver Phase 4A for `consumer_test` by adding source quality scoring, stronger Lane B governance, evidence validation, confidence scoring, and benchmark replay without breaking the existing MiroFish workflow.

**Architecture:** Keep the existing `/api/graph -> /api/simulation -> /api/report` backbone and extend the `backend/app/services/consumer/` package with a credibility layer that attaches machine-readable quality, validation, and confidence fields to research sources, findings, reports, and comparisons. The UI should surface these signals in Step 2, Step 4, and Step 5, while benchmark replay should persist repo-local artifacts for calibration.

**Tech Stack:** Flask, existing MiroFish simulation/report stack, repo-local JSON persistence, pytest, Vue 3 + Vite, Axios, locale JSON

---

## Constraints And Working Rules

- `consumer_test` remains the only Phase 4A entry point.
- `project_type=default` behavior must remain unchanged.
- Lane A user materials outrank Lane B public-web supplements.
- Confidence must be backed by structured fields, not only prose.
- Every task ends with focused verification before commit.
- Keep file boundaries narrow; add new focused modules under `backend/app/services/consumer/`.

## Execution Order

1. `Task Group 1`: Source quality model and persistence
2. `Task Group 2`: Lane B governance and retrieval trace upgrade
3. `Task Group 3`: Evidence validator and confidence scoring
4. `Task Group 4`: Report/UI confidence exposure
5. `Task Group 5`: Benchmark registry and replay
6. `Task Group 6`: Final verification, docs, and handoff

## Task Group 1: Source Quality Model And Persistence

**Files:**
- Create: `backend/app/services/consumer/source_quality.py`
- Create: `backend/tests/consumer/test_source_quality.py`
- Modify: `backend/app/services/consumer/__init__.py`
- Modify: `backend/app/services/consumer/models.py`
- Modify: `backend/app/services/consumer/source_registry.py`
- Modify: `backend/app/services/consumer/project_research_persistence.py`
- Modify: `backend/app/services/consumer/research_ingest.py`
- Modify: `backend/app/api/graph.py`

- [ ] Write failing tests for deterministic source quality scoring across Lane A and Lane B sources.
- [ ] Run `Set-Location backend; .\.venv\Scripts\python.exe -m pytest tests/consumer/test_source_quality.py -q` and confirm failure.
- [ ] Implement source quality scoring with:
  - `trust_tier`
  - `freshness_score`
  - `source_confidence`
  - `coverage_tags`
  - `quality_reasons`
- [ ] Reuse existing model fields instead of duplicating them:
  - keep `ResearchSource.trust_tier` as the primary trust bucket
  - keep `ResearchFinding.confidence` as the numeric base field
  - add companion metadata / summary fields for reasons and labels
- [ ] Persist source quality artifacts into the project research workspace.
- [ ] Wire the new scorer into:
  - `resolve_research_findings()`
  - `build_research_snapshot()`
  - `_build_consumer_graph()` so `project.consumer_context` carries source quality summary
- [ ] Extend source/finding models so quality snapshots can be read from graph build and report flows.
- [ ] Export any new helpers through `backend/app/services/consumer/__init__.py` if the existing import pattern requires it.
- [ ] Run `Set-Location D:\project\MiroFish\.worktrees\consumer-simulation-phase1\backend; .\.venv\Scripts\python.exe -m pytest tests/consumer/test_source_quality.py -q` again and confirm pass.
- [ ] Commit with message: `feat: add consumer source quality scoring`

## Task Group 2: Lane B Governance And Retrieval Trace Upgrade

**Files:**
- Modify: `backend/app/services/consumer/lane_b_provider.py`
- Modify: `backend/app/services/consumer/retrieval.py`
- Modify: `backend/app/services/consumer/finding_distiller.py`
- Create: `backend/tests/consumer/test_lane_b_governance.py`
- Modify: `backend/tests/consumer/test_lane_b_provider.py`

- [ ] Write failing tests for duplicate filtering, weak-snippet rejection, and governance reason persistence.
- [ ] Run targeted tests and confirm failure.
- [ ] Implement stronger Lane B governance with:
  - minimum snippet quality checks
  - duplicate suppression
  - source downgrade rules
  - accepted-vs-rejected trace recording
- [ ] Wire governance into the existing Lane B path so:
  - `lane_b_provider.py` produces governed candidates
  - `retrieval.py` records governance decisions in traces
  - `finding_distiller.py` only distills accepted evidence
- [ ] Ensure public-web findings preserve both normalized evidence and governance metadata.
- [ ] Re-run targeted tests and confirm pass.
- [ ] Run `Set-Location backend; .\.venv\Scripts\python.exe -m pytest tests/consumer/test_lane_b_provider.py tests/consumer/test_lane_b_governance.py -q`.
- [ ] Commit with message: `feat: strengthen lane b governance`

## Task Group 3: Evidence Validator And Confidence Scoring

**Files:**
- Create: `backend/app/services/consumer/evidence_validator.py`
- Create: `backend/app/services/consumer/confidence_scoring.py`
- Create: `backend/tests/consumer/test_evidence_validator.py`
- Create: `backend/tests/consumer/test_confidence_scoring.py`
- Modify: `backend/app/services/consumer/__init__.py`
- Modify: `backend/app/services/consumer/scoring.py`
- Modify: `backend/app/services/consumer/report_context.py`
- Modify: `backend/app/services/consumer/comparison_engine.py`
- Modify: `backend/app/api/simulation.py`
- Modify: `backend/app/api/report.py`

- [ ] Write failing tests for:
  - supported vs weakly supported findings
  - finding-level confidence labels
  - report/comparison confidence outputs
- [ ] Run targeted tests and confirm failure.
- [ ] Implement evidence validation with machine-readable statuses:
  - `supported`
  - `weak_support`
  - `insufficient_support`
- [ ] Implement confidence scoring using:
  - source quality
  - evidence sufficiency
  - signal consistency
  - replay alignment placeholder
- [ ] Wire the new services into existing runtime flows:
  - validate findings after distillation and before report context assembly
  - compute confidence in `scoring.py` for run summaries
  - expose confidence in `report_context.py` and `comparison_engine.py`
  - gate these fields so only `consumer_test` routes return them
- [ ] Attach confidence fields to consumer summary, report context, and comparison snapshot.
- [ ] Re-run targeted tests and confirm pass.
- [ ] Export any new helpers through `backend/app/services/consumer/__init__.py` if required by current imports.
- [ ] Commit with message: `feat: add consumer evidence validation and confidence scoring`

## Task Group 4: Report And UI Confidence Exposure

**Files:**
- Modify: `frontend/src/components/Step2EnvSetup.vue`
- Modify: `frontend/src/components/Step4Report.vue`
- Modify: `frontend/src/components/Step5Interaction.vue`
- Modify: `frontend/src/utils/consumerMode.js`
- Modify: `frontend/src/api/report.js`
- Modify: `frontend/src/api/simulation.js`
- Modify: `frontend/tests/consumerMode.test.js`
- Modify: `frontend/tests/consumerBrief.test.js`
- Modify: `frontend/tests/pendingUpload.test.js`
- Modify: `locales/en.json`
- Modify: `locales/zh.json`

- [ ] Write failing frontend tests for:
  - source quality summary cards
  - finding confidence display mapping
  - low-confidence follow-up prompts
- [ ] Run `node --test frontend/tests/consumerMode.test.js frontend/tests/consumerBrief.test.js frontend/tests/pendingUpload.test.js` and confirm targeted failures.
- [ ] Implement Step 2 quality summary display.
- [ ] Implement Step 4 evidence sufficiency / confidence display and comparison confidence display.
- [ ] Implement Step 5 prompts for weak evidence, low confidence, and replay drift.
- [ ] Re-run targeted frontend tests and confirm pass.
- [ ] Run `Set-Location D:\project\MiroFish\.worktrees\consumer-simulation-phase1\frontend; npm run build`.
- [ ] Commit with message: `feat: surface consumer credibility signals in ui`

## Task Group 5: Benchmark Registry And Replay

**Files:**
- Create: `backend/app/services/consumer/benchmark_registry.py`
- Create: `backend/app/services/consumer/benchmark_replay.py`
- Create: `backend/tests/consumer/test_benchmark_registry.py`
- Create: `backend/tests/consumer/test_benchmark_replay.py`
- Modify: `backend/app/api/report.py`
- Modify: `backend/app/services/report_agent.py`
- Modify: `frontend/src/api/report.js`
- Modify: `frontend/src/components/Step4Report.vue`
- Modify: `frontend/src/components/Step5Interaction.vue`

- [ ] Write failing tests for benchmark registration, replay artifact persistence, and replay alignment output.
- [ ] Run targeted backend tests and confirm failure.
- [ ] Implement repo-local benchmark storage under `backend/uploads/benchmarks/`.
- [ ] Implement replay flow that registers benchmark metadata, executes replay, and persists:
  - manifest
  - expected signals
  - replay result
- [ ] Add report APIs for benchmark register/list/replay/fetch.
- [ ] Update `report_agent.py` only where necessary to:
  - expose replay alignment in generated report context
  - avoid mixing replay summaries into default-mode report paths
- [ ] Add Step 4 replay status and Step 5 replay-aware prompts.
- [ ] Re-run targeted backend and frontend tests and confirm pass.
- [ ] Commit with message: `feat: add consumer benchmark replay calibration`

## Task Group 6: Final Verification, Docs, And Handoff

**Files:**
- Modify: `PRD.md`
- Modify: `docs/superpowers/specs/2026-04-22-consumer-simulation-phase4a-credibility-upgrade-design.md`
- Create: `docs/superpowers/handoffs/2026-04-22-consumer-simulation-phase4a-handoff.md`
- Modify: `README.md`
- Modify: `README-ZH.md`

- [ ] Run full backend verification:
  - `Set-Location D:\project\MiroFish\.worktrees\consumer-simulation-phase1\backend; .\.venv\Scripts\python.exe -m pytest tests -q --ignore=tests/integration`
- [ ] Run targeted frontend verification:
  - `Set-Location D:\project\MiroFish\.worktrees\consumer-simulation-phase1; node --test frontend/tests/consumerMode.test.js frontend/tests/consumerBrief.test.js frontend/tests/pendingUpload.test.js`
- [ ] Run frontend build:
  - `Set-Location D:\project\MiroFish\.worktrees\consumer-simulation-phase1\frontend; npm run build`
- [ ] Manually smoke one consumer workflow:
  - build graph with research enabled
  - prepare simulation
  - inspect confidence-bearing summary
  - export or view benchmark/replay state
- [ ] Update docs with actual acceptance results, known limits, and next steps.
- [ ] Commit with message: `docs: record phase4a credibility upgrade status`

## Global Acceptance Gate

- [ ] Source quality summaries exist in project research artifacts.
- [ ] Lane B public-web evidence passes through stronger governance before surfacing.
- [ ] Findings expose machine-readable evidence validation and confidence fields.
- [ ] Report and comparison outputs expose confidence reasons, not only labels.
- [ ] Step 2 / Step 4 / Step 5 surface credibility signals without breaking current `consumer_test` flow.
- [ ] Benchmark cases can be registered and replayed with persisted replay artifacts.
- [ ] `project_type=default` remains unaffected.
- [ ] Existing consumer projects without Phase 4A artifacts still load with fallback `unknown` / `not_scored` fields.
- [ ] Full backend tests pass.
- [ ] Targeted frontend tests pass.
- [ ] `npm run build` passes.
