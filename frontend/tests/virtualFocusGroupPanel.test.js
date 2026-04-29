import { test } from 'node:test'
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
