import { describe, test } from 'vitest'
import assert from 'node:assert/strict'

import {
  getToolColor,
  getToolDisplayName,
  getToolIcon,
  resolveToolMetadata,
} from '../src/utils/reportToolMetadata.ts'

describe('report tool metadata', () => {
  test('resolves configured tool display metadata', () => {
    assert.deepEqual(resolveToolMetadata('insight_forge'), {
      name: 'Deep Insight',
      color: 'purple',
      icon: 'lightbulb',
    })
    assert.deepEqual(resolveToolMetadata('panorama_search'), {
      name: 'Panorama Search',
      color: 'blue',
      icon: 'globe',
    })
    assert.deepEqual(resolveToolMetadata('interview_agents'), {
      name: 'Agent Interview',
      color: 'green',
      icon: 'users',
    })
    assert.deepEqual(resolveToolMetadata('quick_search'), {
      name: 'Quick Search',
      color: 'orange',
      icon: 'zap',
    })
  })

  test('falls back for unknown tool names', () => {
    assert.deepEqual(resolveToolMetadata('custom_tool'), {
      name: 'custom_tool',
      color: 'gray',
      icon: 'tool',
    })
    assert.equal(getToolDisplayName('custom_tool'), 'custom_tool')
    assert.equal(getToolColor('custom_tool'), 'gray')
    assert.equal(getToolIcon('custom_tool'), 'tool')
  })

  test('exposes small accessors for component templates', () => {
    assert.equal(getToolDisplayName('get_graph_statistics'), 'Graph Stats')
    assert.equal(getToolColor('get_entities_by_type'), 'pink')
    assert.equal(getToolIcon('get_entities_by_type'), 'database')
  })
})
