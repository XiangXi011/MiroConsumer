<template>
  <section v-if="visible" class="path-graph" aria-label="Propagation Path Graph">
    <div class="path-head">
      <span>Propagation Path Graph</span>
      <strong>跨渠道传播路径</strong>
    </div>
    <div class="path-controls">
      <label>
        <span>Round Playback</span>
        <select v-model="selectedRound">
          <option value="all">All rounds</option>
          <option v-for="round in roundOptions" :key="round" :value="round">R{{ round }}</option>
        </select>
      </label>
      <label>
        <span>Channel Filter</span>
        <select v-model="selectedChannel">
          <option value="all">All channels</option>
          <option v-for="channel in channelOptions" :key="channel.id" :value="channel.id">
            {{ channel.label }}
          </option>
        </select>
      </label>
    </div>
    <div class="path-list">
      <div
        v-for="row in playbackRows"
        :key="row.key"
        class="path-card"
        :class="{ 'path-card--critical': row.criticalPath, 'path-card--hub': row.hubScore >= 0.8 }"
        @mouseenter="hoveredNode = row"
        @mouseleave="hoveredNode = null"
      >
        <div class="path-line">
          <span>{{ row.sourceChannelLabel }}</span>
          <span class="path-arrow">→</span>
          <span>{{ row.targetChannelLabel }}</span>
        </div>
        <div class="path-grid">
          <div><span>First Misreader</span><strong>{{ row.firstActorId }}</strong></div>
          <div><span>Propagation Target</span><strong>{{ row.targetChannelLabel }}</strong></div>
          <div><span>Node Profile</span><strong>{{ row.consumerProfileSummary }}</strong></div>
          <div><span>Attitude Δ</span><strong class="mono">{{ row.attitudeDeltaText }}</strong></div>
          <div><span>Hub Nodes</span><strong class="mono">{{ row.hubScoreText }}</strong></div>
          <div><span>Critical Path</span><strong>{{ row.criticalPath ? 'Yes' : 'No' }}</strong></div>
          <div><span>Cross-Segment Depth</span><strong class="mono">{{ row.crossSegmentDepth }}</strong></div>
          <div><span>Cross-Channel Count</span><strong class="mono">{{ row.crossChannelCount }}</strong></div>
          <div><span>Blocked Nodes</span><strong>{{ row.blockedNodesText }}</strong></div>
          <div><span>Repair Nodes</span><strong>{{ row.repairNodesText }}</strong></div>
        </div>
      </div>
    </div>
    <div v-if="hoveredNode" class="node-popover" aria-live="polite">
      <span>Node Profile</span>
      <strong>{{ hoveredNode.firstActorId }}</strong>
      <p>{{ hoveredNode.consumerProfileSummary }}</p>
    </div>
  </section>
</template>

<script setup lang="ts">
// @ts-nocheck
import { computed, ref } from 'vue'
import { buildPropagationPathRows } from '../../utils/channelPropagation'

const props = defineProps({
  context: {
    type: Object,
    default: () => ({}),
  },
})

const rows = computed(() => buildPropagationPathRows(props.context || {}))
const selectedRound = ref('all')
const selectedChannel = ref('all')
const hoveredNode = ref(null)
const roundOptions = computed(() => (
  Array.from(new Set(rows.value.map(row => row.roundIndex))).sort((a, b) => a - b)
))
const channelOptions = computed(() => {
  const map = new Map()
  rows.value.forEach(row => {
    if (row.sourceChannelId) map.set(row.sourceChannelId, row.sourceChannelLabel)
    if (row.targetChannelId) map.set(row.targetChannelId, row.targetChannelLabel)
  })
  return Array.from(map.entries()).map(([id, label]) => ({ id, label }))
})
const playbackRows = computed(() => rows.value.filter(row => {
  const roundMatches = selectedRound.value === 'all' || row.roundIndex === Number(selectedRound.value)
  const channelMatches = selectedChannel.value === 'all' ||
    row.sourceChannelId === selectedChannel.value ||
    row.targetChannelId === selectedChannel.value
  return roundMatches && channelMatches
}))
const visible = computed(() => rows.value.length > 0)
</script>

<style scoped>
.path-graph {
  border-bottom: 1px solid #E5E7EB;
  background: var(--mc-surface);
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.path-head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
}

.path-controls {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.path-controls label {
  display: flex;
  align-items: center;
  gap: 8px;
  border: 1px solid #E5E7EB;
  background: #F9FAFB;
  padding: 7px 9px;
}

.path-controls select {
  border: 1px solid #D1D5DB;
  background: var(--mc-surface);
  color: var(--mc-text-primary);
  font-size: 12px;
  padding: 4px 6px;
}

.path-head span,
.path-grid span,
.path-controls span,
.node-popover span {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: #6B7280;
}

.path-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.path-card {
  border: 1px solid #E5E7EB;
  background: #FAFAFA;
  padding: 12px;
}

.path-card--critical {
  border-color: #F59E0B;
  background: var(--mc-status-warning-bg);
}

.path-card--hub {
  box-shadow: inset 3px 0 0 #10B981;
}

.path-line {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 14px;
  font-weight: 700;
  color: var(--mc-text-primary);
  margin-bottom: 10px;
}

.path-arrow {
  color: #6B7280;
}

.path-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.path-grid div {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
}

.path-grid strong {
  font-size: 12px;
  color: var(--mc-text-primary);
  overflow-wrap: anywhere;
}

.mono {
  font-family: 'JetBrains Mono', monospace;
}

.node-popover {
  border: 1px solid #D1D5DB;
  background: var(--mc-surface);
  padding: 10px 12px;
}

.node-popover strong {
  display: block;
  margin-top: 4px;
  color: var(--mc-text-primary);
}

.node-popover p {
  margin: 4px 0 0;
  color: #4B5563;
  font-size: 12px;
}
</style>
