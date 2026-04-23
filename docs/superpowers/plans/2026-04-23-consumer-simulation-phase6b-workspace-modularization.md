# Consumer Simulation Phase 6B Workspace Modularization Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Modularize the consumer workspace after Phase6A so frontend delivery can continue safely.

**Architecture:** Keep `consumer.js` as the only consumer API facade; do not change backend routes, persistence behavior, or `project_type` semantics; focus only on frontend modularization and state extraction.

**Tech Stack:** Vue 3 + Vite frontend, Node test runner

---

## File Map

### Consumer Composables (State Extraction)

- Create: `frontend/src/composables/consumer/useComparisonState.js`
- Create: `frontend/src/composables/consumer/useResearchAssetState.js`
- Create: `frontend/src/composables/consumer/useBranchInterventionState.js`
- Test: `frontend/tests/composables/useComparisonState.test.js`
- Test: `frontend/tests/composables/useResearchAssetState.test.js`

### Step4Report Consumer Workspace Subcomponents

- Create: `frontend/src/components/consumer/ConsumerReportHeader.vue`
- Create: `frontend/src/components/consumer/ComparisonWorkspace.vue`
- Create: `frontend/src/components/consumer/ResearchAssetWorkspace.vue`
- Modify: `frontend/src/components/Step4Report.vue`

### Step3Simulation Consumer Workspace

- Create: `frontend/src/components/consumer/BranchInterventionWorkspace.vue`
- Modify: `frontend/src/components/Step3Simulation.vue`

### Step5Interaction Alignment

- Modify: `frontend/src/components/Step5Interaction.vue`
- Create: `frontend/src/components/consumer/ComparisonSnapshotWorkspace.vue`

### No Backend Changes

- No backend files are modified in this phase

## Task 1: Extract Comparison and Research-Asset State into Composables

**Files:**
- Create: `frontend/src/composables/consumer/useComparisonState.js`
- Create: `frontend/src/composables/consumer/useResearchAssetState.js`
- Test: `frontend/tests/composables/useComparisonState.test.js`
- Test: `frontend/tests/composables/useResearchAssetState.test.js`

- [ ] **Step 1: Write the failing composable contract tests**

```js
import { test } from 'node:test'
import assert from 'node:assert/strict'

import { useComparisonState } from '../../src/composables/consumer/useComparisonState.js'

test('useComparisonState exposes comparison list and loading flag', () => {
  const state = useComparisonState()
  assert.deepEqual(state.comparisons.value, [])
  assert.equal(state.comparisonLoading.value, false)
})

test('useComparisonState addComparison pushes to list', () => {
  const state = useComparisonState()
  state.addComparison({ id: 'c1', label: 'Run A vs Run B' })
  assert.equal(state.comparisons.value.length, 1)
  assert.equal(state.comparisons.value[0].id, 'c1')
})
```

```js
import { test } from 'node:test'
import assert from 'node:assert/strict'

import { useResearchAssetState } from '../../src/composables/consumer/useResearchAssetState.js'

test('useResearchAssetState exposes asset list and loading flag', () => {
  const state = useResearchAssetState()
  assert.deepEqual(state.researchAssets.value, [])
  assert.equal(state.researchAssetLoading.value, false)
})

test('useResearchAssetState addResearchAsset pushes to list', () => {
  const state = useResearchAssetState()
  state.addResearchAsset({ id: 'r1', name: 'Brief Analysis' })
  assert.equal(state.researchAssets.value.length, 1)
  assert.equal(state.researchAssets.value[0].id, 'r1')
})
```

- [ ] **Step 2: Run the targeted node tests to confirm they fail**

Run:

```powershell
Set-Location D:\project\MiroFish\.worktrees\phase5a-identity
node --test frontend/tests/composables/useComparisonState.test.js frontend/tests/composables/useResearchAssetState.test.js
```

Expected:

- tests fail because the composable modules do not exist yet

- [ ] **Step 3: Implement the composables**

Create `frontend/src/composables/consumer/useComparisonState.js`:

