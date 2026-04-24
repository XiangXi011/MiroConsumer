# Consumer Simulation Phase6E Architecture/Product Debt Closure Implementation Plan
> **For agentic workers:** REQUIRED SUB-SKILL: Use delegating-to-claude-code execution tasks; Codex owns planning/audit and Claude Code owns file edits.

## Goal

Close four verified product/architecture debts without expanding the consumer kernel scope:

1. **Architecture boundary:** `ConsumerAppService.get_consumer_summary()` still imports `ProjectManager` and calls `project_research_persistence.load_persisted_snapshot` directly. Coupling should move behind a provider/repository boundary.
2. **Product-surface/runtime mismatch:** `Step3Simulation.vue` shows dual top platform cards (Info Plaza + Topic Community) in consumer mode, but the consumer runner only starts `reddit_running=True` and emits actions with `platform=reddit`.
3. **Branch restore-state UX:** `BranchInterventionWorkspace.vue` `loadBranches()` restores persisted `selectedBranchId` and calls `loadInterventions()`, but does not call `fetchBranchStatus()` or restart polling when the branch status is `running`. The `onBranchChange()` handler already has the complete mirror logic.
4. **Frontend API behavior-test debt:** `frontend/tests/consumerApi.test.js` is mostly source-string regex/assert includes, providing static-smoke protection but not behavior/contract coverage.

---

## Architecture Decision

**Single propagation stream UI for consumer mode.** The backend consumer runner is currently a single event stream (`reddit`). Phase6E does NOT build dual backend consumer channels. The frontend consumer-mode surface shows one status/timeline card aligned with the single stream. Legacy non-consumer mode keeps the existing dual platform cards.

---

## File Map

### New Files

| File | Purpose |
|------|---------|
| `backend/app/repositories/consumer_project_research_provider.py` or `backend/app/services/consumer/project_research_provider.py` | Repository/provider boundary that wraps `load_persisted_snapshot` and `ProjectManager` lookup. Returns a typed contract (dataclass or TypedDict) that `ConsumerAppService` depends on. |
| `backend/tests/consumer/test_project_research_provider.py` | Tests proving the provider loads snapshots and resolves projects correctly. |
| `backend/tests/application/test_consumer_app_service_provider_boundary.py` | Tests proving `ConsumerAppService.get_consumer_summary()` calls the provider boundary, not `ProjectManager` or persistence directly, and still returns summary context. |
| `frontend/tests/consumerApi.behavior.test.js` | Behavior tests with a mocked service module/function layer. Tests request/response contracts and state transitions, not just source-string inclusion. |

### Modified Files

| File | What Changes |
|------|-------------|
| `backend/app/services/application/consumer_app_service.py` | Replace direct `ProjectManager` import and `load_persisted_snapshot` call with dependency on provider contract. Inject provider via `__init__` or module-level default. |
| `backend/app/services/application/__init__.py` or `backend/app/repositories/__init__.py` | Export new provider type if needed. |
| `frontend/src/components/Step3Simulation.vue` | Consumer mode: render single propagation stream status/timeline card (reddit). Non-consumer mode: keep existing dual platform cards (Info Plaza + Topic Community). Use the existing `isConsumerMode` flag or equivalent to branch rendering. |
| `frontend/src/components/consumer/BranchInterventionWorkspace.vue` | In `loadBranches()`, after restoring persisted `selectedBranchId` and calling `loadInterventions()`, mirror the logic from `onBranchChange()`: call `fetchBranchStatus(branchId)`; if status is `running`, start polling. |
| `frontend/tests/consumerApi.test.js` | Keep honestly as static-smoke if still valuable; otherwise rename to `consumerApi.smoke.test.js` and let `consumerApi.behavior.test.js` own behavior coverage. |

---

## Task Breakdown

### Task 1: Backend Boundary Provider + Tests

**Goal:** Introduce a provider/repository boundary so `ConsumerAppService` depends on a contract, not on `ProjectManager` or persistence internals.

**Steps:**

- [ ] Introduce `ConsumerProjectResearchProvider` (or `ProjectResearchRepository`) with a method like `load_snapshot_for_project(project_id: str) -> ConsumerResearchSnapshot`.
- [ ] Move the existing `ProjectManager` lookup and `load_persisted_snapshot` call into the provider implementation.
- [ ] Update `ConsumerAppService` to accept the provider via `__init__` with a sensible default.
- [ ] Remove direct `ProjectManager` import and `load_persisted_snapshot` import from `consumer_app_service.py`.
- [ ] Write unit tests for the provider (`backend/tests/consumer/test_project_research_provider.py`).
- [ ] Write tests proving `ConsumerAppService` uses the provider and still returns the expected summary context (`backend/tests/application/test_consumer_app_service_provider_boundary.py`).

**Acceptance criteria:**
- `ConsumerAppService` has no direct import of `ProjectManager` or `project_research_persistence`.
- Provider tests pass.
- Consumer app service tests pass.
- Existing backend tests pass (no regression).

**Verification:**
```bash
cd backend
grep -n "ProjectManager\|load_persisted_snapshot" app/services/application/consumer_app_service.py
# Expected: no matches
python -m pytest tests/consumer/test_project_research_provider.py tests/application/test_consumer_app_service_provider_boundary.py -v
python -m pytest tests/ -v --tb=short
```

**Commit:**
```bash
git add backend/app/repositories/consumer_project_research_provider.py backend/tests/consumer/test_project_research_provider.py backend/tests/application/test_consumer_app_service_provider_boundary.py backend/app/services/application/consumer_app_service.py
git commit -m "refactor: decouple ConsumerAppService from ProjectManager/persistence via provider boundary"
```

