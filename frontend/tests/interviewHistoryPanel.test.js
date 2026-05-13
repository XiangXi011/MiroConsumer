import { test } from 'vitest'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

import { normalizeInterviewHistoryItems } from '../src/utils/consumerInterview.ts'

test('normalizeInterviewHistoryItems formats interview and focus group history', () => {
  const items = normalizeInterviewHistoryItems({
    interviews: [{ interview_id: 'interview-1', topic: 'proof', summary: 'summary' }],
    focusGroups: [{ focus_group_id: 'focus-1', topic: 'price', consensus: ['agree'] }],
  })

  assert.deepStrictEqual(items.map(item => item.id), ['interview-1', 'focus-1'])
  assert.deepStrictEqual(items.map(item => item.type), ['interview', 'focus_group'])
})

test('InterviewHistoryPanel.vue shows interview history, focus group history, topic, roles, created time, summary, and reopen action', () => {
  const component = readFileSync(
    new URL('../src/components/consumer/InterviewHistoryPanel.vue', import.meta.url),
    'utf-8'
  )
  const step5 = readFileSync(new URL('../src/components/Step5Interaction.vue', import.meta.url), 'utf-8')

  for (const token of [
    'listInterviewHistory',
    'listFocusGroupHistory',
    'extractConsumerItems',
    'interview-history',
    'focus-group-history',
    'topic',
    'roles',
    'createdAt',
    'summary',
    'Reopen',
  ]) {
    assert.ok(component.includes(token), `missing ${token}`)
  }
  assert.ok(step5.includes('InterviewHistoryPanel'), 'Step5Interaction must mount InterviewHistoryPanel')
})
