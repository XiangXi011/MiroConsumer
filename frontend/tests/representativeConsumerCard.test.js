import { test } from 'vitest'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

import { buildRepresentativeCardView, extractConsumerItems } from '../src/utils/consumerInterview.ts'

test('buildRepresentativeCardView formats complete representative card fields', () => {
  const view = buildRepresentativeCardView({
    agent_id: 'agent-1',
    display_name: 'Consumer agent-1',
    role: 'skeptic',
    segment: 'ingredient readers',
    channel_id: 'zhihu_qa',
    attitude_start: 'neutral',
    attitude_latest: 'skeptical',
    purchase_intent_start: 0.4,
    purchase_intent_latest: 0.2,
    key_quote: 'Show me proof.',
    influence_score: 0.45,
    evidence_ids: ['finding-1'],
    event_ids: ['event-1'],
  })

  assert.equal(view.roleLabel, 'Skeptic')
  assert.equal(view.channelLabel, '知乎/问答社区')
  assert.equal(view.purchaseIntentDeltaText, '-20pp')
  assert.equal(view.influenceText, '45%')
  assert.equal(view.keyQuote, 'Show me proof.')
})

test('RepresentativeConsumerCard.vue displays role, segment, channel, quote, attitude, purchase intent, influence, and ask button', () => {
  const component = readFileSync(
    new URL('../src/components/consumer/RepresentativeConsumerCard.vue', import.meta.url),
    'utf-8'
  )

  for (const token of [
    'roleLabel',
    'segment',
    'channelLabel',
    'keyQuote',
    'attitudeText',
    'purchaseIntentDeltaText',
    'influenceText',
    'Ask Consumer',
  ]) {
    assert.ok(component.includes(token), `missing ${token}`)
  }
})

test('consumer interview channel labels use Phase 6H channel ontology only', () => {
  const util = readFileSync(new URL('../src/utils/consumerInterview.ts', import.meta.url), 'utf-8')
  for (const forbidden of ['twitter', 'reddit', 'weibo', 'bilibili']) {
    assert.ok(!util.includes(forbidden), `consumerInterview.js must not include legacy channel ${forbidden}`)
  }
})

test('extractConsumerItems unwraps backend { success, data: { items } } responses', () => {
  assert.deepStrictEqual(
    extractConsumerItems({ success: true, data: { items: [{ id: 'a1' }] } }),
    [{ id: 'a1' }]
  )
  assert.deepStrictEqual(extractConsumerItems({ success: true, data: [{ id: 'a2' }] }), [{ id: 'a2' }])
  assert.deepStrictEqual(extractConsumerItems(null), [])
})
