import { test } from 'vitest'
import assert from 'node:assert/strict'

import {
  buildBriefValidationItems,
  getBusinessFlowSteps,
  getBusinessStatusCopy,
  isBriefFieldMissing,
} from '../src/utils/businessUx.ts'

test('business flow exposes five brand-friendly stages', () => {
  const steps = getBusinessFlowSteps()

  assert.equal(steps.length, 5)
  assert.deepEqual(steps.map(step => step.title), [
    '准备测试素材',
    '生成消费者画像',
    '运行传播测试',
    '生成洞察报告',
    '追问与验证',
  ])
})

test('business status copy maps processing, completed, and error states', () => {
  assert.equal(getBusinessStatusCopy('brief', 'processing').label, '正在准备测试素材')
  assert.equal(getBusinessStatusCopy('audience', 'completed').label, '消费者画像已准备好')
  assert.equal(getBusinessStatusCopy('run', 'error').label, '传播测试遇到问题')
  assert.equal(getBusinessStatusCopy('report', 'ready').status, 'completed')
})

test('brief validation lists concept-test missing fields by business groups', () => {
  const items = buildBriefValidationItems({
    consumerTaskType: 'concept_test',
    consumerConcept: '',
    consumerCopy: '',
    consumerAudience: '',
    consumerResearchGoal: '',
  })

  assert.deepEqual(items.map(item => item.field), [
    'consumerAudience',
    'consumerResearchGoal',
    'consumerConcept',
    'consumerCopy',
  ])
  assert.equal(isBriefFieldMissing({ consumerTaskType: 'concept_test' }, 'consumerConcept'), true)
})

test('brief validation supports packaging, ab, and price tests', () => {
  assert.deepEqual(
    buildBriefValidationItems({
      consumerTaskType: 'packaging_test',
      consumerAudience: 'eco shoppers',
      consumerResearchGoal: 'trust',
      consumerPackagingAssets: '',
    }).map(item => [item.field, item.hint]),
    [['consumerPackagingAssets', '上传包装 PDF 或图片素材。']],
  )

  assert.deepEqual(
    buildBriefValidationItems({
      consumerTaskType: 'ab_test',
      consumerAudience: 'moms',
      consumerResearchGoal: 'compare',
      consumerTestVariants: 'Only A',
    }).map(item => item.field),
    ['consumerTestVariants'],
  )

  assert.deepEqual(
    buildBriefValidationItems({
      consumerTaskType: 'price_test',
      consumerAudience: 'students',
      consumerResearchGoal: 'price',
      consumerPricePoints: '',
    }).map(item => item.field),
    ['consumerPricePoints'],
  )
})
