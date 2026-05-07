import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'fs'
import { fileURLToPath } from 'url'
import { dirname, join } from 'path'

import {
  buildSocietyRunSummaryItems,
  buildSocietyRunDiagnosticItems,
  formatSocietyDelta,
} from '../src/utils/societyRunSummary.js'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

test('buildSocietyRunSummaryItems formats fixed Phase 6G fields', () => {
  const items = buildSocietyRunSummaryItems({
    society_mode: 'standard',
    society_agents_count: 252,
    society_rounds_completed: 3,
    society_llm_budget_used: 8,
    status: 'running',
    current_agent_id: 'expanded_M03_17_xxx',
    current_layer: 'expanded',
    reasoning_backend: 'llm',
    completed_agents: 17,
    total_agents: 32,
    llm_invoked_count: 8,
    rules_count: 9,
    template_fallback_count: 1,
    failed_count: 0,
    society_metrics: {
      reach_rate: 0.42,
      misread_rate: 0.12,
      trust_recovery_rate: 0.3,
      purchase_intent_delta: 0.18,
    },
  })

  assert.deepStrictEqual(items.map(item => item.key), [
    'mode',
    'agents',
    'rounds',
    'llmBudget',
    'reach',
    'misread',
    'trustRecovery',
    'purchaseIntentDelta',
    'progressStatus',
    'agentProgress',
    'currentLayer',
    'currentBackend',
    'llmInvoked',
    'rulesCount',
    'fallbackCount',
    'failedCount',
  ])
  assert.equal(items.find(item => item.key === 'reach').value, '42%')
  assert.equal(items.find(item => item.key === 'purchaseIntentDelta').value, '+18pp')
  assert.equal(items.find(item => item.key === 'agentProgress').value, '17 / 32')
  assert.equal(items.find(item => item.key === 'currentBackend').value, 'llm')
})

test('formatSocietyDelta includes sign and percentage point suffix', () => {
  assert.equal(formatSocietyDelta(0.12), '+12pp')
  assert.equal(formatSocietyDelta(-0.04), '-4pp')
  assert.equal(formatSocietyDelta(0), '0pp')
})

test('SocietyRunSummary.vue renders all required labels', () => {
  const path = join(__dirname, '../src/components/consumer/SocietyRunSummary.vue')
  const content = readFileSync(path, 'utf-8')

  for (const label of [
    'Society Mode',
    'Agents',
    'Rounds',
    'LLM Budget',
    'Reach',
    'Misread',
    'Trust Recovery',
    'Purchase Intent',
    'Progress',
    'Agent Progress',
    'Current Layer',
    'Backend',
    'LLM Calls',
    'Rules',
    'Fallback',
    'Failed',
  ]) {
    assert.ok(content.includes(label), `missing ${label}`)
  }
})

test('Step3Simulation and Step4Report mount SocietyRunSummary', () => {
  const step3 = readFileSync(join(__dirname, '../src/components/Step3Simulation.vue'), 'utf-8')
  const step4 = readFileSync(join(__dirname, '../src/components/Step4Report.vue'), 'utf-8')

  assert.ok(step3.includes('SocietyRunSummary'), 'Step3Simulation must mount SocietyRunSummary')
  assert.ok(step4.includes('SocietyRunSummary'), 'Step4Report must mount SocietyRunSummary')
})

// ============== Diagnostic items ==============

test('buildSocietyRunDiagnosticItems includes phase6j_status when present', () => {
  const items = buildSocietyRunDiagnosticItems({ phase6j_status: 'incomplete' })
  assert.ok(items.find(i => i.key === 'phase6j_status'))
  assert.equal(items.find(i => i.key === 'phase6j_status').value, 'incomplete')
})

test('buildSocietyRunDiagnosticItems includes error_code when present', () => {
  const items = buildSocietyRunDiagnosticItems({ error_code: 'PHASE6J_MISSING' })
  assert.ok(items.find(i => i.key === 'error_code'))
  assert.equal(items.find(i => i.key === 'error_code').value, 'PHASE6J_MISSING')
})

test('buildSocietyRunDiagnosticItems includes blocking_stage when present', () => {
  const items = buildSocietyRunDiagnosticItems({ blocking_stage: 'phase6j' })
  assert.ok(items.find(i => i.key === 'blocking_stage'))
  assert.equal(items.find(i => i.key === 'blocking_stage').value, 'phase6j')
})

test('buildSocietyRunDiagnosticItems includes next_action when present', () => {
  const items = buildSocietyRunDiagnosticItems({ next_action: 'retry' })
  assert.ok(items.find(i => i.key === 'next_action'))
  assert.equal(items.find(i => i.key === 'next_action').value, 'retry')
})

test('buildSocietyRunDiagnosticItems returns empty array when no diagnostics', () => {
  const items = buildSocietyRunDiagnosticItems({})
  assert.equal(items.length, 0)
})

test('buildSocietyRunDiagnosticItems returns empty array when only irrelevant keys', () => {
  const items = buildSocietyRunDiagnosticItems({ society_mode: 'quick', status: 'idle' })
  assert.equal(items.length, 0)
})

test('societyRunSummary.js exports diagnostic labels', () => {
  const path = join(__dirname, '../src/utils/societyRunSummary.js')
  const content = readFileSync(path, 'utf-8')

  for (const label of ['Phase6J Status', 'Error Code', 'Blocking Stage', 'Next Action']) {
    assert.ok(content.includes(label), `missing ${label}`)
  }
})

test('SocietyRunSummary.vue references diagnosticItems and diagnostics in visible check', () => {
  const content = readFileSync(
    join(__dirname, '../src/components/consumer/SocietyRunSummary.vue'),
    'utf-8'
  )
  assert.ok(content.includes('diagnosticItems'), 'component should reference diagnosticItems')
  assert.ok(content.includes('diagnostics'), 'component should reference diagnostics in visible logic')
})
