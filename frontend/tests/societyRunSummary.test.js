import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'fs'
import { fileURLToPath } from 'url'
import { dirname, join } from 'path'

import {
  buildSocietyRunSummaryItems,
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
  ])
  assert.equal(items.find(item => item.key === 'reach').value, '42%')
  assert.equal(items.find(item => item.key === 'purchaseIntentDelta').value, '+18pp')
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
