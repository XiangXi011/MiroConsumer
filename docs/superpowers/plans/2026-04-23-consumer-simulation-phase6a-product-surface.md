# Consumer Simulation Phase 6A Product Surface Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make MiroConsumer visibly consumer-only while preserving `project_type=default` as an internal compatibility contract for old callers and stored artifacts.

**Architecture:** Phase 6A keeps graph/simulation/report lifecycle ownership in the shared engine, but moves all consumer-specific product entry and post-run behavior onto consumer-owned surfaces and canonical `/api/consumer/*` routes. The implementation should avoid large structural rewrites: use a small frontend contract change, doc cleanup, canonical consumer API wrappers, and focused compatibility regression tests.

**Tech Stack:** Vue 3 + Vite frontend, Flask backend, filesystem repositories, Node test runner, pytest

---

## File Map

### Product Surface and Frontend Contract

- Modify: `frontend/src/views/Home.vue`
- Modify: `frontend/src/store/pendingUpload.js`
- Modify: `frontend/src/api/graph.js`
- Modify: `locales/en.json`
- Modify: `locales/zh.json`
- Test: `frontend/tests/pendingUpload.test.js`
- Create: `frontend/tests/graphApi.test.js`

### Canonical Consumer API Adoption

- Create: `frontend/src/api/consumer.js`
- Modify: `frontend/src/api/simulation.js`
- Modify: `frontend/src/api/report.js`
- Modify: `frontend/src/components/Step3Simulation.vue`
- Modify: `frontend/src/components/Step4Report.vue`
- Modify: `frontend/src/components/Step5Interaction.vue` if it imports consumer-owned APIs through shared modules
- Test: `frontend/tests/consumerMode.test.js`

### Product Docs and Maintainer Contract

- Modify: `README.md`
- Modify: `README-ZH.md`
- Modify: `PRD.md`
- Create: `backend/tests/test_phase6a_product_surface.py`

### Compatibility and Persistence Contract

- Modify: `backend/app/api/graph.py` only if targeted contract tests expose hidden ambiguity in create-time `project_type` handling
- Modify: `backend/app/services/application/simulation_app_service.py` only if targeted contract tests expose `project_type` drift between project and simulation artifacts
- Modify: `backend/app/services/application/report_app_service.py` only if targeted contract tests expose `project_type` drift between simulation and report artifacts
- Modify: `backend/app/repositories/filesystem.py` only if targeted contract tests expose round-trip preservation issues
- Modify: `backend/tests/api/test_consumer_canonical_routes.py`
- Modify: `backend/tests/api/test_consumer_routes.py`
- Create: `backend/tests/api/test_phase6a_project_type_contract.py`

## Task 1: Consumer-Only Product Surface

**Files:**
- Modify: `frontend/src/views/Home.vue`
- Modify: `frontend/src/store/pendingUpload.js`
- Modify: `frontend/src/api/graph.js`
- Modify: `locales/en.json`
- Modify: `locales/zh.json`
- Test: `frontend/tests/pendingUpload.test.js`
- Test: `frontend/tests/graphApi.test.js`

- [ ] **Step 1: Write the failing frontend contract tests**

```js
import { test } from 'node:test'
import assert from 'node:assert/strict'

import { clearPendingUpload, getPendingUpload, setPendingUpload } from '../src/store/pendingUpload.js'
import { buildOntologyFormData } from '../src/api/graph.js'

test('product-facing pending upload defaults to consumer_test', () => {
  clearPendingUpload()
  setPendingUpload([{ name: 'brief.pdf' }], 'Run consumer test')
  assert.equal(getPendingUpload().projectType, 'consumer_test')
})

test('ontology form data persists consumer_test for product-owned creates', () => {
  const formData = buildOntologyFormData({
    files: [],
    simulationRequirement: 'Run consumer test',
  })
  assert.equal(formData.get('project_type'), 'consumer_test')
})
```

- [ ] **Step 2: Run the targeted frontend tests to confirm they fail on the current Phase 5 baseline**

Run:

```powershell
Set-Location D:\project\MiroFish\.worktrees\phase5a-identity
node --test frontend/tests/pendingUpload.test.js frontend/tests/graphApi.test.js
```

Expected:

- the legacy `default` product-mode assumptions fail
- the failure points name `projectType` defaulting and/or `project_type` form serialization

