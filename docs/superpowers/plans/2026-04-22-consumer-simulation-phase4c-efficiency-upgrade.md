# Consumer Simulation Phase 4C Efficiency Upgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve prepare reuse visibility, harden JSON compatibility, and remove the known frontend build warnings without changing the consumer product contract.

**Architecture:** Add a small prepare-manifest layer in the simulation workspace, centralize JSON-response fallback in one backend helper, and clean the frontend bundle through consistent store imports plus route-level chunking.

**Tech Stack:** Flask, Python, OpenAI-compatible client, Vue 3, Vite

---

### Task 1: Harden JSON Compatibility

**Files:**
- Modify: `backend/app/utils/llm_client.py`
- Modify: `backend/app/services/oasis_profile_generator.py`
- Modify: `backend/app/services/simulation_config_generator.py`
- Test: `backend/tests/utils/test_llm_client.py`

- [ ] Add failing tests for:
  - structured `json_object` success
  - fallback to plain-text JSON extraction
  - fenced JSON cleanup
  - malformed JSON hard failure
- [ ] Run the targeted backend tests and verify the new cases fail first
- [ ] Implement shared fallback/retry parsing in `llm_client.py`
- [ ] Refactor profile/config generators to use the shared helper instead of open-coded JSON request paths
- [ ] Re-run the targeted tests and the surrounding generator tests
- [ ] Commit with: `feat: harden llm json compatibility`

### Task 2: Add Prepare Manifest & Reuse Metadata

**Files:**
- Modify: `backend/app/services/simulation_manager.py`
- Modify: `backend/app/api/simulation.py`
- Test: `backend/tests/api/test_consumer_routes.py`
- Test: `backend/tests/test_simulation_manager.py`

- [ ] Add failing tests for:
  - new prepare manifest persisted after successful prepare
  - repeated prepare exposes reuse metadata
  - default-mode prepare remains backward compatible
- [ ] Run the targeted tests and verify failure
- [ ] Implement manifest persistence and payload exposure
- [ ] Wire manifest info into prepare/config responses without removing old fields
- [ ] Re-run targeted tests, then the full backend non-integration suite
- [ ] Commit with: `feat: add prepare manifest metadata`

### Task 3: Remove Pending Upload Warning

**Files:**
- Modify: `frontend/src/store/pendingUpload.js`
- Modify: `frontend/src/views/Home.vue`
- Modify: `frontend/src/views/MainView.vue`
- Modify: `frontend/src/views/Process.vue`
- Test: `frontend/tests/pendingUpload.test.js`

- [ ] Add/adjust frontend tests for the carryover payload flow
- [ ] Run the targeted tests first
- [ ] Normalize `pendingUpload` usage to one import strategy
- [ ] Re-run the targeted tests
- [ ] Commit with: `fix: normalize pending upload imports`

### Task 4: Route Lazy Loading & Chunk Cleanup

**Files:**
- Modify: `frontend/src/router/index.js`
- Modify: `frontend/vite.config.js`
- Test: `frontend/tests/consumerMode.test.js`

- [ ] Convert non-home routes to lazy imports
- [ ] Add manual chunking for vendor-heavy paths
- [ ] Run `npm run build`
- [ ] Confirm the previous mixed-import warning and chunk-size warning are gone or materially improved
- [ ] Re-run targeted frontend tests
- [ ] Commit with: `perf: split frontend routes and chunks`

### Task 5: Verification & Docs

**Files:**
- Modify: `PRD.md`
- Modify: `docs/superpowers/handoffs/2026-04-22-consumer-simulation-phase4a-handoff.md`
- Add or Modify: `docs/superpowers/handoffs/2026-04-22-consumer-simulation-phase4c-handoff.md`

- [ ] Run backend full non-integration tests
- [ ] Run frontend targeted tests
- [ ] Run frontend build
- [ ] Update docs/handoff with 4C outcomes and remaining limits
- [ ] Commit with: `docs: record phase4c completion`

