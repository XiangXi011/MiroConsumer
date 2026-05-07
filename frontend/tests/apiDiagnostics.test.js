import { test } from 'node:test'
import assert from 'node:assert/strict'
import {
  createStructuredError,
  createStructuredErrorFromAxiosError,
} from '../src/api/createStructuredError.js'

test('createStructuredError preserves payload as full response', () => {
  const res = { success: false, error: 'test error' }
  const err = createStructuredError(res)
  assert.strictEqual(err.payload, res)
})

test('createStructuredError preserves error_code from response', () => {
  const res = { success: false, error: 'blocked', error_code: 'PHASE6J_MISSING' }
  const err = createStructuredError(res)
  assert.equal(err.error_code, 'PHASE6J_MISSING')
})

test('createStructuredError preserves blocking_stage from response', () => {
  const res = { success: false, error: 'blocked', blocking_stage: 'phase6j' }
  const err = createStructuredError(res)
  assert.equal(err.blocking_stage, 'phase6j')
})

test('createStructuredError preserves recoverable from response', () => {
  const res = { success: false, error: 'blocked', recoverable: true }
  const err = createStructuredError(res)
  assert.equal(err.recoverable, true)
})

test('createStructuredError preserves next_action and aliases suggested_action', () => {
  const res = { success: false, error: 'blocked', next_action: 'retry' }
  const err = createStructuredError(res)
  assert.equal(err.next_action, 'retry')
  assert.equal(err.suggested_action, 'retry')
})

test('createStructuredError aliases suggested_action to next_action when next_action missing', () => {
  const res = { success: false, error: 'blocked', suggested_action: 'wait' }
  const err = createStructuredError(res)
  assert.equal(err.next_action, 'wait')
  assert.equal(err.suggested_action, 'wait')
})

test('createStructuredError preserves details from response', () => {
  const res = { success: false, error: 'blocked', details: { foo: 'bar' } }
  const err = createStructuredError(res)
  assert.deepStrictEqual(err.details, { foo: 'bar' })
})

test('createStructuredError uses error field for message', () => {
  const res = { success: false, error: 'custom error' }
  const err = createStructuredError(res)
  assert.equal(err.message, 'custom error')
})

test('createStructuredError falls back to message field for error message', () => {
  const res = { success: false, message: 'msg fallback' }
  const err = createStructuredError(res)
  assert.equal(err.message, 'msg fallback')
})

test('createStructuredError does not drop Phase6J payload in details', () => {
  const res = {
    success: false,
    error: 'artifact missing',
    error_code: 'PHASE6J_MISSING',
    details: { phase6j_payload: { status: 'incomplete', artifact_id: 'art-1' } },
  }
  const err = createStructuredError(res)
  assert.deepStrictEqual(err.details.phase6j_payload, { status: 'incomplete', artifact_id: 'art-1' })
})

test('createStructuredError defaults to "Error" when no message present', () => {
  const res = { success: false }
  const err = createStructuredError(res)
  assert.equal(err.message, 'Error')
})

test('createStructuredError prefers error over message when both present', () => {
  const res = { success: false, error: 'err wins', message: 'msg loses' }
  const err = createStructuredError(res)
  assert.equal(err.message, 'err wins')
})

test('createStructuredErrorFromAxiosError preserves non-2xx backend payload', () => {
  const axiosError = {
    response: {
      status: 403,
      data: {
        success: false,
        error: 'Phase6J blocked',
        error_code: 'PHASE6J_BLOCKED',
        blocking_stage: 'calibration',
        next_action: 'inspect_failed_checks',
        details: { failed_checks: ['reasoning_backend_coverage'] },
      },
    },
  }

  const err = createStructuredErrorFromAxiosError(axiosError)

  assert.equal(err.message, 'Phase6J blocked')
  assert.equal(err.http_status, 403)
  assert.equal(err.error_code, 'PHASE6J_BLOCKED')
  assert.equal(err.blocking_stage, 'calibration')
  assert.equal(err.next_action, 'inspect_failed_checks')
  assert.deepStrictEqual(err.details.failed_checks, ['reasoning_backend_coverage'])
})

test('createStructuredErrorFromAxiosError returns original network error without response payload', () => {
  const networkError = new Error('Network Error')
  assert.strictEqual(createStructuredErrorFromAxiosError(networkError), networkError)
})
