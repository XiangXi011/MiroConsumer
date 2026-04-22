# Consumer Simulation Phase 4A Credibility Upgrade — Handoff

**Date:** 2026-04-22
**Branch:** `codex/consumer-simulation-phase1`
**Scope:** Documentation and status record for the completed Phase 4A credibility upgrade.

---

## What Phase 4A Delivered

Phase 4A upgraded `consumer_test` from a research-grade simulation workflow into a more trustworthy decision system by adding source quality governance, evidence validation, confidence scoring, and benchmark replay calibration.

### Task Groups Completed

| Task Group | Commit | Description |
|------------|--------|-------------|
| 1 | `3392288` | Source quality scoring (`source_quality.py`) with trust tiers, freshness, coverage tags, and deterministic scoring for Lane A and Lane B sources |
| 2 | `7476d70` | Stronger Lane B governance with duplicate filtering, weak-snippet rejection, source downgrade rules, and retrieval trace recording |
| 3 | `d87d872` | Evidence validator (`evidence_validator.py`) and confidence scoring (`confidence_scoring.py`) with machine-readable statuses |
| 4 | `76a74c8` | UI exposure of credibility signals in Step 2 (source quality summary), Step 4 (finding confidence / evidence sufficiency), and Step 5 (weak-evidence prompts) |
| 5 | `6fda61e` | Benchmark registry and replay with repo-local artifact persistence under `backend/uploads/benchmarks/` |
| 5 | `20a6c2e` | Consumer-test gating enforced on all benchmark API routes |

### New Backend Modules

- `backend/app/services/consumer/source_quality.py`
- `backend/app/services/consumer/evidence_validator.py`
- `backend/app/services/consumer/confidence_scoring.py`
- `backend/app/services/consumer/benchmark_registry.py`
- `backend/app/services/consumer/benchmark_replay.py`

### New Backend Tests

- `backend/tests/consumer/test_source_quality.py`
- `backend/tests/consumer/test_lane_b_governance.py`
- `backend/tests/consumer/test_evidence_validator.py`
- `backend/tests/consumer/test_confidence_scoring.py`
- `backend/tests/consumer/test_benchmark_registry.py`
- `backend/tests/consumer/test_benchmark_replay.py`

### Modified Backend Services

- `backend/app/services/consumer/models.py` — quality and confidence companion fields
- `backend/app/services/consumer/source_registry.py` — quality snapshot wiring
- `backend/app/services/consumer/project_research_persistence.py` — `source_quality.json` and `evidence_validation.json` persistence
- `backend/app/services/consumer/research_ingest.py` — quality scoring integration
- `backend/app/services/consumer/lane_b_provider.py` — governance rules
- `backend/app/services/consumer/retrieval.py` — governance trace recording
- `backend/app/services/consumer/finding_distiller.py` — accepted-evidence-only distillation
- `backend/app/services/consumer/scoring.py` — confidence-attached run summaries
- `backend/app/services/consumer/report_context.py` — confidence-formatted report structures
- `backend/app/services/consumer/comparison_engine.py` — comparison confidence output
- `backend/app/services/consumer/__init__.py` — new exports
- `backend/app/api/graph.py` — `source_quality_summary` in consumer context
- `backend/app/api/simulation.py` — confidence gating on consumer summary
- `backend/app/api/report.py` — benchmark register / list / replay / fetch routes
- `backend/app/services/report_agent.py` — replay alignment exposure in report context

### Modified Frontend

- `frontend/src/components/Step2EnvSetup.vue` — source quality summary cards
- `frontend/src/components/Step4Report.vue` — finding confidence and replay status
- `frontend/src/components/Step5Interaction.vue` — weak-evidence and replay-aware prompts
- `frontend/src/utils/consumerMode.js` — confidence badge / label helpers
- `frontend/src/api/report.js` — benchmark API client
- `frontend/src/api/simulation.js` — confidence field handling
- `frontend/tests/consumerMode.test.js` — confidence UI tests
- `locales/en.json` and `locales/zh.json` — credibility signal labels

---

## Verified Test Results

### Backend

| Suite | Count | Status |
|-------|-------|--------|
| Benchmark module tests (`test_benchmark_registry.py` + `test_benchmark_replay.py`) | 17 passed | Pass |
| Benchmark route tests (benchmark-gated routes in `test_consumer_routes.py`) | 7 passed | Pass |
| Full non-integration backend suite (`pytest tests -q --ignore=tests/integration`) | 347 passed | Pass |

### Frontend

| Suite | Count | Status |
|-------|-------|--------|
| Targeted consumer tests (`consumerMode.test.js` + `consumerBrief.test.js` + `pendingUpload.test.js`) | 73 passed | Pass |
| Build (`npm run build`) | success | Pass |

### Backward Compatibility

- `project_type=default` remains unaffected; default-mode routes do not invoke source quality, evidence validation, confidence scoring, or benchmark replay
- Existing consumer projects without Phase 4A artifacts load with fallback `unknown` / `not_scored` fields

---

## Known Limits

- `auto_enrich` still uses deterministic synthetic research rather than live external search; Lane B public-web supplementation quality depends on the grounded provider implementation
- Kimi For Coding response time remains ~3-5 minutes per profile; full prepare for 4 profiles still ~21 minutes
- `json_object` compatibility remains mitigated by proxy but may fluctuate with model or proxy configuration changes
- Small-scale profiles (4) are stable; larger scales still recommend faster models
- `pendingUpload.js` dynamic/static import mix warning persists (non-blocking)
- Frontend chunk size warning persists (non-blocking)
- Manual end-to-end smoke run through the full consumer workflow (build graph with research enabled -> prepare simulation -> inspect confidence-bearing summary -> export benchmark/replay state) is not yet recorded in repo evidence

---

## Next Steps

1. **Live external research provider** — replace deterministic `auto_enrich` and grounded Lane B with a real retrieval provider when stability and cost allow
2. **Performance scaling** — profile generation concurrency and larger sample stability
3. **Benchmark library expansion** — grow from minimal repeatability checks into a category memory / recurring insight library
4. **Cross-project asset reuse** — strengthen project-level and cross-project research asset lineage without implicit knowledge leakage
5. **Manual end-to-end smoke verification** — run a full consumer workflow through Step 2 -> Step 4 -> Step 5 with confidence signals and benchmark replay visible

---

## References

- Plan: `docs/superpowers/plans/2026-04-22-consumer-simulation-phase4a-credibility-upgrade.md`
- Design spec: `docs/superpowers/specs/2026-04-22-consumer-simulation-phase4a-credibility-upgrade-design.md`
