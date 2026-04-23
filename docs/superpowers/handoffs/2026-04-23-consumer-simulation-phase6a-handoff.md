# Consumer Simulation Phase 6A Handoff

## 1. Status

Phase 6A is complete on branch `codex/phase5-closure`, committed as `4f51131`.

This phase established the **consumer-only product surface**: the UI no longer exposes a project-type switcher, `consumer_test` is the sole product-facing mode, and `project_type=default` is demoted to a maintainer-only internal compatibility mode documented in the PRD.

## 2. Batch Summary

Phase 6A was delivered in 4 batches:

- **Batch 1 — Consumer-Only Product Surface**: removed the project-mode switcher from `Home.vue`; `formData.projectType` now defaults to `consumer_test`; the consumer-brief section is always visible (no longer gated behind a mode check). Locale keys for the removed mode switcher (`home.projectMode`, `home.modeDefault`, `home.modeConsumer`, etc.) were deleted from both `en.json` and `zh.json`.
- **Batch 2 — Product-Doc & Contract Alignment**: PRD section 4.3 rewritten as "Maintainer-Only: Internal Compatibility Mode (`project_type=default`)" — makes explicit that default is not a user-facing product mode. Existing acceptance and regression references updated to say "internal compatibility mode" instead of "default mode".
- **Batch 3 — Canonical Consumer Frontend API Ownership**: new `frontend/src/api/consumer.js` (136 lines) owns all consumer-specific endpoints (consumer-summary, branches, interventions, research-assets, comparisons). `report.js` and `simulation.js` were thinned: consumer-facing functions moved to `consumer.js` and re-exported from `report.js` for backwards compatibility. `buildOntologyFormData` extracted to `ontologyFormData.js` with the default `projectType` flipped to `consumer_test`. `graph.js` re-exports from `ontologyFormData.js` instead of inlining the builder.
- **Batch 4 — Compatibility Hardening Tests**: 761 lines of new test code across 3 files — `test_phase6a_product_surface.py` (116 lines, guards that product-facing docs never mention `project_type=default`), `test_phase6a_project_type_contract.py` (378 lines, regression tests for project-type persistence through graph intake and simulation create), `consumerApi.test.js` (307 lines, verifies every canonical route string in the consumer API module), `graphApi.test.js` (74 lines, verifies `buildOntologyFormData` defaults and re-export surface).

## 3. Key Touched Files

### Frontend

- `frontend/src/views/Home.vue` — removed mode switcher UI, default projectType flipped to `consumer_test`
- `frontend/src/api/consumer.js` — **new**; canonical consumer API module
- `frontend/src/api/ontologyFormData.js` — **new**; extracted form-data builder, default `consumer_test`
- `frontend/src/api/graph.js` — re-exports `buildOntologyFormData` from `ontologyFormData.js`
- `frontend/src/api/report.js` — consumer-facing functions now re-exported from `consumer.js`
- `frontend/src/api/simulation.js` — thinned; consumer routes moved out
- `frontend/src/components/Step3Simulation.vue` — minor import alignment
- `frontend/src/components/Step4Report.vue` — minor import alignment
- `frontend/src/components/Step5Interaction.vue` — minor import alignment
- `frontend/src/store/pendingUpload.js` — default projectType updated

### Frontend Tests

- `frontend/tests/consumerApi.test.js` — **new** (307 lines)
- `frontend/tests/graphApi.test.js` — **new** (74 lines)
- `frontend/tests/pendingUpload.test.js` — updated for new default

### Backend Tests

- `backend/tests/test_phase6a_product_surface.py` — **new** (116 lines)
- `backend/tests/api/test_phase6a_project_type_contract.py` — **new** (378 lines)

### Docs / Config

- `PRD.md` — section 4.3 rewritten; acceptance references updated
- `locales/en.json` — 5 mode-switcher keys removed
- `locales/zh.json` — 5 mode-switcher keys removed

## 4. Verification Evidence

Phase 6A ships with three layers of automated guards:

1. **Product-surface doc tests** (`test_phase6a_product_surface.py`): regex-based assertions that `README.md`, `README-ZH.md`, and `PRD.md` never contain `project_type=default` as a visible product mode. If someone re-introduces default as a product-facing mode in docs, these tests break.

2. **Project-type persistence contract** (`test_phase6a_project_type_contract.py`): 378-line integration-style test covering four rules — legacy callers without `project_type` still get default compatibility behaviour; explicit `consumer_test` persists through project and simulation creation; legacy `default` artifacts round-trip through repositories; canonical `/api/consumer/*` routes and legacy shim routes remain green.

3. **Frontend API contract tests**: `consumerApi.test.js` verifies every route string in `consumer.js` matches expected canonical paths (consumer-summary, branches, interventions, research-assets, comparisons). `graphApi.test.js` verifies `buildOntologyFormData` defaults to `consumer_test` and that `graph.js` re-exports it correctly.

## 5. Compatibility Notes

- The UI no longer shows a mode switcher — all new projects default to `consumer_test`.
- `project_type=default` still works when sent explicitly (internal compat mode), but it is not exposed to users and is documented as maintainer-only in the PRD.
- `report.js` re-exports consumer functions from `consumer.js`, so existing imports from `report.js` continue to resolve.
- `graph.js` re-exports `buildOntologyFormData` from `ontologyFormData.js`, so existing imports are unchanged.
- No backend route changes were made in this phase; all backend endpoints remain at their Phase 5 positions.

## 6. Remaining Non-Blockers

- Some historical `MiroFish` references survive in non-primary surfaces (logs, comments, old docs); these are cosmetic.
- The large logo asset retains its historical filename `MiroFish_logo_left...`; not functional.
- The locale removals (10 keys total) are clean — no remaining references to the deleted keys exist in templates.
- `simulation.js` still has a thin shim layer; fully deprecating legacy consumer routes in `simulation.js` is a future cleanup.

## 7. Next Step

Phase 6A establishes the consumer-only product surface and guards it with contract tests. The most natural next step is **Phase 6B or equivalent** — adding new consumer-specific capability depth (e.g. richer intervention tooling, batch comparison workflows, or advanced branch management) on top of the now-clean consumer API surface. The infrastructure and ownership boundaries are in place; the next phase should focus on product features rather than structural cleanup.
