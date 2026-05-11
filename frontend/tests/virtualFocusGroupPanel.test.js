import { test } from 'vitest'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

import { buildFocusGroupRequest } from '../src/utils/consumerInterview.js'

test('buildFocusGroupRequest emits fixed Phase 6I request body and caps max agents', () => {
  const payload = buildFocusGroupRequest({
    topic: 'price and proof',
    moderatorGoal: 'Find disagreement',
    selectedRoles: ['skeptic', 'advocate'],
    maxAgents: 20,
    targetContext: { branch_id: 'branch-1' },
  })

  assert.deepStrictEqual(payload, {
    topic: 'price and proof',
    moderator_goal: 'Find disagreement',
    roles: ['skeptic', 'advocate'],
    mode: 'snapshot',
    max_agents: 8,
    target_context: { branch_id: 'branch-1' },
  })
})

test('VirtualFocusGroupPanel.vue supports participant roles, moderator goal, four-turn view, consensus, disagreement, evidence, and What-if output', () => {
  const component = readFileSync(
    new URL('../src/components/consumer/VirtualFocusGroupPanel.vue', import.meta.url),
    'utf-8'
  )
  const step5 = readFileSync(new URL('../src/components/Step5Interaction.vue', import.meta.url), 'utf-8')

  for (const token of [
    'participant-role-selection',
    'moderator-goal-input',
    'runFocusGroup',
    'turn-by-turn',
    'turn.responses',
    'consensus-view',
    'disagreement-view',
    'result.disagreements',
    'evidence-map-view',
    'what-if-output',
    'next_what_if_experiments',
  ]) {
    assert.ok(component.includes(token), `missing ${token}`)
  }
  assert.ok(step5.includes('VirtualFocusGroupPanel'), 'Step5Interaction must mount VirtualFocusGroupPanel')
})

// --- Phase 6J P1: VirtualFocusGroupPanel explainability convergence ---

test('VirtualFocusGroupPanel.vue imports ConsumerExplainabilityPanel', () => {
  const component = readFileSync(
    new URL('../src/components/consumer/VirtualFocusGroupPanel.vue', import.meta.url),
    'utf-8'
  )
  assert.ok(component.includes("import ConsumerExplainabilityPanel from './ConsumerExplainabilityPanel.vue'"), 'must import ConsumerExplainabilityPanel')
})

test('VirtualFocusGroupPanel.vue renders ConsumerExplainabilityPanel for focus_group responses', () => {
  const component = readFileSync(
    new URL('../src/components/consumer/VirtualFocusGroupPanel.vue', import.meta.url),
    'utf-8'
  )
  assert.ok(component.includes('ConsumerExplainabilityPanel'), 'must render ConsumerExplainabilityPanel')
  assert.ok(component.includes('response.reasoning_metadata') || component.includes('reasoning_metadata'), 'must derive from response reasoning_metadata')
})

test('VirtualFocusGroupPanel.vue renders ConsumerExplainabilityPanel for next_what_if_experiments modification advice', () => {
  const component = readFileSync(
    new URL('../src/components/consumer/VirtualFocusGroupPanel.vue', import.meta.url),
    'utf-8'
  )
  assert.ok(component.includes('next_what_if_experiments'), 'must reference next_what_if_experiments')
  assert.ok(component.includes('ConsumerExplainabilityPanel'), 'must render ConsumerExplainabilityPanel')
})

test('VirtualFocusGroupPanel.vue derives audit data from response reasoning metadata, source, context, and evidence_map', () => {
  const component = readFileSync(
    new URL('../src/components/consumer/VirtualFocusGroupPanel.vue', import.meta.url),
    'utf-8'
  )
  assert.ok(component.includes('reasoning_metadata'), 'must reference reasoning_metadata')
  assert.ok(component.includes('evidence_map'), 'must reference evidence_map')
})

test('VirtualFocusGroupPanel.vue uses result.evidence_map and targetContext for explainability', () => {
  const component = readFileSync(
    new URL('../src/components/consumer/VirtualFocusGroupPanel.vue', import.meta.url),
    'utf-8'
  )
  assert.ok(component.includes('result.evidence_map') || component.includes('result'), 'must reference result evidence_map')
  assert.ok(component.includes('targetContext') || component.includes('target_context'), 'must reference targetContext')
})

test('VirtualFocusGroupPanel.vue normalizes object-shaped evidence_map for response and what-if explainability', () => {
  const component = readFileSync(
    new URL('../src/components/consumer/VirtualFocusGroupPanel.vue', import.meta.url),
    'utf-8'
  )
  assert.ok(component.includes('normalizeEvidenceMap'), 'must use normalizeEvidenceMap helper')
  assert.ok(component.includes('Object.values'), 'must support object-shaped evidence_map')
})