- [ ] **Step 3: Implement the smallest product-surface contract change**

```js
const PRODUCT_PROJECT_TYPE = 'consumer_test'

const createDefaultState = () => ({
  files: [],
  simulationRequirement: '',
  projectType: PRODUCT_PROJECT_TYPE,
  consumerBrief: null,
  researchMode: 'manual_only',
  enableLaneB: false,
  personaPackSelection: null,
  personaPackFile: null,
  isPending: false,
})

formData.value.projectType = PRODUCT_PROJECT_TYPE
formData.append('project_type', payload.projectType || PRODUCT_PROJECT_TYPE)
```

Implementation notes:

- remove the visible `default` / `consumer_test` mode switch from `Home.vue`
- initialize the Home page and pending-upload store in consumer mode
- keep the existing upload flow shape intact so `Process.vue` does not need a broad rewrite
- update locale strings so product-facing copy no longer describes two visible modes

- [ ] **Step 4: Re-run frontend tests and build**

Run:

```powershell
Set-Location D:\project\MiroFish\.worktrees\phase5a-identity
node --test frontend/tests/pendingUpload.test.js frontend/tests/graphApi.test.js frontend/tests/consumerMode.test.js
Set-Location frontend
npm run build
```

Expected:

- all targeted frontend tests pass
- Vite build succeeds
- no visible product surface renders a `default` selector

- [ ] **Step 5: Commit the product-surface batch**

```bash
git add frontend/src/views/Home.vue frontend/src/store/pendingUpload.js frontend/src/api/graph.js locales/en.json locales/zh.json frontend/tests/pendingUpload.test.js frontend/tests/graphApi.test.js
git commit -m "feat: make product entry consumer-only"
```

## Task 2: Product Docs and Maintainer Contract Alignment

**Files:**
- Modify: `README.md`
- Modify: `README-ZH.md`
- Modify: `PRD.md`
- Create: `backend/tests/test_phase6a_product_surface.py`

- [ ] **Step 1: Write failing product-doc regression tests**

```python
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_product_docs_do_not_present_default_mode():
    for rel_path in ("README.md", "README-ZH.md"):
        text = (ROOT.parent / rel_path).read_text(encoding="utf-8")
        assert "project_type=default" not in text
        assert "`default`" not in text

def test_prd_mentions_default_only_in_maintainer_section():
    text = (ROOT.parent / "PRD.md").read_text(encoding="utf-8")
    assert "## Maintainer Compatibility Notes" in text
```

- [ ] **Step 2: Run the doc regression tests and confirm the current PRD fails**

Run:

```powershell
Set-Location D:\project\MiroFish\.worktrees\phase5a-identity\backend
python -m pytest tests/test_phase6a_product_surface.py -q
```

Expected:

- `README.md` and `README-ZH.md` are already close to green
- `PRD.md` fails because product-facing sections still mention `default`

- [ ] **Step 3: Rewrite product docs and split compatibility notes explicitly**

```markdown
## Maintainer Compatibility Notes

- `project_type=default` remains an internal compatibility mode
- new product-owned flows must persist `consumer_test`
- stored legacy artifacts keep their original `project_type`
```

Implementation notes:

- keep `README.md` and `README-ZH.md` strictly product-facing
- move any `default` discussion in `PRD.md` into a clearly labeled maintainer-only section near the implementation/compatibility material
- align wording with the accepted Phase 6A design spec rather than inventing new product positioning

- [ ] **Step 4: Re-run doc regression tests**

Run:

```powershell
Set-Location D:\project\MiroFish\.worktrees\phase5a-identity\backend
python -m pytest tests/test_phase6a_product_surface.py -q
```

Expected:

- docs test passes
- `default` is only documented as an internal compatibility mode

- [ ] **Step 5: Commit the doc-alignment batch**

```bash
git add README.md README-ZH.md PRD.md backend/tests/test_phase6a_product_surface.py
git commit -m "docs: align product docs with phase6 consumer-only surface"
```

## Task 3: Canonical Consumer API Adoption in the Frontend

