import { test } from 'vitest'
import assert from 'node:assert/strict'
import { readFileSync } from 'fs'
import { fileURLToPath } from 'url'
import { dirname, join } from 'path'

import { buildPropagationTimelineItems } from '../src/utils/channelPropagation.ts'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

test('buildPropagationTimelineItems truncates fixed timeline to completed rounds', () => {
  const items = buildPropagationTimelineItems({
    society_rounds_completed: 6,
    channel_metrics: {
      channels: {
        douyin: { misread_risk: 0.7 },
        xiaohongshu: { resonance: 0.8 },
      },
    },
  })

  assert.deepStrictEqual(items.map(item => item.phase), [
    '初见反应',
    '卖点扩散',
    '疑虑出现',
  ])
  assert.equal(items[2].roundRange, 'R4-R6')
})

test('PropagationTimeline.vue is mounted by Step4Report', () => {
  const component = readFileSync(join(__dirname, '../src/components/consumer/PropagationTimeline.vue'), 'utf-8')
  const util = readFileSync(join(__dirname, '../src/utils/channelPropagation.ts'), 'utf-8')
  const step4 = readFileSync(join(__dirname, '../src/components/Step4Report.vue'), 'utf-8')

  for (const label of ['初见反应', '卖点扩散', '疑虑出现', '误读扩散', '证据修复']) {
    assert.ok(util.includes(label), `missing ${label}`)
  }
  assert.ok(component.includes('Response Timeline'))
  assert.ok(step4.includes('PropagationTimeline'), 'Step4Report must mount PropagationTimeline')
})
