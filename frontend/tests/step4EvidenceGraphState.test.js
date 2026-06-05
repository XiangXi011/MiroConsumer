import { test } from 'vitest'
import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { ref } from 'vue'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

const step4Path = join(__dirname, '../src/components/Step4Report.vue')
const composablePath = join(__dirname, '../src/composables/useStep4EvidenceGraphState.ts')

function createHarness(overrides = {}) {
  const reportId = ref('report-1')
  const isConsumerMode = ref(true)
  const calls = []
  const getReportEvidenceGraph = async id => {
    calls.push(id)
    return { success: true, data: { nodes: [{ id: 'n1' }], edges: [] } }
  }
  return {
    reportId,
    isConsumerMode,
    calls,
    getReportEvidenceGraph,
    ...overrides,
  }
}

test('useStep4EvidenceGraphState loads evidence graph data', async () => {
  assert.ok(existsSync(composablePath), 'useStep4EvidenceGraphState composable must exist')

  const { useStep4EvidenceGraphState } = await import('../src/composables/useStep4EvidenceGraphState.ts')
  const harness = createHarness()
  const state = useStep4EvidenceGraphState(harness)

  await state.loadEvidenceGraph()

  assert.deepEqual(harness.calls, ['report-1'])
  assert.deepEqual(state.evidenceGraph.value, { nodes: [{ id: 'n1' }], edges: [] })
  assert.equal(state.evidenceGraphLoading.value, false)
  assert.equal(state.evidenceGraphError.value, '')
})

test('useStep4EvidenceGraphState clears graph when not applicable', async () => {
  const { useStep4EvidenceGraphState } = await import('../src/composables/useStep4EvidenceGraphState.ts')
  const harness = createHarness()
  const state = useStep4EvidenceGraphState(harness)

  state.evidenceGraph.value = { nodes: [{ id: 'old' }] }
  state.evidenceGraphError.value = 'old error'
  harness.isConsumerMode.value = false

  await state.loadEvidenceGraph()

  assert.deepEqual(harness.calls, [])
  assert.equal(state.evidenceGraph.value, null)
  assert.equal(state.evidenceGraphError.value, '')
  assert.equal(state.evidenceGraphLoading.value, false)

  harness.isConsumerMode.value = true
  harness.reportId.value = ''
  state.evidenceGraph.value = { nodes: [{ id: 'old' }] }
  await state.loadEvidenceGraph()
  assert.equal(state.evidenceGraph.value, null)
})

test('useStep4EvidenceGraphState records API failures and thrown errors', async () => {
  const { useStep4EvidenceGraphState } = await import('../src/composables/useStep4EvidenceGraphState.ts')
  const failed = useStep4EvidenceGraphState(createHarness({
    getReportEvidenceGraph: async () => ({ success: false, error: 'No graph' }),
  }))

  await failed.loadEvidenceGraph()
  assert.equal(failed.evidenceGraph.value, null)
  assert.equal(failed.evidenceGraphError.value, 'No graph')
  assert.equal(failed.evidenceGraphLoading.value, false)

  const thrown = useStep4EvidenceGraphState(createHarness({
    getReportEvidenceGraph: async () => {
      throw new Error('Network down')
    },
  }))

  await thrown.loadEvidenceGraph()
  assert.equal(thrown.evidenceGraph.value, null)
  assert.equal(thrown.evidenceGraphError.value, 'Network down')
  assert.equal(thrown.evidenceGraphLoading.value, false)
})

test('useStep4EvidenceGraphState resets graph state explicitly', async () => {
  const { useStep4EvidenceGraphState } = await import('../src/composables/useStep4EvidenceGraphState.ts')
  const state = useStep4EvidenceGraphState(createHarness())

  state.evidenceGraph.value = { nodes: [{ id: 'old' }] }
  state.evidenceGraphLoading.value = true
  state.evidenceGraphError.value = 'old error'
  state.resetEvidenceGraph()

  assert.equal(state.evidenceGraph.value, null)
  assert.equal(state.evidenceGraphLoading.value, false)
  assert.equal(state.evidenceGraphError.value, '')
})

test('Step4Report delegates evidence graph state to useStep4EvidenceGraphState', () => {
  const step4Content = readFileSync(step4Path, 'utf-8')
  assert.ok(step4Content.includes("import { useStep4EvidenceGraphState } from '../composables/useStep4EvidenceGraphState'"), 'Step4 must import useStep4EvidenceGraphState')
  assert.ok(step4Content.includes('useStep4EvidenceGraphState({'), 'Step4 must initialize evidence graph state via composable')

  for (const token of [
    'getReportEvidenceGraph',
    'const evidenceGraph = ref(null)',
    'const evidenceGraphLoading = ref(false)',
    "const evidenceGraphError = ref('')",
    'const loadEvidenceGraph = async ()',
    'evidenceGraph.value = null',
    "evidenceGraphError.value = ''",
  ]) {
    assert.ok(!step4Content.includes(token), `Step4 should not inline evidence graph token: ${token}`)
  }
})
