import { test } from 'vitest'
import assert from 'node:assert/strict'
import { readFileSync } from 'fs'
import { fileURLToPath } from 'url'
import { dirname, join } from 'path'

import { buildPropagationPathRows } from '../src/utils/channelPropagation.js'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

test('buildPropagationPathRows formats cross-channel propagation paths', () => {
  const rows = buildPropagationPathRows({
    cross_channel_paths: [
      {
        first_actor_id: 'agent-1',
        source_channel_id: 'douyin',
        target_channel_id: 'wechat_group',
        cross_segment_depth: 3,
        cross_channel_count: 1,
        affected_segments: ['mom_group', 'student'],
        blocked_nodes: ['agent-5'],
        repair_nodes: ['agent-8'],
      },
    ],
  })

  assert.equal(rows[0].firstActorId, 'agent-1')
  assert.equal(rows[0].sourceChannelLabel, '抖音')
  assert.equal(rows[0].targetChannelLabel, '微信群')
  assert.equal(rows[0].affectedSegmentsText, 'mom_group, student')
})

test('PropagationPathGraph.vue is mounted by Step5Interaction', () => {
  const component = readFileSync(join(__dirname, '../src/components/consumer/PropagationPathGraph.vue'), 'utf-8')
  const step5 = readFileSync(join(__dirname, '../src/components/Step5Interaction.vue'), 'utf-8')

  for (const label of ['First Misreader', 'Propagation Target', 'Cross-Segment Depth', 'Cross-Channel Count', 'Blocked Nodes', 'Repair Nodes']) {
    assert.ok(component.includes(label), `missing ${label}`)
  }
  assert.ok(step5.includes('PropagationPathGraph'), 'Step5Interaction must mount PropagationPathGraph')
})