```js
import { ref } from 'vue'

export function useComparisonState() {
  const comparisons = ref([])
  const comparisonLoading = ref(false)

  function addComparison(comparison) {
    comparisons.value.push(comparison)
  }

  function removeComparison(id) {
    comparisons.value = comparisons.value.filter(c => c.id !== id)
  }

  function setComparisons(list) {
    comparisons.value = list
  }

  return {
    comparisons,
    comparisonLoading,
    addComparison,
    removeComparison,
    setComparisons,
  }
}
```

Create `frontend/src/composables/consumer/useResearchAssetState.js`:

```js
import { ref } from 'vue'

export function useResearchAssetState() {
  const researchAssets = ref([])
  const researchAssetLoading = ref(false)

  function addResearchAsset(asset) {
    researchAssets.value.push(asset)
  }

  function removeResearchAsset(id) {
    researchAssets.value = researchAssets.value.filter(a => a.id !== id)
  }

  function setResearchAssets(list) {
    researchAssets.value = list
  }

  return {
    researchAssets,
    researchAssetLoading,
    addResearchAsset,
    removeResearchAsset,
    setResearchAssets,
  }
}
```

Implementation notes:

- extract only the state declarations and mutations that currently live inline in `Step4Report.vue`
- keep reactive refs, not computed wrappers — the consuming components own the computed logic
- do not import `consumer.js` API calls inside the composables; callers pass data in

- [ ] **Step 4: Re-run the composable tests**

Run:

```powershell
Set-Location D:\project\MiroFish\.worktrees\phase5a-identity
node --test frontend/tests/composables/useComparisonState.test.js frontend/tests/composables/useResearchAssetState.test.js
```

Expected:

- both composable tests pass

- [ ] **Step 5: Commit the composable extraction batch**

```bash
git add frontend/src/composables/consumer/useComparisonState.js frontend/src/composables/consumer/useResearchAssetState.js frontend/tests/composables/useComparisonState.test.js frontend/tests/composables/useResearchAssetState.test.js
git commit -m "refactor: extract comparison and research-asset state into composables"
```

## Task 2: Extract Step4Report Consumer Workspace into Subcomponents

**Files:**
- Create: `frontend/src/components/consumer/ConsumerReportHeader.vue`
- Create: `frontend/src/components/consumer/ComparisonWorkspace.vue`
- Create: `frontend/src/components/consumer/ResearchAssetWorkspace.vue`
- Modify: `frontend/src/components/Step4Report.vue`

- [ ] **Step 1: Identify the consumer-workspace sections in Step4Report.vue**

Read `frontend/src/components/Step4Report.vue` and mark:
- the consumer report header block (simulation label, summary link, consumer-only badges)
- the comparison list/table section
- the research asset list/table section

- [ ] **Step 2: Create ConsumerReportHeader.vue**

Extract the consumer header markup and props into `frontend/src/components/consumer/ConsumerReportHeader.vue`.

```vue
<template>
  <div class="consumer-report-header">
    <!-- consumer summary link, simulation label, status badges -->
  </div>
</template>

<script setup>
defineProps({
  simulationId: { type: String, required: true },
  simulationLabel: { type: String, default: '' },
})
</script>
```

Implementation notes:

- pass `simulationId` and `simulationLabel` as props from Step4Report
- do not add new behavior; move the existing template and minimal computed logic only
- emit events back to Step4Report for any actions (e.g., `@refresh-summary`)

- [ ] **Step 3: Create ComparisonWorkspace.vue**

Extract the comparison table/list and the `useComparisonState` composable usage.

```vue
<template>
  <div class="comparison-workspace">
    <!-- comparison list, add/remove controls -->
  </div>
</template>

<script setup>
import { useComparisonState } from '@/composables/consumer/useComparisonState.js'

const props = defineProps({
  simulationId: { type: String, required: true },
})

const { comparisons, comparisonLoading, addComparison, removeComparison } = useComparisonState()
</script>
```

Implementation notes:

- the composable owns reactive state; the component owns the template and user actions
- event callbacks (e.g., `@comparison-selected`) bubble up to Step4Report if the parent needs them
- do not change any `consumer.js` API call signatures