**Files:**
- Create: `frontend/src/api/consumer.js`
- Modify: `frontend/src/api/simulation.js`
- Modify: `frontend/src/api/report.js`
- Modify: `frontend/src/components/Step3Simulation.vue`
- Modify: `frontend/src/components/Step4Report.vue`
- Modify: `frontend/src/components/Step5Interaction.vue` if needed
- Test: `frontend/tests/consumerMode.test.js`

- [ ] **Step 1: Write the failing consumer-route ownership tests**

```js
import { test } from 'node:test'
import assert from 'node:assert/strict'

import {
  buildConsumerSummaryPath,
  buildConsumerBranchesPath,
  buildConsumerComparisonsPath,
  buildConsumerResearchAssetsPath,
} from '../src/api/consumer.js'

test('consumer summary path uses canonical consumer route', () => {
  assert.equal(
    buildConsumerSummaryPath('sim_123'),
    '/api/consumer/simulation/sim_123/consumer-summary'
  )
})

test('comparison and research asset paths use canonical consumer route family', () => {
  assert.equal(buildConsumerComparisonsPath(), '/api/consumer/comparisons')
  assert.equal(buildConsumerResearchAssetsPath(), '/api/consumer/research-assets')
})
```

- [ ] **Step 2: Run the targeted frontend tests to confirm the canonical wrapper module is missing**

Run:

```powershell
Set-Location D:\project\MiroFish\.worktrees\phase5a-identity
node --test frontend/tests/consumerMode.test.js
```

Expected:

- the new route-builder assertions fail because the canonical consumer wrapper module does not exist yet

- [ ] **Step 3: Create the canonical consumer wrapper module and migrate imports**

```js
export const buildConsumerSummaryPath = (simulationId) =>
  `/api/consumer/simulation/${simulationId}/consumer-summary`

export const getConsumerSummary = (simulationId) =>
  service.get(buildConsumerSummaryPath(simulationId))

export const listBranches = (simulationId) =>
  service.get(`/api/consumer/simulations/${simulationId}/branches`)
```

Implementation notes:

- move consumer-only wrappers out of `simulation.js` and `report.js` into `consumer.js`
- leave shared lifecycle APIs in `simulation.js` and `report.js`
- update `Step3Simulation.vue` to import summary/branch/intervention functions from `consumer.js`
- update `Step4Report.vue` to import comparison/research-asset functions from `consumer.js`
- only touch `Step5Interaction.vue` if it reaches into consumer-specific wrappers through shared modules
- keep the legacy backend shim routes untouched; this batch is about frontend canonical ownership

- [ ] **Step 4: Re-run the frontend tests and build**

Run:

```powershell
Set-Location D:\project\MiroFish\.worktrees\phase5a-identity
node --test frontend/tests/consumerMode.test.js frontend/tests/pendingUpload.test.js frontend/tests/graphApi.test.js
Set-Location frontend
npm run build
```

Expected:

- canonical route helper assertions pass
- consumer Step components build successfully against the new imports
- no runtime import errors remain in Vite build output

- [ ] **Step 5: Commit the canonical consumer API batch**

```bash
git add frontend/src/api/consumer.js frontend/src/api/simulation.js frontend/src/api/report.js frontend/src/components/Step3Simulation.vue frontend/src/components/Step4Report.vue frontend/src/components/Step5Interaction.vue frontend/tests/consumerMode.test.js
git commit -m "refactor: make consumer routes canonical in frontend"
```

## Task 4: Compatibility Hardening and Persistence Contract Regression

**Files:**
- Create: `backend/tests/api/test_phase6a_project_type_contract.py`
- Modify: `backend/tests/api/test_consumer_canonical_routes.py`
- Modify: `backend/tests/api/test_consumer_routes.py`
- Modify: `backend/app/api/graph.py` only if tests expose create-time ambiguity
- Modify: `backend/app/services/application/simulation_app_service.py` only if tests expose simulation-level drift
- Modify: `backend/app/services/application/report_app_service.py` only if tests expose report-level drift
- Modify: `backend/app/repositories/filesystem.py` only if tests expose round-trip drift

- [ ] **Step 1: Write the failing backend contract tests**

