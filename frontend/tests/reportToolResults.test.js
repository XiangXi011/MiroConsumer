import { describe, test } from 'vitest'
import assert from 'node:assert/strict'

import {
  parseInsightForge,
  parseInterview,
  parsePanorama,
  parseQuickSearch,
} from '../src/utils/reportToolResults.ts'

const lines = (...items) => items.join('\n')

describe('report tool result parsers', () => {
  test('parseQuickSearch extracts query, count, facts, edges, and nodes', () => {
    const result = parseQuickSearch(lines(
      '\u641c\u7d22\u67e5\u8be2: buyer hesitation',
      '\u627e\u5230 2 \u6761',
      '### \u76f8\u5173\u8fb9:',
      '- Buyer --[cares_about]--> Evidence',
      '### \u76f8\u5173\u8282\u70b9:',
      '- **Buyer** (Persona)',
      '- Plain signal',
      '### \u76f8\u5173\u4e8b\u5b9e:',
      '1. Proof detail matters.',
      '2. Price pressure is high.',
    ))

    assert.equal(result.query, 'buyer hesitation')
    assert.equal(result.count, 2)
    assert.deepEqual(result.facts, [
      'Proof detail matters.',
      'Price pressure is high.',
    ])
    assert.deepEqual(result.edges, [
      { source: 'Buyer', relation: 'cares_about', target: 'Evidence' },
    ])
    assert.deepEqual(result.nodes, [
      { name: 'Buyer', type: 'Persona' },
      { name: 'Plain signal', type: '' },
    ])
  })

  test('parsePanorama extracts graph stats, facts, and entities', () => {
    const result = parsePanorama(lines(
      '\u67e5\u8be2: campaign graph',
      '\u603b\u8282\u70b9\u6570: 12',
      '\u603b\u8fb9\u6570: 7',
      '\u5f53\u524d\u6709\u6548\u4e8b\u5b9e: 3',
      '\u5386\u53f2/\u8fc7\u671f\u4e8b\u5b9e: 1',
      '### \u3010\u5f53\u524d\u6709\u6548\u4e8b\u5b9e\u3011',
      '1. "Current fact"',
      '### \u3010\u5386\u53f2/\u8fc7\u671f\u4e8b\u5b9e\u3011',
      '1. "Historical fact"',
      '### \u3010\u6d89\u53ca\u5b9e\u4f53\u3011',
      '- **Campaign** (Event)',
    ))

    assert.deepEqual(result.stats, {
      nodes: 12,
      edges: 7,
      activeFacts: 3,
      historicalFacts: 1,
    })
    assert.deepEqual(result.activeFacts, ['Current fact'])
    assert.deepEqual(result.historicalFacts, ['Historical fact'])
    assert.deepEqual(result.entities, [{ name: 'Campaign', type: 'Event' }])
  })

  test('parseInsightForge extracts insight sections', () => {
    const result = parseInsightForge(lines(
      '\u5206\u6790\u95ee\u9898: why conversion stalls',
      '\u9884\u6d4b\u573a\u666f: launch week',
      '\u76f8\u5173\u9884\u6d4b\u4e8b\u5b9e: 4',
      '\u6d89\u53ca\u5b9e\u4f53: 2',
      '\u5173\u7cfb\u94fe: 1',
      '### \u5206\u6790\u7684\u5b50\u95ee\u9898',
      '1. Which claim is weak?',
      '2. Which channel drops users?',
      '### \u3010\u5173\u952e\u4e8b\u5b9e\u3011',
      '1. "Evidence gap"',
      '### \u3010\u6838\u5fc3\u5b9e\u4f53\u3011',
      '- **Product** (Offer)',
      '\u6458\u8981: "Main product summary"',
      '\u76f8\u5173\u4e8b\u5b9e: 3',
      '### \u3010\u5173\u7cfb\u94fe\u3011',
      '- Product --[needs]--> Evidence',
    ))

    assert.equal(result.query, 'why conversion stalls')
    assert.equal(result.simulationRequirement, 'launch week')
    assert.deepEqual(result.stats, { facts: 4, entities: 2, relationships: 1 })
    assert.deepEqual(result.subQueries, [
      'Which claim is weak?',
      'Which channel drops users?',
    ])
    assert.deepEqual(result.facts, ['Evidence gap'])
    assert.deepEqual(result.entities, [{
      name: 'Product',
      type: 'Offer',
      summary: 'Main product summary',
      relatedFactsCount: 3,
    }])
    assert.deepEqual(result.relations, [
      { source: 'Product', relation: 'needs', target: 'Evidence' },
    ])
  })

  test('parseInterview extracts interview metadata and platform answers', () => {
    const result = parseInterview(lines(
      '**\u91c7\u8bbf\u4e3b\u9898:** purchase decision',
      '**\u91c7\u8bbf\u4eba\u6570:** 1 / 3 \u4f4d\u6a21\u62dfAgent',
      '### \u91c7\u8bbf\u5bf9\u8c61\u9009\u62e9\u7406\u7531',
      '1. **AgentA(index=0)**: strongest category involvement.',
      '---',
      '### \u91c7\u8bbf\u5b9e\u5f55',
      '#### \u91c7\u8bbf #1: Primary buyer',
      '**AgentA** (Parent)',
      '_\u7b80\u4ecb: Shops weekly_',
      '**Q:**',
      '1. What matters?',
      '2. Why now?',
      '',
      '**A:**',
      '\u3010Twitter\u5e73\u53f0\u56de\u7b54\u3011',
      'Short answer.',
      '\u3010Reddit\u5e73\u53f0\u56de\u7b54\u3011',
      'Long answer.',
      '**\u5173\u952e\u5f15\u8a00:**',
      '> "Evidence beats slogans"',
      '### \u91c7\u8bbf\u6458\u8981\u4e0e\u6838\u5fc3\u89c2\u70b9',
      'Summary line.',
    ))

    assert.equal(result.topic, 'purchase decision')
    assert.equal(result.agentCount, '1 / 3')
    assert.equal(result.successCount, 1)
    assert.equal(result.totalCount, 3)
    assert.equal(result.summary, 'Summary line.')
    assert.equal(result.interviews.length, 1)
    assert.deepEqual(result.interviews[0], {
      num: 1,
      title: 'Primary buyer',
      name: 'AgentA',
      role: 'Parent',
      bio: 'Shops weekly',
      selectionReason: 'strongest category involvement.',
      questions: ['What matters?', 'Why now?'],
      twitterAnswer: 'Short answer.',
      redditAnswer: 'Long answer.',
      quotes: ['Evidence beats slogans'],
    })
  })
})