- [ ] **Step 4: Create ResearchAssetWorkspace.vue**

Extract the research asset list and the `useResearchAssetState` composable usage.

```vue
<template>
  <div class="research-asset-workspace">
    <!-- research asset list, upload/refresh controls -->
  </div>
</template>

<script setup>
import { useResearchAssetState } from '@/composables/consumer/useResearchAssetState.js'

const props = defineProps({
  simulationId: { type: String, required: true },
})

const { researchAssets, researchAssetLoading, addResearchAsset, removeResearchAsset } = useResearchAssetState()
</script>
```

Implementation notes:

- same pattern as ComparisonWorkspace: composable owns state, component owns template
- keep the same CSS class names so existing styles apply without changes

- [ ] **Step 5: Refactor Step4Report.vue to compose the new subcomponents**

Replace the extracted inline sections with:

```vue
<template>
  <ConsumerReportHeader :simulation-id="simulationId" :simulation-label="simulationLabel" />
  <ComparisonWorkspace :simulation-id="simulationId" />
  <ResearchAssetWorkspace :simulation-id="simulationId" />
  <!-- remaining non-consumer sections stay inline -->
</template>

<script setup>
import ConsumerReportHeader from '@/components/consumer/ConsumerReportHeader.vue'
import ComparisonWorkspace from '@/components/consumer/ComparisonWorkspace.vue'
import ResearchAssetWorkspace from '@/components/consumer/ResearchAssetWorkspace.vue'
</script>
```

Implementation notes:

- Step4Report.vue should become substantially smaller after this extraction
- do not change any lifecycle hooks, route guards, or non-consumer sections
- `consumer.js` remains the only API facade imported by the subcomponents

- [ ] **Step 6: Run frontend build to confirm no import or template errors**

Run:

```powershell
Set-Location D:\project\MiroFish\.worktrees\phase5a-identity\frontend
npm run build
```

Expected:

- Vite build succeeds
- no unresolved import or template reference errors

- [ ] **Step 7: Commit the Step4Report extraction batch**

```bash
git add frontend/src/components/consumer/ConsumerReportHeader.vue frontend/src/components/consumer/ComparisonWorkspace.vue frontend/src/components/consumer/ResearchAssetWorkspace.vue frontend/src/components/Step4Report.vue
git commit -m "refactor: extract Step4Report consumer workspace into subcomponents"
```

## Task 3: Extract Step3Simulation Branch/Intervention Workspace

**Files:**
- Create: `frontend/src/composables/consumer/useBranchInterventionState.js`
- Create: `frontend/src/components/consumer/BranchInterventionWorkspace.vue`
- Modify: `frontend/src/components/Step3Simulation.vue`

- [ ] **Step 1: Write the failing composable test**

```js
import { test } from 'node:test'
import assert from 'node:assert/strict'

import { useBranchInterventionState } from '../../src/composables/consumer/useBranchInterventionState.js'

test('useBranchInterventionState exposes branches and interventions', () => {
  const state = useBranchInterventionState()
  assert.deepEqual(state.branches.value, [])
  assert.deepEqual(state.interventions.value, [])
  assert.equal(state.branchLoading.value, false)
})

test('useBranchInterventionState addBranch pushes to list', () => {
  const state = useBranchInterventionState()
  state.addBranch({ id: 'b1', name: 'Branch A' })
  assert.equal(state.branches.value.length, 1)
})
```

- [ ] **Step 2: Run the targeted node test to confirm it fails**

Run:

```powershell
Set-Location D:\project\MiroFish\.worktrees\phase5a-identity
node --test frontend/tests/composables/useBranchInterventionState.test.js
```

Expected:

- test fails because the composable module does not exist yet

- [ ] **Step 3: Implement useBranchInterventionState.js**

Create `frontend/src/composables/consumer/useBranchInterventionState.js`:

