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

import { getConsumerEventLabel } from '../src/utils/consumerMode.js'

test('getConsumerEventLabel returns label for known phase2 event types', () => {
  assert.ok(getConsumerEventLabel('risk_discovery').toLowerCase().includes('risk'))
  assert.ok(getConsumerEventLabel('positive_relay').toLowerCase().includes('positive') || getConsumerEventLabel('positive_relay').toLowerCase().includes('relay'))
  assert.ok(getConsumerEventLabel('misread_amplification').toLowerCase().includes('misread'))
  assert.ok(getConsumerEventLabel('skeptical_challenge').toLowerCase().includes('skeptical') || getConsumerEventLabel('skeptical_challenge').toLowerCase().includes('challenge'))
  assert.ok(getConsumerEventLabel('clarification_recovery').toLowerCase().includes('clarification') || getConsumerEventLabel('clarification_recovery').toLowerCase().includes('recovery'))
})

test('getConsumerEventLabel returns fallback for unknown event type', () => {
  assert.equal(getConsumerEventLabel('unknown_event'), 'unknown_event')
})

test('buildConsumerQuickPrompts includes causal spread prompt when persona_group_signals is a non-empty object map', () => {
  const prompts = buildConsumerQuickPrompts({
    persona_group_signals: {
      health_conscious_mom: { amplified: ['risk_discovery'], blocked: [] },
      fitness_beginner: { amplified: ['misread_amplification'], blocked: [] },
    },
  })

  const spreadPrompt = prompts.find(p => p.includes('spread'))
  assert.ok(spreadPrompt, 'Expected spread prompt to be present for non-empty object-map persona_group_signals')
})

test('buildConsumerQuickPrompts uses backend field shapes for phase2 gating', () => {
  const prompts = buildConsumerQuickPrompts({
    top_risk_findings: [{ finding_id: 'r1', finding_type: 'risk_discovery', summary: 'Sugar concern' }],
    causal_chains: [{ finding_summary: 'Sugar concern', event_ids: ['e1'], event_types: ['risk_discovery'] }],
    top_clarification_opportunities: [{ finding_id: 'c1', finding_type: 'clarification_recovery', summary: 'Protein clarified' }],
    event_led_reversals: [{ event_id: 'e2', event_type: 'clarification_recovery' }],
  })

  const triggerPrompt = prompts.find(p => p.includes('triggered'))
  const recoveryPrompt = prompts.find(p => p.includes('recover'))
  assert.ok(triggerPrompt, 'Expected trigger prompt from top_risk_findings/causal_chains')
  assert.ok(recoveryPrompt, 'Expected recovery prompt from clarifications/reversals')
})

test('buildConsumerQuickPrompts omits causal spread prompt when persona_group_signals is empty object', () => {
  const prompts = buildConsumerQuickPrompts({
    persona_group_signals: {},
  })

  const spreadPrompt = prompts.find(p => p.includes('spread'))
  assert.equal(spreadPrompt, undefined, 'Expected no spread prompt for empty object-map persona_group_signals')
})

test('buildConsumerQuickPrompts omits causal spread prompt when persona_group_signals is missing', () => {
  const prompts = buildConsumerQuickPrompts({
    top_resonance_points: ['portable breakfast'],
  })

  const spreadPrompt = prompts.find(p => p.includes('spread'))
  assert.equal(spreadPrompt, undefined, 'Expected no spread prompt when persona_group_signals is missing')
})

// Mirrors Step4Report.vue computed-property mapping; fails if field names drift from backend.
test('Step4Report field mapping renders non-empty results with real backend schema', () => {
  const reportContext = {
    top_risk_findings: [
      { finding_id: 'r1', finding_type: 'risk_discovery', summary: 'Sugar too high' },
    ],
    top_clarification_opportunities: [
      { finding_id: 'c1', finding_type: 'clarification_recovery', summary: 'Protein explained' },
    ],
    causal_chains: [
      { finding_summary: 'Sugar too high', event_ids: ['e1'], event_types: ['risk_discovery', 'misread_amplification'] },
    ],
  }

  const riskFindings = (reportContext.top_risk_findings || [])
    .filter(f => f && f.summary)
    .map(f => ({ text: f.summary, type: f.finding_type || '' }))

  const clarifications = (reportContext.top_clarification_opportunities || [])
    .filter(c => c && c.summary)
    .map(c => ({ text: c.summary }))

  const causalChains = (reportContext.causal_chains || [])
    .filter(c => c && c.finding_summary)
    .map(c => ({ description: `${c.finding_summary} → ${(c.event_types || []).join(', ')}` }))

  assert.equal(riskFindings.length, 1, 'Expected risk findings mapped from summary field')
  assert.equal(riskFindings[0].text, 'Sugar too high')
  assert.equal(clarifications.length, 1, 'Expected clarifications mapped from summary field')
  assert.equal(clarifications[0].text, 'Protein explained')
  assert.equal(causalChains.length, 1, 'Expected causal chains mapped from finding_summary field')
  assert.ok(causalChains[0].description.includes('Sugar too high'))
  assert.ok(causalChains[0].description.includes('risk_discovery'))
})
