import { test } from 'node:test'
import assert from 'node:assert/strict'

import {
  buildConsumerMetricCards,
  buildConsumerQuickPrompts,
  isConsumerProject,
  pickTopVocQuotes,
} from '../src/utils/consumerMode.js'

test('isConsumerProject supports backend and frontend project type shapes', () => {
  assert.equal(isConsumerProject({ project_type: 'consumer_test' }), true)
  assert.equal(isConsumerProject({ projectType: 'consumer_test' }), true)
  assert.equal(isConsumerProject({ project_type: 'default' }), false)
  assert.equal(isConsumerProject(null), false)
})

test('buildConsumerMetricCards formats propagation summary into compact cards', () => {
  const cards = buildConsumerMetricCards({
    summary: {
      initial_acceptance: { positive: 0.42 },
      post_propagation_acceptance: { positive: 0.67 },
      attitude_shift_rate: 0.31,
    },
    events_count: 18,
  })

  assert.deepEqual(cards, [
    { key: 'initial', label: 'Initial Acceptance', value: '42%' },
    { key: 'post', label: 'Post-Propagation Acceptance', value: '67%' },
    { key: 'shift', label: 'Attitude Shift', value: '31%' },
    { key: 'events', label: 'Captured Events', value: '18' },
  ])
})

test('pickTopVocQuotes returns one highlight per bucket in display order', () => {
  const quotes = pickTopVocQuotes({
    representative_voc_quotes: {
      resonance: [{ quote: 'This one feels easy to share.', engagement: 9, agent_id: 'a1' }],
      risk: [{ quote: 'I would question the low sugar promise.', engagement: 8, agent_id: 'a2' }],
      misread: [{ quote: 'Is this medicine or food?', engagement: 6, agent_id: 'a3' }],
    },
  })

  assert.deepEqual(quotes, [
    { bucket: 'resonance', label: 'Resonance', quote: 'This one feels easy to share.', engagement: 9, agentId: 'a1' },
    { bucket: 'risk', label: 'Risk', quote: 'I would question the low sugar promise.', engagement: 8, agentId: 'a2' },
    { bucket: 'misread', label: 'Misread', quote: 'Is this medicine or food?', engagement: 6, agentId: 'a3' },
  ])
})

test('buildConsumerQuickPrompts turns top findings into follow-up questions', () => {
  const prompts = buildConsumerQuickPrompts({
    top_resonance_points: ['portable breakfast'],
    top_risk_points: ['sweetener debate'],
    top_misreads: ['meal replacement confusion'],
  })

  assert.deepEqual(prompts, [
    'Why did "portable breakfast" become a top resonance point?',
    'Why did "sweetener debate" get amplified during propagation?',
    'How did "meal replacement confusion" turn into a misread?',
  ])
})
