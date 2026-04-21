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
    research_mode: 'manual_only',
    enable_lane_b: false,
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

test('buildConsumerBrief preserves research mode when provided', () => {
  const brief = buildConsumerBrief({
    consumerConcept: 'Protein yogurt',
    consumerCopy: '14g protein',
    consumerAudience: 'fitness beginners',
    consumerResearchGoal: 'Find resonance',
    consumerResearchMode: 'auto_enrich',
  })

  assert.equal(brief.research_mode, 'auto_enrich')
})

test('buildConsumerBrief defaults research mode to manual_only when omitted', () => {
  const brief = buildConsumerBrief({
    consumerConcept: 'Protein yogurt',
    consumerCopy: '14g protein',
    consumerAudience: 'fitness beginners',
    consumerResearchGoal: 'Find resonance',
  })

  assert.equal(brief.research_mode, 'manual_only')
})

test('buildConsumerBrief defaults enable_lane_b to false when omitted', () => {
  const brief = buildConsumerBrief({
    consumerConcept: 'Protein yogurt',
    consumerCopy: '14g protein',
    consumerAudience: 'fitness beginners',
    consumerResearchGoal: 'Find resonance',
  })

  assert.equal(brief.enable_lane_b, false)
})

test('buildConsumerBrief carries enable_lane_b when true', () => {
  const brief = buildConsumerBrief({
    consumerConcept: 'Protein yogurt',
    consumerCopy: '14g protein',
    consumerAudience: 'fitness beginners',
    consumerResearchGoal: 'Find resonance',
    consumerEnableLaneB: true,
  })

  assert.equal(brief.enable_lane_b, true)
})

test('buildConsumerBrief carries enable_lane_b when false', () => {
  const brief = buildConsumerBrief({
    consumerConcept: 'Protein yogurt',
    consumerCopy: '14g protein',
    consumerAudience: 'fitness beginners',
    consumerResearchGoal: 'Find resonance',
    consumerEnableLaneB: false,
  })

  assert.equal(brief.enable_lane_b, false)
})
