import { test } from 'vitest'
import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { ref } from 'vue'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

const step4Path = join(__dirname, '../src/components/Step4Report.vue')
const composablePath = join(__dirname, '../src/composables/useStep4ReportPollingState.ts')

function createHarness(overrides = {}) {
  const reportId = ref('report-1')
  const isComplete = ref(false)
  const rightPanel = ref({ scrollTop: 0, scrollHeight: 320 })
  const logContent = ref({ scrollTop: 0, scrollHeight: 180 })
  const patches = []
  const warnings = []
  const intervals = []
  const cleared = []
  const api = {
    getAgentLog: async (_id, _line) => ({
      success: true,
      data: {
        from_line: 5,
        logs: [
          { action: 'section_start', section_index: 2, timestamp: 't1' },
          { action: 'section_complete', section_index: 2, timestamp: 't2', details: { content: 'done' } },
        ],
      },
    }),
    getConsoleLog: async (_id, _line) => ({
      success: true,
      data: {
        from_line: 3,
        logs: ['hello', 'world'],
      },
    }),
    ...overrides.api,
  }

  return {
    reportId,
    isComplete,
    rightPanel,
    logContent,
    patches,
    warnings,
    api,
    applyAgentLogStatePatch: patch => patches.push(patch),
    nextTick: fn => fn(),
    setIntervalFn: (fn, delay) => {
      const id = { fn, delay }
      intervals.push(id)
      return id
    },
    clearIntervalFn: id => cleared.push(id),
    warn: (...args) => warnings.push(args),
    intervals,
    cleared,
  }
}

test('useStep4ReportPollingState fetches agent and console logs', async () => {
  assert.ok(existsSync(composablePath), 'useStep4ReportPollingState composable must exist')

  const { useStep4ReportPollingState } = await import('../src/composables/useStep4ReportPollingState.ts')
  const harness = createHarness()
  const state = useStep4ReportPollingState(harness)

  await state.fetchAgentLog()
  await state.fetchConsoleLog()

  assert.equal(state.agentLogs.value.length, 2)
  assert.equal(state.agentLogLine.value, 7)
  assert.deepEqual(harness.patches, [
    { currentSectionIndex: 2 },
    { generatedSection: { index: 2, content: 'done' }, expandedContentIndex: 1, currentSectionIndex: null },
  ])
  assert.equal(harness.rightPanel.value.scrollTop, 320)
  assert.deepEqual(state.consoleLogs.value, ['hello', 'world'])
  assert.equal(state.consoleLogLine.value, 5)
  assert.equal(harness.logContent.value.scrollTop, 180)
})

test('useStep4ReportPollingState scrolls completed agent runs to top', async () => {
  const { useStep4ReportPollingState } = await import('../src/composables/useStep4ReportPollingState.ts')
  const harness = createHarness()
  harness.isComplete.value = true
  harness.rightPanel.value.scrollTop = 99
  const state = useStep4ReportPollingState(harness)

  await state.fetchAgentLog()

  assert.equal(harness.rightPanel.value.scrollTop, 0)
})

test('useStep4ReportPollingState starts, stops, and resets polling state', async () => {
  const { useStep4ReportPollingState } = await import('../src/composables/useStep4ReportPollingState.ts')
  const harness = createHarness({
    api: {
      getAgentLog: async () => ({ success: true, data: { from_line: 0, logs: [] } }),
      getConsoleLog: async () => ({ success: true, data: { from_line: 0, logs: [] } }),
    },
  })
  const state = useStep4ReportPollingState(harness)

  state.agentLogs.value.push({ action: 'old' })
  state.consoleLogs.value.push('old')
  state.agentLogLine.value = 9
  state.consoleLogLine.value = 4
  state.resetPollingState()
  assert.deepEqual(state.agentLogs.value, [])
  assert.deepEqual(state.consoleLogs.value, [])
  assert.equal(state.agentLogLine.value, 0)
  assert.equal(state.consoleLogLine.value, 0)

  await state.startPolling()
  await state.startPolling()
  assert.equal(harness.intervals.length, 2)
  assert.deepEqual(harness.intervals.map(i => i.delay), [2000, 1500])

  state.stopPolling()
  assert.equal(harness.cleared.length, 2)
})

test('useStep4ReportPollingState skips missing report id and warns on API failures', async () => {
  const { useStep4ReportPollingState } = await import('../src/composables/useStep4ReportPollingState.ts')
  let agentCalls = 0
  let consoleCalls = 0
  const harness = createHarness({
    api: {
      getAgentLog: async () => {
        agentCalls += 1
        throw new Error('agent down')
      },
      getConsoleLog: async () => {
        consoleCalls += 1
        throw new Error('console down')
      },
    },
  })
  const state = useStep4ReportPollingState(harness)

  harness.reportId.value = ''
  await state.fetchAgentLog()
  await state.fetchConsoleLog()
  assert.equal(agentCalls, 0)
  assert.equal(consoleCalls, 0)

  harness.reportId.value = 'report-2'
  await state.fetchAgentLog()
  await state.fetchConsoleLog()
  assert.equal(agentCalls, 1)
  assert.equal(consoleCalls, 1)
  assert.equal(harness.warnings.length, 2)
})

test('Step4Report delegates polling state to useStep4ReportPollingState', () => {
  const step4Content = readFileSync(step4Path, 'utf-8')
  assert.ok(step4Content.includes("import { useStep4ReportPollingState } from '../composables/useStep4ReportPollingState'"), 'Step4 must import useStep4ReportPollingState')
  assert.ok(step4Content.includes('useStep4ReportPollingState({'), 'Step4 must initialize polling state via composable')

  for (const token of [
    'getAgentLog, getConsoleLog',
    'const agentLogs = ref([])',
    'const consoleLogs = ref([])',
    'const agentLogLine = ref(0)',
    'const consoleLogLine = ref(0)',
    'let agentLogTimer = null',
    'let consoleLogTimer = null',
    'const fetchAgentLog = async ()',
    'const fetchConsoleLog = async ()',
    'const startPolling = ()',
    'const stopPolling = ()',
  ]) {
    assert.ok(!step4Content.includes(token), `Step4 should not inline polling token: ${token}`)
  }
})