```js
import { ref } from 'vue'

export function useBranchInterventionState() {
  const branches = ref([])
  const interventions = ref([])
  const branchLoading = ref(false)
  const interventionLoading = ref(false)

  function addBranch(branch) {
    branches.value.push(branch)
  }

  function removeBranch(id) {
    branches.value = branches.value.filter(b => b.id !== id)
  }

  function setBranches(list) {
    branches.value = list
  }

  function addIntervention(intervention) {
    interventions.value.push(intervention)
  }

  function removeIntervention(id) {
    interventions.value = interventions.value.filter(i => i.id !== id)
  }

  function setInterventions(list) {
    interventions.value = list
  }

  return {
    branches,
    interventions,
    branchLoading,
    interventionLoading,
    addBranch,
    removeBranch,
    setBranches,
    addIntervention,
    removeIntervention,
    setInterventions,
  }
}
```

- [ ] **Step 4: Re-run the composable test**

Run:

```powershell
Set-Location D:\project\MiroFish\.worktrees\phase5a-identity
node --test frontend/tests/composables/useBranchInterventionState.test.js
```

Expected:

- composable test passes

- [ ] **Step 5: Create BranchInterventionWorkspace.vue**

Extract the branch and intervention markup from `Step3Simulation.vue` into `frontend/src/components/consumer/BranchInterventionWorkspace.vue`.

```vue
<template>
  <div class="branch-intervention-workspace">
    <!-- branch list, intervention list, add/remove controls -->
  </div>
</template>

<script setup>
import { useBranchInterventionState } from '@/composables/consumer/useBranchInterventionState.js'

const props = defineProps({
  simulationId: { type: String, required: true },
})

const {
  branches,
  interventions,
  branchLoading,
  interventionLoading,
  addBranch,
  removeBranch,
  addIntervention,
  removeIntervention,
} = useBranchInterventionState()
</script>
```

Implementation notes:

- the composable owns reactive state; the component owns template and event handlers
- emit events to Step3Simulation for cross-section coordination
- `consumer.js` remains the only API facade

- [ ] **Step 6: Refactor Step3Simulation.vue to use the new subcomponent**

Replace the extracted branch/intervention sections with:

```vue
<template>
  <BranchInterventionWorkspace :simulation-id="simulationId" />
  <!-- remaining non-consumer sections stay inline -->
</template>

<script setup>
import BranchInterventionWorkspace from '@/components/consumer/BranchInterventionWorkspace.vue'
</script>
```

Implementation notes:

- Step3Simulation.vue should lose consumer-workspace-specific state after extraction
- do not change lifecycle hooks, route guards, or non-consumer simulation controls
- keep the same CSS class names so existing styles apply without changes

- [ ] **Step 7: Run frontend build and composable tests**

Run:

```powershell
Set-Location D:\project\MiroFish\.worktrees\phase5a-identity
node --test frontend/tests/composables/useBranchInterventionState.test.js frontend/tests/composables/useComparisonState.test.js frontend/tests/composables/useResearchAssetState.test.js
Set-Location frontend
npm run build
```

Expected:

- all composable tests pass
- Vite build succeeds

- [ ] **Step 8: Commit the Step3Simulation extraction batch**

```bash
git add frontend/src/composables/consumer/useBranchInterventionState.js frontend/src/components/consumer/BranchInterventionWorkspace.vue frontend/src/components/Step3Simulation.vue frontend/tests/composables/useBranchInterventionState.test.js
git commit -m "refactor: extract Step3Simulation branch/intervention workspace"
```

## Task 4: Align Step5Interaction to Shared Helpers and Run Final Regression

**Files:**
- Create: `frontend/src/components/consumer/ComparisonSnapshotWorkspace.vue`
- Modify: `frontend/src/components/Step5Interaction.vue`

- [ ] **Step 1: Review Step5Interaction.vue for comparison and snapshot sections**

Read `frontend/src/components/Step5Interaction.vue` and mark:
- the comparison snapshot display section
- any inline comparison-workspace markup that duplicates `ComparisonWorkspace.vue` logic

- [ ] **Step 2: Create ComparisonSnapshotWorkspace.vue**

