import { test } from 'vitest'
import assert from 'node:assert/strict'

import {
  buildPackagingAssetSummary,
  buildConsumerBrief,
  isConsumerBriefComplete,
  resolveSimulationRequirement,
} from '../src/utils/consumerBrief.ts'

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

// ========== Phase 4B: New task types ==========

test('buildConsumerBrief emits packaging_test task type and packaging_assets', () => {
  const brief = buildConsumerBrief({
    consumerTaskType: 'packaging_test',
    consumerPackagingAssets: 'Eco-friendly glass jar\nRecyclable label',
    consumerCopy: 'Sustainable packaging\nZero waste',
    consumerAudience: 'eco-conscious millennials',
    consumerResearchGoal: 'Test packaging trust signals',
  })

  assert.equal(brief.task_type, 'packaging_test')
  assert.deepEqual(brief.packaging_assets, ['Eco-friendly glass jar', 'Recyclable label'])
  assert.deepEqual(brief.copy_material, ['Sustainable packaging', 'Zero waste'])
  assert.deepEqual(brief.target_audience, ['eco-conscious millennials'])
})

test('buildPackagingAssetSummary turns uploaded packaging files into brief assets', () => {
  const summary = buildPackagingAssetSummary([
    { name: '舒客酵素亮白牙膏-包装正面.png' },
    { name: '舒客酵素亮白牙膏-外盒.pdf' },
  ])

  assert.equal(summary, '包装素材文件：舒客酵素亮白牙膏-包装正面.png、舒客酵素亮白牙膏-外盒.pdf')

  const brief = buildConsumerBrief({
    consumerTaskType: 'packaging_test',
    consumerPackagingAssets: summary,
    consumerAudience: '咖啡茶饮高频用户',
    consumerResearchGoal: '判断包装是否传达温和去黄',
  })

  assert.deepEqual(brief.packaging_assets, [
    '包装素材文件：舒客酵素亮白牙膏-包装正面.png、舒客酵素亮白牙膏-外盒.pdf',
  ])
})

test('buildConsumerBrief emits ab_test task type and test_variants', () => {
  const brief = buildConsumerBrief({
    consumerTaskType: 'ab_test',
    consumerTestVariants: 'Variant A: Bold claim\nVariant B: Soft claim',
    consumerAudience: 'working moms',
    consumerResearchGoal: 'Compare variant resonance',
  })

  assert.equal(brief.task_type, 'ab_test')
  assert.equal(brief.test_variants.length, 2)
  assert.equal(brief.test_variants[0].variant_id, 'v1')
  assert.equal(brief.test_variants[0].label, 'Variant A: Bold claim')
  assert.equal(brief.test_variants[1].variant_id, 'v2')
  assert.equal(brief.test_variants[1].label, 'Variant B: Soft claim')
})

test('buildConsumerBrief emits ab_test variants from array input', () => {
  const brief = buildConsumerBrief({
    consumerTaskType: 'ab_test',
    consumerTestVariants: [
      { variant_id: 'control', label: 'Control', concept_assets: ['Original'] },
      { variant_id: 'treatment', label: 'Treatment', concept_assets: ['New'] },
    ],
    consumerAudience: 'working moms',
    consumerResearchGoal: 'Compare variant resonance',
  })

  assert.equal(brief.test_variants.length, 2)
  assert.equal(brief.test_variants[0].variant_id, 'control')
  assert.deepEqual(brief.test_variants[0].concept_assets, ['Original'])
})

test('buildConsumerBrief emits price_test task type and price fields', () => {
  const brief = buildConsumerBrief({
    consumerTaskType: 'price_test',
    consumerPricePoints: '$9.99, $14.99\n$19.99',
    consumerPriceContext: 'subscription monthly',
    consumerConcept: 'Premium protein yogurt',
    consumerCopy: '14g protein',
    consumerAudience: 'fitness enthusiasts',
    consumerResearchGoal: 'Find optimal price point',
  })

  assert.equal(brief.task_type, 'price_test')
  assert.deepEqual(brief.price_points, ['$9.99', '$14.99', '$19.99'])
  assert.equal(brief.price_context, 'subscription monthly')
  assert.deepEqual(brief.product_concept_assets, ['Premium protein yogurt'])
})

test('isConsumerBriefComplete validates packaging_test requires packaging_assets', () => {
  assert.equal(
    isConsumerBriefComplete({
      consumerTaskType: 'packaging_test',
      consumerPackagingAssets: 'Glass jar',
      consumerAudience: 'audience',
      consumerResearchGoal: 'goal',
    }),
    true
  )

  assert.equal(
    isConsumerBriefComplete({
      consumerTaskType: 'packaging_test',
      consumerPackagingAssets: '',
      consumerAudience: 'audience',
      consumerResearchGoal: 'goal',
    }),
    false
  )
})

test('isConsumerBriefComplete validates ab_test requires at least 2 variants', () => {
  assert.equal(
    isConsumerBriefComplete({
      consumerTaskType: 'ab_test',
      consumerTestVariants: 'Variant A\nVariant B',
      consumerAudience: 'audience',
      consumerResearchGoal: 'goal',
    }),
    true
  )

  assert.equal(
    isConsumerBriefComplete({
      consumerTaskType: 'ab_test',
      consumerTestVariants: 'Only one',
      consumerAudience: 'audience',
      consumerResearchGoal: 'goal',
    }),
    false
  )
})

test('isConsumerBriefComplete validates price_test requires price_points', () => {
  assert.equal(
    isConsumerBriefComplete({
      consumerTaskType: 'price_test',
      consumerPricePoints: '$9.99',
      consumerAudience: 'audience',
      consumerResearchGoal: 'goal',
    }),
    true
  )

  assert.equal(
    isConsumerBriefComplete({
      consumerTaskType: 'price_test',
      consumerPricePoints: '',
      consumerAudience: 'audience',
      consumerResearchGoal: 'goal',
    }),
    false
  )
})

test('buildConsumerBrief backward compatible: concept_test when task type omitted', () => {
  const brief = buildConsumerBrief({
    consumerConcept: 'Concept',
    consumerCopy: 'Copy',
    consumerAudience: 'Audience',
    consumerResearchGoal: 'Goal',
  })

  assert.equal(brief.task_type, 'concept_test')
  assert.deepEqual(brief.product_concept_assets, ['Concept'])
  assert.deepEqual(brief.copy_material, ['Copy'])
})
