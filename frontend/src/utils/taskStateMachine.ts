export const TASK_STATE_SCHEMA_VERSION = 'task-state.v1'

export type TaskStateKind =
  | 'failed'
  | 'timeout'
  | 'llm_degraded'
  | 'reconnecting'

export interface RuntimeTaskState {
  schema_version: string
  kind: TaskStateKind
  severity: 'info' | 'warning' | 'error'
  title: string
  message: string
  recovery_action: string
  retry_attempt?: number
  next_retry_ms?: number
  terminal?: boolean
}

interface PollingStopInput {
  status?: string
  attempts: number
  elapsedMs: number
  maxAttempts?: number
  maxElapsedMs?: number
}

export function getPollingDelay(
  attempt: number,
  baseMs = 1000,
  maxMs = 8000,
): number {
  const safeAttempt = Math.max(0, Number(attempt) || 0)
  return Math.min(maxMs, baseMs * (2 ** safeAttempt))
}

export function shouldStopPolling({
  status,
  attempts,
  elapsedMs,
  maxAttempts = 30,
  maxElapsedMs = 300000,
}: PollingStopInput): boolean {
  if (['completed', 'stopped', 'failed', 'timeout'].includes(String(status || '').toLowerCase())) {
    return true
  }
  return attempts >= maxAttempts || elapsedMs >= maxElapsedMs
}

export function selectStatusTransport({
  websocketAvailable,
  eventSourceAvailable,
}: {
  websocketAvailable: boolean
  eventSourceAvailable: boolean
}): 'websocket' | 'sse' | 'polling' {
  if (websocketAvailable) return 'websocket'
  if (eventSourceAvailable) return 'sse'
  return 'polling'
}

export function normalizeTaskState(payload: Record<string, any> | null | undefined): RuntimeTaskState | null {
  if (!payload) return null
  const status = String(payload.runner_status || payload.status || '').toLowerCase()
  const errorCode = String(payload.error_code || '').toUpperCase()
  const fallbackReason = String(
    payload.llm_fallback_reason || payload.fallback_reason || payload.reasoning_error || '',
  ).toLowerCase()

  if (status === 'failed' || errorCode.includes('RUNTIME_ERROR')) {
    return {
      schema_version: TASK_STATE_SCHEMA_VERSION,
      kind: 'failed',
      severity: 'error',
      title: 'Simulation needs attention',
      message: 'The run stopped before completion. Review the latest diagnostics and retry from the last stable checkpoint.',
      recovery_action: 'Retry from checkpoint',
      terminal: true,
    }
  }

  if (status === 'timeout') {
    return {
      schema_version: TASK_STATE_SCHEMA_VERSION,
      kind: 'timeout',
      severity: 'error',
      title: 'Simulation timed out',
      message: 'This run timed out before all platform rounds reported a stable result.',
      recovery_action: 'Reduce rounds or restart',
      terminal: true,
    }
  }

  if (fallbackReason.includes('timeout') || errorCode.includes('LLM_TIMEOUT')) {
    return {
      schema_version: TASK_STATE_SCHEMA_VERSION,
      kind: 'llm_degraded',
      severity: 'warning',
      title: 'LLM degraded mode',
      message: 'Some reasoning calls exceeded the timeout and the run is continuing with template fallback.',
      recovery_action: 'Continue and review diagnostics',
      terminal: false,
    }
  }

  if (status === 'network_error' || errorCode === 'NETWORK_ERROR') {
    const nextRetryMs = Number(payload.next_retry_ms || 0)
    const retryAttempt = Number(payload.retry_attempt || 0)
    return {
      schema_version: TASK_STATE_SCHEMA_VERSION,
      kind: 'reconnecting',
      severity: 'warning',
      title: 'Reconnecting',
      message: 'The status stream was interrupted. The workbench will restore state automatically.',
      recovery_action: 'Automatic retry',
      retry_attempt: retryAttempt,
      next_retry_ms: nextRetryMs,
      terminal: false,
    }
  }

  return null
}
