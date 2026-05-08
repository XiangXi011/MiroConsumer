import { test } from 'vitest'
import assert from 'node:assert/strict'
import { readFileSync } from 'fs'
import { fileURLToPath } from 'url'
import { dirname, join } from 'path'

import { buildChannelFitItems } from '../src/utils/channelPropagation.js'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

test('buildChannelFitItems formats best channel and fixed channel risks', () => {
  const items = buildChannelFitItems({
    channel_metrics: {
      best_launch_channel: 'xiaohongshu',
      highest_misread_channel: 'douyin',
      highest_evidence_demand_channel: 'zhihu_qa',
      highest_price_resistance_channel: 'ecommerce_review',
      channels: {
        xiaohongshu: { fit_score: 0.78, misread_risk: 0.18, evidence_demand: 0.34, price_resistance: 0.2 },
        douyin: { fit_score: 0.54, misread_risk: 0.62, evidence_demand: 0.2, price_resistance: 0.1 },
      },
    },
  })

  assert.equal(items.summary.bestLaunchChannel, '小红书')
  assert.equal(items.summary.highestMisreadChannel, '抖音')
  assert.equal(items.channels[0].fitScoreText, '78%')
  assert.ok(items.channels[1].primaryRisk.includes('Misread'))
})

test('ChannelFitPanel.vue is mounted by Step3Simulation and Step4Report', () => {
  const component = readFileSync(join(__dirname, '../src/components/consumer/ChannelFitPanel.vue'), 'utf-8')
  const step3 = readFileSync(join(__dirname, '../src/components/Step3Simulation.vue'), 'utf-8')
  const step4 = readFileSync(join(__dirname, '../src/components/Step4Report.vue'), 'utf-8')

  assert.ok(component.includes('Best Launch Channel'))
  assert.ok(component.includes('Highest Misread Channel'))
  assert.ok(step3.includes('ChannelFitPanel'))
  assert.ok(step4.includes('ChannelFitPanel'))
})
