import { test } from 'vitest'
import assert from 'node:assert/strict'
import { readFileSync } from 'fs'
import { fileURLToPath } from 'url'
import { dirname, join } from 'path'

import {
  TASK_STATE_SCHEMA_VERSION,
  getPollingDelay,
  normalizeTaskState,
  selectStatusTransport,
  shouldStopPolling,
} from '../src/utils/taskStateMachine.ts'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)
const root = join(__dirname, '..')

test('polling delay uses exponential backoff capped at 8s', () => {
  assert.deepStrictEqual(
    [0, 1, 2, 3, 4, 5].map(attempt => getPollingDelay(attempt)),
    [1000, 2000, 4000, 8000, 8000, 8000]
  )
})

test('polling stops after 30 attempts or 5 minutes', () => {
  assert.equal(shouldStopPolling({ attempts: 29, elapsedMs: 299000 }), false)
  assert.equal(shouldStopPolling({ attempts: 30, elapsedMs: 1000 }), true)
  assert.equal(shouldStopPolling({ attempts: 1, elapsedMs: 300000 }), true)
  assert.equal(shouldStopPolling({ status: 'completed', attempts: 0, elapsedMs: 0 }), true)
})

test('normalizeTaskState maps failed timeout and llm fallback into friendly UI states', () => {
  const failed = normalizeTaskState({
    status: 'failed',
    error_code: 'SIMULATION_RUNTIME_ERROR',
    error: 'worker failed',
  })
  assert.equal(failed.schema_version, TASK_STATE_SCHEMA_VERSION)
  assert.equal(failed.kind, 'failed')
  assert.match(failed.title, /Simulation/)
  assert.ok(!failed.message.includes('failed'))

  const timeout = normalizeTaskState({ status: 'timeout' })
  assert.equal(timeout.kind, 'timeout')
  assert.match(timeout.message, /timed out/i)

  const llm = normalizeTaskState({ llm_fallback_reason: 'timeout' })
  assert.equal(llm.kind, 'llm_degraded')
  assert.equal(llm.severity, 'warning')
})

test('transport selection falls back from websocket to sse then polling', () => {
  assert.equal(selectStatusTransport({ websocketAvailable: true, eventSourceAvailable: true }), 'websocket')
  assert.equal(selectStatusTransport({ websocketAvailable: false, eventSourceAvailable: true }), 'sse')
  assert.equal(selectStatusTransport({ websocketAvailable: false, eventSourceAvailable: false }), 'polling')
})

test('Step3Simulation mounts exceptional state UI and UX doc records state schema', () => {
  const step3 = readFileSync(join(root, 'src/components/Step3Simulation.vue'), 'utf-8')
  const doc = readFileSync(join(root, '../docs/product/ux-design.md'), 'utf-8')

  assert.ok(step3.includes('RuntimeExceptionalState'), 'Step3 must render the exception state component')
  assert.ok(step3.includes('getPollingDelay'), 'Step3 must use exponential polling helper')
  assert.ok(doc.includes(TASK_STATE_SCHEMA_VERSION), 'UX doc must record versioned state schema')
  assert.ok(doc.includes('1s → 2s → 4s → 8s'), 'UX doc must record backoff contract')
  assert.ok(doc.includes('SSE'), 'UX doc must record SSE fallback')
})
