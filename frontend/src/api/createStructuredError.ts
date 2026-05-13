// @ts-nocheck
/**
 * Build an Error that preserves backend structured diagnostic fields.
 *
 * @param {object} res - The backend response body (response.data).
 * @returns {Error}
 */
export function createStructuredError(res) {
  const message = res.error || res.message || 'Error'
  const err = new Error(message)

  err.payload = res
  err.message = message

  if (res.error_code !== undefined) {
    err.error_code = res.error_code
  }
  if (res.blocking_stage !== undefined) {
    err.blocking_stage = res.blocking_stage
  }
  if (res.recoverable !== undefined) {
    err.recoverable = res.recoverable
  }
  if (res.next_action !== undefined) {
    err.next_action = res.next_action
  }
  if (res.suggested_action !== undefined) {
    err.suggested_action = res.suggested_action
  }

  // Alias: ensure both next_action and suggested_action are present when either is.
  if (err.next_action !== undefined && err.suggested_action === undefined) {
    err.suggested_action = err.next_action
  }
  if (err.suggested_action !== undefined && err.next_action === undefined) {
    err.next_action = err.suggested_action
  }

  if (res.details !== undefined) {
    err.details = res.details
  }

  return err
}

export function createStructuredErrorFromAxiosError(error) {
  const payload = error?.response?.data
  if (!payload || typeof payload !== 'object') {
    return error
  }

  const err = createStructuredError(payload)
  if (error.response.status !== undefined) {
    err.http_status = error.response.status
  }
  err.original_error = error
  return err
}
