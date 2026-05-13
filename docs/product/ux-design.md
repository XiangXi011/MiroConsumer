# UX Exceptional States

This document records the front-end state contract for long-running simulation
tasks.

## State Schema

`task-state.v1` is the current versioned state-machine schema. A normalized
state contains:

- `schema_version`: always `task-state.v1`
- `kind`: `failed`, `timeout`, `llm_degraded`, or `reconnecting`
- `severity`: `info`, `warning`, or `error`
- `title`, `message`, and `recovery_action`
- optional `retry_attempt` and `next_retry_ms`

## Exceptional States

- **Task timeout**: show a friendly timeout state with restart guidance.
- **Task failure**: show a diagnostic state instead of rendering only `failed`.
- **LLM timeout**: keep the run visible and show progressive degraded-mode
  messaging when the runtime falls back to template reasoning.
- **Network interruption**: preserve current results and reconnect
  automatically.

## Polling Contract

Status polling uses exponential backoff on repeated failures:

`1s → 2s → 4s → 8s`

The client stops after 30 failed attempts or 5 minutes, whichever comes first.

## Transport Fallback

The preferred transport order is WebSocket, then SSE, then polling. SSE is the
first fallback when WebSocket is unavailable. Polling remains the final
compatibility path for local development and restricted networks.