---

### Task 2: BranchInterventionWorkspace Restore-State + Test

**Goal:** After `loadBranches()` restores a persisted selected branch, also restore branch status and polling if the branch is running.

**Steps:**

- [ ] In `BranchInterventionWorkspace.vue` `loadBranches()`, after restoring `selectedBranchId` and calling `loadInterventions()`, add the same status-fetch and polling-start logic that exists in `onBranchChange()`.
- [ ] Extract the status-check + polling-start logic into a shared helper (e.g., `startBranchStatusPolling(branchId)`) if the duplication is more than two lines, to keep both call sites clean.
- [ ] Add or update a frontend component/util test verifying that `loadBranches()` triggers status fetch when a persisted branch is selected and running.

**Acceptance criteria:**
- After page reload with a persisted selected branch in `running` state, the workspace shows running status and polls without requiring the user to re-select the branch.
- No duplication of polling logic (extracted helper or inline mirroring with clear comment).
- Existing BranchInterventionWorkspace tests/build pass.

**Verification:**
```bash
cd frontend
npm run test:unit -- --grep "BranchInterventionWorkspace"
npm run build
```

**Commit:**
```bash
git add frontend/src/components/consumer/BranchInterventionWorkspace.vue
git commit -m "fix: restore branch status polling after persisted selected branch reload"
```

---

### Task 3: Step3 Consumer Single-Stream Surface + Test/Build Check

**Goal:** Align the consumer-mode top status/timeline surface with the single backend propagation stream.

**Steps:**

- [ ] In `Step3Simulation.vue`, locate the top platform card rendering (Info Plaza + Topic Community).
- [ ] Add a conditional: if consumer mode, render a single card labeled with the active platform (e.g., "Reddit Propagation Stream"). If non-consumer mode, keep the existing dual cards.
- [ ] Ensure the single card shows the same status/timeline data that the runner emits.
- [ ] Run frontend build and any existing component tests.

**Acceptance criteria:**
- Consumer mode shows exactly one propagation stream card.
- Non-consumer mode still shows Info Plaza + Topic Community cards unchanged.
- Build passes. No runtime errors in either mode.

**Verification:**
```bash
cd frontend
npm run build
npm run test:unit -- --grep "Step3Simulation"
```

**Commit:**
```bash
git add frontend/src/components/Step3Simulation.vue
git commit -m "fix: align Step3 consumer mode surface with single propagation stream"
```

---

### Task 4: Frontend API Behavior Contract Tests

**Goal:** Add behavior tests that verify request/response contracts and state transitions, not just source-string inclusion.

**Steps:**

- [ ] Create `frontend/tests/consumerApi.behavior.test.js`.
- [ ] Mock the API service module/function layer (e.g., `import * as consumerApi from '@/services/consumerApi'` and `vi.spyOn` or `vi.mock`).
- [ ] Write tests for:
  - Successful consumer summary fetch returns expected shape.
  - Consumer action emission includes `platform=reddit` and correct payload fields.
  - Branch status fetch maps API response to local state correctly.
  - Error paths propagate correctly (e.g., 500 -> rejected promise with message).
- [ ] If `frontend/tests/consumerApi.test.js` still has value as static smoke, rename it to `consumerApi.smoke.test.js` and keep it. Otherwise, replace it honestly.
- [ ] If existing component-test infra supports it, add minimal tests for any extracted utility/behavior function.

**Acceptance criteria:**
- Behavior tests verify contracts, not regex against source strings.
- All new tests pass.
- Existing frontend test suite passes.

**Verification:**
```bash
cd frontend
npm run test:unit -- consumerApi.behavior.test.js
npm run test:unit
```

**Commit:**
```bash
git add frontend/tests/consumerApi.behavior.test.js
# If renamed:
git mv frontend/tests/consumerApi.test.js frontend/tests/consumerApi.smoke.test.js
# Or if removed:
# git rm frontend/tests/consumerApi.test.js
git commit -m "test: add frontend API behavior contract tests for consumer surface"
```

---

### Task 5: Docs/Handoff + Regression Suite

**Goal:** Document the Phase6E closeout and run the regression suite.

**Steps:**

- [ ] Update or create a closeout note summarizing what was fixed and what remains deferred.
- [ ] Run the full backend test suite.
- [ ] Run the full frontend test suite and build.
- [ ] Verify no non-docs files were modified outside the planned scope.

**Acceptance criteria:**
- All backend tests pass.
- Frontend build passes.
- All frontend tests pass.
- No new architecture debt introduced.

**Verification:**
```bash
cd backend
python -m pytest tests/ -v --tb=short

cd ../frontend
npm run build
npm run test:unit
```

**Commit:**
```bash
git add docs/
git commit -m "docs: add phase6e closeout and regression notes"
```

---

## Risk Notes

- **Avoid changing consumer kernel behavior.** Phase6E is boundary/UX/test debt closure. The hybrid kernel and propagation dynamics were handled in earlier phases. Do not modify `HybridSimulationKernel`, `LegacySimulationKernel`, or `PropagationState` logic.
- **Avoid breaking legacy non-consumer platform UI.** `Step3Simulation.vue` dual-card rendering for non-consumer mode must remain byte-for-byte stable in behavior and appearance.
- **Preserve API route paths.** No consumer API URL paths change in this phase. The provider boundary is an internal refactor.
- **Smoke deferred until requested.** End-to-end smoke tests remain deferred per prior phase instructions. Unit and integration tests are the verification gate for Phase6E.
- **Minimal change set.** Do not introduce new backend-to-frontend contracts, new persistence models, or new runner channels. The scope is boundary extraction, UI conditional alignment, polling restore, and test quality.
