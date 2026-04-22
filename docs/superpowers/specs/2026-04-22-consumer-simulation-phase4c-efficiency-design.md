# Consumer Simulation Phase 4C Efficiency & Engineering Upgrade Design

**Date:** 2026-04-22  
**Branch:** `codex/consumer-simulation-phase1`

---

## 1. Goal

Phase 4C upgrades the current consumer simulation stack from “functionally complete” to “faster, cleaner, and more repeatable” without changing the product contract.

The focus is not new research logic or new test types. Phase 4C is about:

- reducing unnecessary prepare work
- hardening LLM JSON-output compatibility
- removing known frontend build warnings
- shrinking the frontend entry bundle through route-level loading and chunk control

---

## 2. Scope

### 2.1 In Scope

- prepare cache metadata and artifact reuse signaling
- centralized `json_object` fallback and parsing resilience
- `pendingUpload` import-warning cleanup
- route lazy loading and Vite chunk strategy
- regression coverage for the above changes

### 2.2 Out Of Scope

- new consumer task types
- changes to scoring logic or benchmark semantics
- replacing the external model provider
- redesigning Step 2-5 UI structure

---

## 3. Product Outcome

When Phase 4C is complete:

1. repeated prepares should explicitly report whether artifacts were reused or regenerated
2. JSON-shaped LLM calls should degrade more safely when `response_format=json_object` is unstable
3. the existing `pendingUpload` mixed dynamic/static import warning should disappear
4. the frontend should load large views lazily and build with a materially cleaner chunk profile

---

## 4. Design

### 4.1 Prepare Cache Metadata

Current state:

- consumer prepare already short-circuits once the simulation is ready
- but the system does not persist a normalized “why it was reused” manifest
- repeated prepares are hard to reason about from API responses alone

Phase 4C adds a lightweight prepare manifest:

- persisted under the simulation workspace
- records:
  - `simulation_id`
  - `project_id`
  - `prepared_at`
  - `project_type`
  - `consumer_mode`
  - `profiles_count`
  - `entities_count`
  - `entity_types`
  - `config_generated`
  - `persona_pack_id`
  - `reuse_count`
  - `last_reused_at`
- reused by:
  - `POST /api/simulation/prepare`
  - `POST /api/simulation/prepare/status`
  - simulation-manager level inspection helpers

The goal is observability first, not an unsafe cross-project cache.

### 4.2 JSON Compatibility Layer

Current state:

- `oasis_profile_generator.py`
- `simulation_config_generator.py`
- `llm_client.py`

all depend on `response_format={"type": "json_object"}` behavior that can vary by provider or proxy.

Phase 4C introduces one shared compatibility path in `llm_client.py`:

- first try the structured JSON response mode
- if that fails, retry with plain-text instructions that force JSON-only output
- strip fenced-code wrappers and `<think>` blocks consistently
- return machine-readable diagnostics for parse path / fallback path

The profile generator and simulation config generator should route their JSON calls through this shared helper instead of open-coding request/parse logic.

### 4.3 Frontend Warning Cleanup

Current state:

- `Home.vue` dynamically imports `pendingUpload`
- `MainView.vue` and `Process.vue` statically import it
- this mixed access pattern causes the known Vite warning

Phase 4C makes `pendingUpload` access consistent:

- one import style only
- shared helper remains repo-local and synchronous
- no behavioral change to the Home -> Process carryover flow

### 4.4 Route-Level Splitting

Current state:

- the router eagerly imports every view
- the current bundle still reports a chunk-size warning

Phase 4C changes:

- use lazy imports for non-home routes
- keep Home as eager entry if needed
- add manual chunking in `vite.config.js` for:
  - Vue core
  - `d3`
  - report-heavy / graph-heavy app code where it makes sense

This is an engineering-only change; route URLs and page behavior stay unchanged.

---

## 5. Files

### Backend

- `backend/app/utils/llm_client.py`
- `backend/app/services/oasis_profile_generator.py`
- `backend/app/services/simulation_config_generator.py`
- `backend/app/services/simulation_manager.py`
- `backend/app/api/simulation.py`
- `backend/tests/...` targeted coverage for JSON fallback and prepare metadata

### Frontend

- `frontend/src/store/pendingUpload.js`
- `frontend/src/views/Home.vue`
- `frontend/src/views/MainView.vue`
- `frontend/src/views/Process.vue`
- `frontend/src/router/index.js`
- `frontend/vite.config.js`
- frontend tests covering pending upload carryover and route loading assumptions

---

## 6. Acceptance

- repeated prepare calls expose whether artifacts were reused
- prepare/config payloads expose the new manifest metadata without breaking existing fields
- JSON fallback tests cover both direct structured success and plain-text fallback success
- `pendingUpload` warning is removed
- frontend build completes without the current chunk-size warning or mixed-import warning
- existing consumer and default flows remain backward compatible

---

## 7. Implementation Outcome (2026-04-22)

Phase 4C is now implemented on `codex/consumer-simulation-phase1`.

Delivered changes:

- backend JSON compatibility now routes through `LLMClient` shared helpers:
  - `chat_with_finish_reason()`
  - `clean_llm_text()`
  - `extract_json()`
  - `chat_json_with_meta()`
- `oasis_profile_generator.py` and `simulation_config_generator.py` no longer open-code JSON parsing logic
- simulation prepare now persists `prepare_manifest.json` and exposes it via:
  - `POST /api/simulation/prepare`
  - `POST /api/simulation/prepare/status`
- repeated prepare calls increment manifest reuse metadata instead of silently short-circuiting
- `Home.vue` now uses a single static `pendingUpload` import path
- non-home routes now lazy-load in `frontend/src/router/index.js`
- `frontend/vite.config.js` now defines manual chunking for vendor-heavy bundles

Verified results:

- backend targeted regression: `57 passed`
- backend full non-integration regression: `373 passed`
- frontend targeted tests: `73 passed`
- frontend build: success
- old `pendingUpload` mixed-import warning: removed
- old Vite chunk-size warning: removed

---

## 8. Risks

- over-engineering cache semantics; keep the manifest descriptive, not globally shared
- accidental behavior changes in legacy prepare logic; tests must cover `project_type=default`
- over-splitting frontend chunks; only split where it clearly improves entry size
