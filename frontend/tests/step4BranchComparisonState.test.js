import { afterEach, test } from 'vitest'
import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { ref } from 'vue'

import {
  loadSelectedBranch,
  saveSelectedBranch,
} from '../src/utils/consumerMode.ts'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

const step4Path = join(__dirname, '../src/components/Step4Report.vue')
const composablePath = join(__dirname, '../src/composables/useStep4BranchComparisonState.ts')

function installLocalStorageMock() {
  const store = new Map()
  globalThis.window = {
    localStorage: {
      getItem: key => (store.has(key) ? store.get(key) : null),
      setItem: (key, value) => store.set(key, String(value)),
      removeItem: key => store.delete(key),
    },
  }
  return store
}

function createHarness(overrides = {}) {
  const simulationId = ref('sim-1')
  const isConsumerMode = ref(true)
  const calls = []
  const getBranchComparison = async (simId, branchId) => {
    calls.push([simId, branchId])
    return {
      success: true,
      data: {
        branch_id: branchId,
        branch_name: 'Safer claim',
        fork_round: 2,
        base_summary: { post_propagation_acceptance: { positive: 0.4 }, events_count: 3 },
        branch_summary: { post_propagation_acceptance: { positive: 0.55 }, events_count: 4 },
      },
    }
  }
  return {
    simulationId,
    isConsumerMode,
    calls,
    getBranchComparison,
    t: (_key, fallback) => fallback || _key,
    ...overrides,
  }
}

afterEach(() => {
  delete globalThis.window
})

test('useStep4BranchComparisonState loads and formats selected branch comparison', async () => {
  assert.ok(existsSync(composablePath), 'useStep4BranchComparisonState composable must exist')

  installLocalStorageMock()
  saveSelectedBranch('sim-1', 'branch-a')
  const { useStep4BranchComparisonState } = await import('../src/composables/useStep4BranchComparisonState.ts')
  const harness = createHarness()
  const state = useStep4BranchComparisonState(harness)

  await state.loadBranchComparison()

  assert.deepEqual(harness.calls, [['sim-1', 'branch-a']])
  assert.equal(state.branchComparisonRaw.value.branch_id, 'branch-a')
  assert.equal(state.branchComparisonFormatted.value.branchId, 'branch-a')
  assert.equal(state.branchComparisonFormatted.value.branchName, 'Safer claim')
})

test('useStep4BranchComparisonState clears state when prerequisites or selection are missing', async () => {
  installLocalStorageMock()
  const { useStep4BranchComparisonState } = await import('../src/composables/useStep4BranchComparisonState.ts')
  const harness = createHarness()
  const state = useStep4BranchComparisonState(harness)

  state.branchComparisonRaw.value = { branch_id: 'old' }
  harness.isConsumerMode.value = false
  await state.loadBranchComparison()
  assert.equal(state.branchComparisonRaw.value, null)
  assert.equal(state.branchComparisonFormatted.value, null)
  assert.deepEqual(harness.calls, [])

  harness.isConsumerMode.value = true
  harness.simulationId.value = ''
  state.branchComparisonRaw.value = { branch_id: 'old' }
  await state.loadBranchComparison()
  assert.equal(state.branchComparisonRaw.value, null)
  assert.deepEqual(harness.calls, [])

  harness.simulationId.value = 'sim-1'
  state.branchComparisonRaw.value = { branch_id: 'old' }
  await state.loadBranchComparison()
  assert.equal(state.branchComparisonRaw.value, null)
  assert.deepEqual(harness.calls, [])
})

test('useStep4BranchComparisonState clears persisted selection when API fails', async () => {
  installLocalStorageMock()
  saveSelectedBranch('sim-1', 'branch-missing')
  const { useStep4BranchComparisonState } = await import('../src/composables/useStep4BranchComparisonState.ts')
  const state = useStep4BranchComparisonState(createHarness({
    getBranchComparison: async () => ({ success: false, error: 'missing' }),
  }))

  await state.loadBranchComparison()
  assert.equal(state.branchComparisonRaw.value, null)
  assert.equal(loadSelectedBranch('sim-1'), null)

  saveSelectedBranch('sim-1', 'branch-throws')
  const throwingState = useStep4BranchComparisonState(createHarness({
    getBranchComparison: async () => {
      throw new Error('down')
    },
  }))
  await throwingState.loadBranchComparison()
  assert.equal(throwingState.branchComparisonRaw.value, null)
  assert.equal(loadSelectedBranch('sim-1'), null)
})

test('Step4Report delegates branch comparison state to useStep4BranchComparisonState', () => {
  const step4Content = readFileSync(step4Path, 'utf-8')
  assert.ok(step4Content.includes("import { useStep4BranchComparisonState } from '../composables/useStep4BranchComparisonState'"), 'Step4 must import useStep4BranchComparisonState')
  assert.ok(step4Content.includes('useStep4BranchComparisonState({'), 'Step4 must initialize branch comparison state via composable')

  for (const token of [
    'getBranchComparison',
    'loadSelectedBranch',
    'formatBranchComparison',
    'clearSelectedBranch',
    'const branchComparisonRaw = ref(null)',
    'const branchComparisonFormatted = computed(()',
    'const loadBranchComparison = async ()',
  ]) {
    assert.ok(!step4Content.includes(token), `Step4 should not inline branch comparison token: ${token}`)
  }
})