Extract comparison snapshot display into `frontend/src/components/consumer/ComparisonSnapshotWorkspace.vue`.

```vue
<template>
  <div class="comparison-snapshot-workspace">
    <!-- snapshot cards, comparison summary display -->
  </div>
</template>

<script setup>
import { useComparisonState } from '@/composables/consumer/useComparisonState.js'

const props = defineProps({
  simulationId: { type: String, required: true },
})

const { comparisons, comparisonLoading, setComparisons } = useComparisonState()
</script>
```

Implementation notes:

- this is a read-focused sibling of `ComparisonWorkspace.vue` — it reuses the same composable
- do not add add/remove controls; this workspace is for display only
- emit events to Step5Interaction if the parent needs to react to snapshot changes

- [ ] **Step 3: Refactor Step5Interaction.vue to use ComparisonSnapshotWorkspace**

Replace the inline comparison snapshot section with:

```vue
<template>
  <ComparisonSnapshotWorkspace :simulation-id="simulationId" />
  <!-- remaining non-consumer sections stay inline -->
</template>

<script setup>
import ComparisonSnapshotWorkspace from '@/components/consumer/ComparisonSnapshotWorkspace.vue'
</script>
```

Implementation notes:

- Step5Interaction.vue should lose consumer-workspace-specific state after extraction
- do not change lifecycle hooks, route guards, or chat/interaction sections
- `consumer.js` remains the only API facade imported by the subcomponent

- [ ] **Step 4: Run the full frontend regression**

Run:

```powershell
Set-Location D:\project\MiroFish\.worktrees\phase5a-identity
node --test frontend/tests/composables/useComparisonState.test.js frontend/tests/composables/useResearchAssetState.test.js frontend/tests/composables/useBranchInterventionState.test.js frontend/tests/consumerBrief.test.js frontend/tests/consumerMode.test.js frontend/tests/pendingUpload.test.js frontend/tests/graphApi.test.js
Set-Location frontend
npm run build
```

Expected:

- all node tests pass
- Vite build succeeds
- `consumer.js` remains the only consumer API route facade
- no backend files are touched

- [ ] **Step 5: Commit the Step5Interaction alignment batch**

```bash
git add frontend/src/components/consumer/ComparisonSnapshotWorkspace.vue frontend/src/components/Step5Interaction.vue
git commit -m "refactor: align Step5Interaction to shared comparison snapshot helpers"
```

## Final Verification

- [ ] Run the complete frontend regression

```powershell
Set-Location D:\project\MiroFish\.worktrees\phase5a-identity
node --test frontend/tests/composables/useComparisonState.test.js frontend/tests/composables/useResearchAssetState.test.js frontend/tests/composables/useBranchInterventionState.test.js frontend/tests/consumerBrief.test.js frontend/tests/consumerMode.test.js frontend/tests/pendingUpload.test.js frontend/tests/graphApi.test.js
Set-Location frontend
npm run build
```

- [ ] Confirm measurable acceptance criteria

Checklist:

- `Step4Report.vue` is substantially smaller after subcomponent extraction
- `Step3Simulation.vue` no longer holds consumer-workspace-specific branch/intervention state
- `Step5Interaction.vue` no longer holds consumer-workspace-specific comparison snapshot state
- `consumer.js` remains the only consumer API route facade (no new route modules)
- no backend files are touched
- `npm run build` succeeds
- all targeted node tests pass

- [ ] Perform a manual consumer-workspace smoke check

Checklist:

- open the report step and confirm the consumer header, comparison workspace, and research asset workspace render correctly
- open the simulation step and confirm branch and intervention controls still work
- open the interaction step and confirm comparison snapshots display correctly
- confirm no visual regressions in the consumer flow from home through interaction

## Notes for Execution

- Execute against `D:\project\MiroFish\.worktrees\phase5a-identity`, not the root `main` worktree
- The Phase 6A plan is at `docs/superpowers/plans/2026-04-23-consumer-simulation-phase6a-product-surface.md`
- Keep the scope to frontend modularization only; do not touch backend routes, persistence behavior, or `project_type` semantics
