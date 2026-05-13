import { test } from 'vitest'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

import { INTERVIEW_ROLE_PRESETS, buildInterviewRequest } from '../src/utils/consumerInterview.ts'

test('buildInterviewRequest emits fixed Phase 6I request body', () => {
  const payload = buildInterviewRequest({
    topic: 'proof repair',
    questionsText: 'What proof changes trust?\nWhat would you share?',
    selectedAgentIds: ['agent-1'],
    selectedRoles: ['skeptic'],
    mode: 'snapshot',
    maxAgents: 3,
    targetContext: { finding_id: 'finding-1' },
  })

  assert.deepStrictEqual(payload, {
    topic: 'proof repair',
    questions: ['What proof changes trust?', 'What would you share?'],
    agent_ids: ['agent-1'],
    roles: ['skeptic'],
    mode: 'snapshot',
    max_agents: 3,
    target_context: { finding_id: 'finding-1' },
  })
})

test('INTERVIEW_ROLE_PRESETS covers required role-based interview entries', () => {
  assert.deepStrictEqual(INTERVIEW_ROLE_PRESETS.map(item => item.role), [
    'advocate',
    'skeptic',
    'misreader',
    'price_sensitive',
    'amplifier',
    'trust_repairable',
  ])
})

test('RepresentativeConsumerInterview.vue supports role filter, agent selection, topic, questions, prompt buttons, result, and followups', () => {
  const component = readFileSync(
    new URL('../src/components/consumer/RepresentativeConsumerInterview.vue', import.meta.url),
    'utf-8'
  )
  const step5 = readFileSync(new URL('../src/components/Step5Interaction.vue', import.meta.url), 'utf-8')

  for (const token of [
    'role-filter',
    'agent-selection',
    'topic-input',
    'question-list',
    'fixed-prompt',
    'interview-result',
    'result.answers',
    'follow-up-question',
    'extractConsumerItems',
    'runConsumerInterview',
    'listRepresentativeAgents',
  ]) {
    assert.ok(component.includes(token), `missing ${token}`)
  }
  assert.ok(step5.includes('RepresentativeConsumerInterview'), 'Step5Interaction must mount RepresentativeConsumerInterview')
})
