# Consumer Simulation Phase 5 Handoff

## 1. Status

Phase 5 is complete on branch `codex/phase5-closure`.

This phase closed the product and architecture cleanup wave after Phase 4:

- product identity cleanup
- thin API route layer
- repository abstraction for file persistence
- configurable persona packs
- evidence validation as gatekeeping
- clearer `consumer_test` bounded context

## 2. What Landed

### 2.1 Product Identity

- core product-facing views now show `MiroConsumer`
- root package and lockfile naming are aligned to `miroconsumer`
- the repo presentation is less fork-like and more product-like

Primary touched surfaces:

- `frontend/src/views/Home.vue`
- `frontend/src/views/MainView.vue`
- `frontend/src/views/SimulationView.vue`
- `frontend/src/views/SimulationRunView.vue`
- `frontend/src/views/ReportView.vue`
- `frontend/src/views/InteractionView.vue`
- `frontend/src/views/Process.vue`
- `package.json`
- `package-lock.json`

### 2.2 Service and Repository Boundaries

- application-service orchestration now exists for graph, simulation, report, branch, benchmark, and consumer flows
- repository abstractions now include:
  - `ProjectRepository`
  - `ConsumerStateRepository`
  - `SimulationRepository`
  - `BranchRepository`
  - `ReportRepository`
  - `BenchmarkRepository`
- filesystem-backed implementations remain the active storage backend

Key files:

- `backend/app/services/application/graph_app_service.py`
- `backend/app/services/application/simulation_app_service.py`
- `backend/app/services/application/report_app_service.py`
- `backend/app/services/application/branch_app_service.py`
- `backend/app/services/application/benchmark_app_service.py`
- `backend/app/services/application/consumer_app_service.py`
- `backend/app/repositories/__init__.py`
- `backend/app/repositories/filesystem.py`

### 2.3 Persona Pack Assetization

- persona packs are now explicit assets rather than hidden defaults
- supported pack classes:
  - generic
  - industry
  - category
  - geography
  - custom uploaded
- custom persona pack upload is supported from the consumer creation flow
- selected pack metadata propagates through brief build, graph build, and simulation prepare

Key files:

- `backend/app/services/consumer/persona_pack_registry.py`
- `backend/app/services/consumer/models.py`
- `backend/app/services/consumer/brief_adapter.py`
- `backend/app/services/application/graph_app_service.py`
- `backend/app/services/simulation_manager.py`
- `backend/app/api/graph.py`
- `frontend/src/views/Home.vue`
- `frontend/src/store/pendingUpload.js`
- `frontend/src/utils/consumerBrief.js`
- `frontend/src/api/graph.js`
- `frontend/src/components/Step2EnvSetup.vue`

### 2.4 Evidence Gatekeeping

- evidence validation no longer stops at advisory scoring
- findings now pass through hard gatekeeping before they can influence high-level outputs
- executive summary style outputs block unsupported high-stakes findings
- comparison and benchmark replay reflect weak/blocked evidence instead of treating all findings as equal

Key files:

- `backend/app/services/consumer/evidence_validator.py`
- `backend/app/services/consumer/scoring.py`
- `backend/app/services/consumer/report_context.py`
- `backend/app/services/consumer/comparison_engine.py`
- `backend/app/services/consumer/benchmark_replay.py`

### 2.5 Consumer Bounded Context

- canonical consumer route now exists at:
  - `/api/consumer/simulation/<simulation_id>/consumer-summary`
- legacy simulation route remains as a compatibility shim:
  - `/api/simulation/<simulation_id>/consumer-summary`
- consumer-specific gating, orchestration, and state access are now more explicit

Key files:

- `backend/app/api/consumer.py`
- `backend/app/api/simulation.py`
- `backend/app/api/__init__.py`
- `backend/app/__init__.py`
- `backend/app/services/application/consumer_app_service.py`
- `backend/app/services/consumer/api_guard.py`
- `backend/app/services/consumer/simulation_state_accessor.py`

## 3. Verification

Fresh verification run after integration:

- targeted backend acceptance:
  - `166 passed`
- full backend non-integration regression:
  - `534 passed, 1 deselected`
- targeted frontend tests:
  - `92 passed`
- frontend build:
  - passed
- Flask app smoke:
  - `/api/consumer/simulation/<simulation_id>/consumer-summary` registered successfully

Key commands used:

```powershell
D:\project\MiroFish\.worktrees\consumer-simulation-phase1\backend\.venv\Scripts\python.exe -m pytest backend\tests\consumer\test_persona_pack_registry.py backend\tests\consumer\test_evidence_validator.py backend\tests\consumer\test_scoring.py backend\tests\consumer\test_benchmark_replay.py backend\tests\consumer\test_comparison_engine.py backend\tests\consumer\test_api_guard.py backend\tests\consumer\test_consumer_app_service.py backend\tests\consumer\test_simulation_state_accessor.py backend\tests\api\test_consumer_routes.py backend\tests\api\test_consumer_interventions.py -q
```

```powershell
D:\project\MiroFish\.worktrees\consumer-simulation-phase1\backend\.venv\Scripts\python.exe -m pytest tests -q --ignore=tests\integration -k "not test_test_variants_takes_precedence_over_legacy_variants_in_model"
```

```powershell
node --test frontend\tests\consumerMode.test.js frontend\tests\consumerBrief.test.js frontend\tests\pendingUpload.test.js
```

```powershell
npm run build
```

## 4. Compatibility Notes

- existing frontend flows continue to use legacy route shapes where needed
- the new consumer blueprint is additive, not a breaking replacement
- filesystem persistence remains active; repository abstractions are a seam, not a storage migration

## 5. Remaining Non-Blockers

- some legacy/internal `MiroFish` references still exist in non-primary surfaces, logs, comments, or historical docs; they are no longer the main product face
- the large logo asset still keeps the historical filename `MiroFish_logo_left...`; this is cosmetic, not functional
- build retains the pre-existing large-asset footprint in frontend output

## 6. Next Step

Phase 5 is the closure point for product/architecture cleanup.

The next wave should start as `Phase 6` or an equivalent new roadmap, focused on new capability depth rather than structural catch-up.