```python
def test_legacy_omitted_project_type_still_persists_default(client):
    response = client.post("/api/graph/ontology/generate", data={...})
    assert response.status_code == 200
    assert response.get_json()["data"]["project"]["project_type"] == "default"

def test_explicit_consumer_project_type_persists_consumer_test(client):
    response = client.post("/api/graph/ontology/generate", data={..., "project_type": "consumer_test"})
    assert response.status_code == 200
    assert response.get_json()["data"]["project"]["project_type"] == "consumer_test"

def test_persisted_default_artifact_round_trips_without_route_shim(repo_seed):
    state = simulation_repo.get_simulation("sim_legacy")
    assert state.project_type == "default"
```

- [ ] **Step 2: Run the targeted backend suite and record the first failing assertion**

Run:

```powershell
Set-Location D:\project\MiroFish\.worktrees\phase5a-identity\backend
python -m pytest tests/api/test_phase6a_project_type_contract.py tests/api/test_consumer_canonical_routes.py tests/api/test_consumer_routes.py -q
```

Expected:

- at least one new contract test fails before implementation
- existing canonical/shim route tests remain a safety net while adding the new assertions

- [ ] **Step 3: Patch only the layer that actually leaks the contract**

```python
project_type = request.form.get("project_type", "default").strip() or "default"

state = simulation_repo.create_simulation(
    project_id=project.project_id,
    graph_id=graph_id,
    project_type=project.project_type or "default",
)

report = report_repo.create_report(
    simulation_id=simulation_id,
    project_type=project.project_type or state.project_type or "default",
)
```

Implementation notes:

- keep omitted and explicit `default` behavior intact for legacy callers
- do not add new product-facing branching on `default`
- only change backend code if the new tests prove a real persistence or round-trip bug
- if no bug exists, this task may land as tests-only plus comments that make the contract explicit

- [ ] **Step 4: Re-run targeted tests plus core regression**

Run:

```powershell
Set-Location D:\project\MiroFish\.worktrees\phase5a-identity\backend
python -m pytest tests/api/test_phase6a_project_type_contract.py tests/api/test_consumer_canonical_routes.py tests/api/test_consumer_routes.py tests/test_phase6a_product_surface.py -q
python -m pytest tests/api/ tests/consumer/ tests/services/application/ -q
```

Expected:

- explicit `default` still works for compatibility callers
- explicit `consumer_test` still works for canonical consumer callers
- legacy persisted `default` artifacts still round-trip without backfill
- canonical `/api/consumer/*` and legacy shim routes both stay green

- [ ] **Step 5: Commit the compatibility-hardening batch**

```bash
git add backend/tests/api/test_phase6a_project_type_contract.py backend/tests/api/test_consumer_canonical_routes.py backend/tests/api/test_consumer_routes.py backend/app/api/graph.py backend/app/services/application/simulation_app_service.py backend/app/services/application/report_app_service.py backend/app/repositories/filesystem.py
git commit -m "test: harden phase6 product type compatibility contract"
```

## Final Verification

- [ ] Run the complete frontend regression relevant to Phase 6A

```powershell
Set-Location D:\project\MiroFish\.worktrees\phase5a-identity
node --test frontend/tests/consumerBrief.test.js frontend/tests/consumerMode.test.js frontend/tests/pendingUpload.test.js frontend/tests/graphApi.test.js
Set-Location frontend
npm run build
```

- [ ] Run the backend Phase 6A regression bundle

```powershell
Set-Location D:\project\MiroFish\.worktrees\phase5a-identity\backend
python -m pytest tests/test_phase6a_product_surface.py tests/api/test_phase6a_project_type_contract.py tests/api/test_consumer_canonical_routes.py tests/api/test_consumer_routes.py -q
python -m pytest tests/api/ tests/consumer/ tests/services/application/ -q
```

- [ ] Perform a manual product-surface smoke check

Checklist:

- open the homepage and confirm no visible `default` selector exists
- create a new project from the homepage and confirm the persisted project uses `project_type=consumer_test`
- run the normal graph -> prepare -> start -> report flow
- confirm consumer summary, branches, interventions, comparisons, and research assets all use the canonical consumer path in frontend code while legacy backend shims still remain callable

## Notes for Execution

- Execute against `D:\project\MiroFish\.worktrees\phase5a-identity`, not the root `main` worktree
- The existing untracked spec file for this phase is `docs/superpowers/specs/2026-04-23-consumer-simulation-phase6a-product-surface-design.md`
- Keep the scope to Phase 6A only; do not combine this with large component decomposition or unrelated runtime tuning
