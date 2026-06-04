import { test } from 'vitest'
import assert from 'node:assert/strict'
import { readFileSync } from 'fs'
import { fileURLToPath } from 'url'
import { dirname, join } from 'path'

import { buildPropagationPathRows } from '../src/utils/channelPropagation.ts'

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

test('buildPropagationPathRows carries node exploration playback and heatmap metadata', () => {
  const rows = buildPropagationPathRows({
    cross_channel_paths: [
      {
        path_id: 'p1',
        first_actor_id: 'agent-1',
        source_channel_id: 'douyin',
        target_channel_id: 'wechat_group',
        round_index: 3,
        attitude_delta: 0.18,
        consumer_profile_summary: 'price-sensitive mom, high evidence demand',
        hub_score: 0.91,
        critical_path: true,
      },
    ],
  })

  assert.equal(rows[0].roundIndex, 3)
  assert.equal(rows[0].sourceChannelId, 'douyin')
  assert.equal(rows[0].attitudeDeltaText, '+18pp')
  assert.equal(rows[0].consumerProfileSummary, 'price-sensitive mom, high evidence demand')
  assert.equal(rows[0].hubScoreText, '91%')
  assert.equal(rows[0].criticalPath, true)
})

test('PropagationPathGraph.vue is mounted by Step5Interaction', () => {
  const component = readFileSync(join(__dirname, '../src/components/consumer/PropagationPathGraph.vue'), 'utf-8')
  const step5 = readFileSync(join(__dirname, '../src/components/Step5Interaction.vue'), 'utf-8')
  const workspaceShell = readFileSync(join(__dirname, '../src/components/report/InteractionWorkspaceShell.vue'), 'utf-8')

  for (const label of ['First Misreader', 'Propagation Target', 'Cross-Segment Depth', 'Cross-Channel Count', 'Blocked Nodes', 'Repair Nodes']) {
    assert.ok(component.includes(label), `missing ${label}`)
  }
  for (const label of ['Round Playback', 'Channel Filter', 'Node Profile', 'Attitude Δ', 'Hub Nodes', 'Critical Path']) {
    assert.ok(component.includes(label), `missing ${label}`)
  }
  for (const stateName of ['selectedRound', 'selectedChannel', 'hoveredNode', 'playbackRows']) {
    assert.ok(component.includes(stateName), `missing ${stateName}`)
  }
  assert.ok(step5.includes('InteractionWorkspaceShell'), 'Step5Interaction must mount InteractionWorkspaceShell')
  assert.ok(workspaceShell.includes('PropagationPathGraph'), 'InteractionWorkspaceShell must mount PropagationPathGraph')
})
