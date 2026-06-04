import { afterEach, test } from 'vitest'
import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

import {
  getConsumerInterviewHandoffStorageKey,
  saveConsumerInterviewHandoff,
} from '../src/utils/consumerResearchActions.ts'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

const step5Path = join(__dirname, '../src/components/Step5Interaction.vue')
const composablePath = join(__dirname, '../src/composables/useStep5InterviewHandoffState.ts')

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

test('useStep5InterviewHandoffState loads, clears, and resets handoff context', async () => {
  assert.ok(existsSync(composablePath), 'useStep5InterviewHandoffState composable must exist')

  const store = installLocalStorageMock()
  const { useStep5InterviewHandoffState } = await import('../src/composables/useStep5InterviewHandoffState.ts')
  const state = useStep5InterviewHandoffState()
  const targetContext = {
    section_index: 2,
    claim: 'Price concern',
  }

  assert.equal(state.interviewHandoffContext.value, null)

  saveConsumerInterviewHandoff('sim-1', targetContext)
  state.loadInterviewHandoff('sim-1')
  assert.deepEqual(state.interviewHandoffContext.value, targetContext)

  state.clearInterviewHandoff('sim-1')
  assert.equal(state.interviewHandoffContext.value, null)
  assert.equal(store.has(getConsumerInterviewHandoffStorageKey('sim-1')), false)

  saveConsumerInterviewHandoff('sim-2', targetContext)
  state.loadInterviewHandoff(null)
  assert.equal(state.interviewHandoffContext.value, null)

  state.loadInterviewHandoff('sim-2')
  assert.deepEqual(state.interviewHandoffContext.value, targetContext)
  state.clearInterviewHandoff(null)
  assert.deepEqual(state.interviewHandoffContext.value, targetContext)
})

test('Step5Interaction delegates interview handoff state to useStep5InterviewHandoffState', () => {
  const step5Content = readFileSync(step5Path, 'utf-8')
  assert.ok(step5Content.includes("import { useStep5InterviewHandoffState } from '../composables/useStep5InterviewHandoffState'"), 'Step5 must import useStep5InterviewHandoffState')
  assert.ok(step5Content.includes('useStep5InterviewHandoffState()'), 'Step5 must initialize interview handoff state via composable')

  for (const token of [
    'const interviewHandoffContext = ref(null)',
    'loadConsumerInterviewHandoff',
    'clearConsumerInterviewHandoff',
    'interviewHandoffContext.value = loadConsumerInterviewHandoff(props.simulationId)',
    'clearConsumerInterviewHandoff(props.simulationId)',
  ]) {
    assert.ok(!step5Content.includes(token), `Step5 should not inline interview handoff token: ${token}`)
  }
})
