import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'fs'
import { fileURLToPath } from 'url'
import { dirname, join } from 'path'

import {
  buildChannelHeatmapRows,
  formatChannelPercent,
} from '../src/utils/channelPropagation.js'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

test('buildChannelHeatmapRows creates channel matrices for claim, segment, risk, and purchase intent', () => {
  const rows = buildChannelHeatmapRows({
    channels: {
      xiaohongshu: {
        fit_score: 0.78,
        resonance: 0.72,
        misread_risk: 0.18,
        evidence_demand: 0.34,
        price_resistance: 0.22,
        purchase_intent_delta: 0.41,
      },
      ecommerce_review: {
        fit_score: 0.52,
        resonance: 0.44,
        misread_risk: 0.2,
        evidence_demand: 0.31,
        price_resistance: 0.63,
        purchase_intent_delta: 0.14,
      },
    },
  })

  assert.deepStrictEqual(rows.map(row => row.key), ['claim', 'segment', 'risk', 'purchaseIntent'])
  assert.equal(rows[0].cells[0].channelId, 'xiaohongshu')
  assert.equal(rows[0].cells[0].valueText, '72%')
  assert.equal(rows[3].cells[1].valueText, '14%')
})

test('formatChannelPercent clamps invalid values to zero percent', () => {
  assert.equal(formatChannelPercent(0.345), '35%')
  assert.equal(formatChannelPercent('bad'), '0%')
})

test('ChannelHeatmap.vue is mounted by Step4Report', () => {
  const component = readFileSync(join(__dirname, '../src/components/consumer/ChannelHeatmap.vue'), 'utf-8')
  const step4 = readFileSync(join(__dirname, '../src/components/Step4Report.vue'), 'utf-8')

  for (const label of ['Channel x Claim', 'Channel x Persona Segment', 'Channel x Risk Type', 'Channel x Purchase Intent']) {
    assert.ok(component.includes(label), `missing ${label}`)
  }
  assert.ok(step4.includes('ChannelHeatmap'), 'Step4Report must mount ChannelHeatmap')
})
