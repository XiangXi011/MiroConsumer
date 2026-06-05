import { afterEach, test } from 'vitest'
import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { ref } from 'vue'

import {
  getConsumerInterviewHandoffStorageKey,
} from '../src/utils/consumerResearchActions.ts'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

const step4Path = join(__dirname, '../src/components/Step4Report.vue')
const composablePath = join(__dirname, '../src/composables/useStep4InsightDrawerState.ts')

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

afterEach(() => {
  delete globalThis.window
})

test('useStep4InsightDrawerState runs research actions and manages drawer state', async () => {
  assert.ok(existsSync(composablePath), 'useStep4InsightDrawerState composable must exist')

  const { useStep4InsightDrawerState } = await import('../src/composables/useStep4InsightDrawerState.ts')
  const simulationId = ref('sim-1')
  const calls = []
  const state = useStep4InsightDrawerState({
    simulationId,
    runConsumerResearchAction: async (id, payload) => {
      calls.push([id, payload])
      return { success: true, data: { title: 'Drawer result' } }
    },
  })

  assert.equal(state.showInsightDrawer.value, false)
  await state.handleRunAction({ action_type: 'verify' })

  assert.deepEqual(calls, [['sim-1', { action_type: 'verify' }]])
  assert.equal(state.showInsightDrawer.value, true)
  assert.equal(state.drawerLoading.value, false)
  assert.equal(state.drawerError.value, '')
  assert.deepEqual(state.drawerResult.value, { title: 'Drawer result' })

  state.closeInsightDrawer()
  assert.equal(state.showInsightDrawer.value, false)
  assert.equal(state.drawerResult.value, null)
})

test('useStep4InsightDrawerState skips missing simulation id and records action errors', async () => {
  const { useStep4InsightDrawerState } = await import('../src/composables/useStep4InsightDrawerState.ts')
  const simulationId = ref('')
  let calls = 0
  const state = useStep4InsightDrawerState({
    simulationId,
    runConsumerResearchAction: async () => {
      calls += 1
      throw new Error('action failed')
    },
  })

  await state.handleRunAction({ action_type: 'verify' })
  assert.equal(calls, 0)
  assert.equal(state.showInsightDrawer.value, false)

  simulationId.value = 'sim-2'
  await state.handleRunAction({ action_type: 'verify' })
  assert.equal(calls, 1)
  assert.equal(state.showInsightDrawer.value, true)
  assert.equal(state.drawerLoading.value, false)
  assert.equal(state.drawerError.value, 'action failed')
  assert.equal(state.drawerResult.value, null)
})

test('useStep4InsightDrawerState saves handoff context before navigating', async () => {
  const store = installLocalStorageMock()
  const { useStep4InsightDrawerState } = await import('../src/composables/useStep4InsightDrawerState.ts')
  const simulationId = ref('sim-3')
  const navigations = []
  const state = useStep4InsightDrawerState({
    simulationId,
    goToInteraction: () => navigations.push('go'),
  })

  state.handleOpenHandoff({ section_index: 4, claim: 'Trust signal' })

  const raw = store.get(getConsumerInterviewHandoffStorageKey('sim-3'))
  assert.ok(raw, 'handoff context should be persisted')
  assert.deepEqual(JSON.parse(raw).targetContext, { section_index: 4, claim: 'Trust signal' })
  assert.deepEqual(navigations, ['go'])
})

test('Step4Report delegates insight drawer state to useStep4InsightDrawerState', () => {
  const step4Content = readFileSync(step4Path, 'utf-8')
  assert.ok(step4Content.includes("import { useStep4InsightDrawerState } from '../composables/useStep4InsightDrawerState'"), 'Step4 must import useStep4InsightDrawerState')
  assert.ok(step4Content.includes('useStep4InsightDrawerState({'), 'Step4 must initialize insight drawer state via composable')

  for (const token of [
    'const closeInsightDrawer = ()',
    'const handleRunAction = async (payload)',
    'const handleOpenHandoff = (targetContext)',
    'const showInsightDrawer = ref(false)',
    'const drawerResult = ref(null)',
    'const drawerLoading = ref(false)',
    "const drawerError = ref('')",
    'runConsumerResearchAction',
    'normalizeConsumerResearchActionResponse',
    'saveConsumerInterviewHandoff',
  ]) {
    assert.ok(!step4Content.includes(token), `Step4 should not inline insight drawer token: ${token}`)
  }
})
