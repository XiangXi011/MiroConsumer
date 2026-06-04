import { test } from 'vitest'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

import { normalizeInterviewHistoryItems } from '../src/utils/consumerInterview.ts'
import {
  buildSurveyInterviewRequests,
  extractAgentChatResponse,
  normalizeSurveyResults,
} from '../src/utils/step5Survey.ts'

test('normalizeInterviewHistoryItems formats interview and focus group history', () => {
  const items = normalizeInterviewHistoryItems({
    interviews: [{ interview_id: 'interview-1', topic: 'proof', summary: 'summary' }],
    focusGroups: [{ focus_group_id: 'focus-1', topic: 'price', consensus: ['agree'] }],
  })

  assert.deepStrictEqual(items.map(item => item.id), ['interview-1', 'focus-1'])
  assert.deepStrictEqual(items.map(item => item.type), ['interview', 'focus_group'])
})

test('buildSurveyInterviewRequests maps selected agent indexes to prompt payloads', () => {
  const interviews = buildSurveyInterviewRequests(new Set([2, 0]), ' Why did trust drop? ')

  assert.deepStrictEqual(interviews, [
    { agent_id: 2, prompt: 'Why did trust drop?' },
    { agent_id: 0, prompt: 'Why did trust drop?' },
  ])
})

test('normalizeSurveyResults prefers reddit object result before twitter result', () => {
  const interviews = [
    { agent_id: 0, prompt: 'Why did trust drop?' },
    { agent_id: 1, prompt: 'Why did trust drop?' },
  ]
  const profiles = [
    { username: 'Ava', profession: 'Designer' },
    { username: 'Bo', profession: 'Parent' },
  ]

  const results = normalizeSurveyResults({
    interviews,
    profiles,
    resultData: {
      results: {
        twitter_0: { response: 'Twitter answer' },
        reddit_0: { answer: 'Reddit answer' },
        twitter_1: { response: 'Second answer' },
      },
    },
    question: 'Why did trust drop?',
    noResponseText: 'No response',
  })

  assert.deepStrictEqual(results, [
    {
      agent_id: 0,
      agent_name: 'Ava',
      profession: 'Designer',
      question: 'Why did trust drop?',
      answer: 'Reddit answer',
    },
    {
      agent_id: 1,
      agent_name: 'Bo',
      profession: 'Parent',
      question: 'Why did trust drop?',
      answer: 'Second answer',
    },
  ])
})

test('normalizeSurveyResults supports array-shaped backend results and missing replies', () => {
  const results = normalizeSurveyResults({
    interviews: [
      { agent_id: 3, prompt: 'Which signal matters?' },
      { agent_id: 4, prompt: 'Which signal matters?' },
    ],
    profiles: [],
    resultData: [
      { agent_id: 3, answer: 'Array answer' },
    ],
    question: 'Which signal matters?',
    noResponseText: 'No response',
  })

  assert.deepStrictEqual(results, [
    {
      agent_id: 3,
      agent_name: 'Agent 3',
      profession: undefined,
      question: 'Which signal matters?',
      answer: 'Array answer',
    },
    {
      agent_id: 4,
      agent_name: 'Agent 4',
      profession: undefined,
      question: 'Which signal matters?',
      answer: 'No response',
    },
  ])
})

test('extractAgentChatResponse prefers reddit and twitter result for the selected agent', () => {
  assert.equal(
    extractAgentChatResponse({
      resultData: {
        results: {
          twitter_2: { response: 'Twitter reply' },
          reddit_2: { answer: 'Reddit reply' },
          reddit_3: { response: 'Other reply' },
        },
      },
      agentId: 2,
    }),
    'Reddit reply',
  )
})

test('extractAgentChatResponse falls back to first object result when selected agent is absent', () => {
  assert.equal(
    extractAgentChatResponse({
      resultData: {
        results: {
          reddit_7: { response: 'Fallback reply' },
        },
      },
      agentId: 2,
    }),
    'Fallback reply',
  )
})

test('extractAgentChatResponse supports array-shaped backend results', () => {
  assert.equal(
    extractAgentChatResponse({
      resultData: [
        { agent_id: 2, answer: 'Array reply' },
      ],
      agentId: 2,
    }),
    'Array reply',
  )
})

test('extractAgentChatResponse returns empty string when no response is available', () => {
  assert.equal(extractAgentChatResponse({ resultData: null, agentId: 2 }), '')
  assert.equal(extractAgentChatResponse({ resultData: { results: {} }, agentId: 2 }), '')
})

test('InterviewHistoryPanel.vue shows interview history, focus group history, topic, roles, created time, summary, and reopen action', () => {
  const component = readFileSync(
    new URL('../src/components/consumer/InterviewHistoryPanel.vue', import.meta.url),
    'utf-8'
  )
  const step5 = readFileSync(new URL('../src/components/Step5Interaction.vue', import.meta.url), 'utf-8')
  const workspaceShell = readFileSync(new URL('../src/components/report/InteractionWorkspaceShell.vue', import.meta.url), 'utf-8')

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
  assert.ok(step5.includes('InteractionWorkspaceShell'), 'Step5Interaction must mount InteractionWorkspaceShell')
  assert.ok(workspaceShell.includes('InterviewHistoryPanel'), 'InteractionWorkspaceShell must mount InterviewHistoryPanel')
})
