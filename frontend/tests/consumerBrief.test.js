import { test } from 'node:test'
import assert from 'node:assert/strict'

import {
  buildConsumerBrief,
  isConsumerBriefComplete,
  resolveSimulationRequirement,
} from '../src/utils/consumerBrief.js'

test('buildConsumerBrief normalizes multiline and delimited fields', () => {
  const brief = buildConsumerBrief({
    consumerConcept: 'High-protein yogurt for busy mornings\nPortable breakfast cup',
    consumerCopy: '14g protein\nLow sugar',
    consumerClaims: '14g protein, low sugar; probiotic support',
    consumerAudience: 'working moms，fitness beginners',
    consumerScene: 'weekday breakfast\ncommute snack',
    consumerResearchGoal: 'Identify resonance and misread risks  ',
  })

  assert.deepEqual(brief, {
    task_type: 'concept_test',
    product_concept_assets: [
      'High-protein yogurt for busy mornings',
      'Portable breakfast cup',
    ],
    copy_material: ['14g protein', 'Low sugar'],
    claims: ['14g protein', 'low sugar', 'probiotic support'],
    target_audience: ['working moms', 'fitness beginners'],
    usage_scene: ['weekday breakfast', 'commute snack'],
    research_goal: 'Identify resonance and misread risks',
  })
})

test('isConsumerBriefComplete only passes when required consumer fields are present', () => {
  assert.equal(
    isConsumerBriefComplete({
      consumerConcept: 'Concept',
      consumerCopy: 'Copy',
      consumerAudience: 'Audience',
      consumerResearchGoal: 'Goal',
    }),
    true
  )

  assert.equal(
    isConsumerBriefComplete({
      consumerConcept: 'Concept',
      consumerCopy: '',
      consumerAudience: 'Audience',
      consumerResearchGoal: 'Goal',
    }),
    false
  )
})

test('resolveSimulationRequirement only applies consumer fallback in consumer mode', () => {
  assert.equal(
    resolveSimulationRequirement('consumer_test', '', 'Run consumer propagation test'),
    'Run consumer propagation test'
  )
  assert.equal(
    resolveSimulationRequirement('consumer_test', '  Use custom prompt  ', 'fallback'),
    'Use custom prompt'
  )
  assert.equal(resolveSimulationRequirement('default', '  Legacy prompt  ', 'fallback'), 'Legacy prompt')
  assert.equal(resolveSimulationRequirement('default', '', 'fallback'), '')
})
