<template>
  <section v-if="visible" class="path-graph" aria-label="Propagation Path Graph">
    <div class="path-head">
      <span>Propagation Path Graph</span>
      <strong>跨渠道传播路径</strong>
    </div>
    <div class="path-list">
      <div v-for="row in rows" :key="row.key" class="path-card">
        <div class="path-line">
          <span>{{ row.sourceChannelLabel }}</span>
          <span class="path-arrow">→</span>
          <span>{{ row.targetChannelLabel }}</span>
        </div>
        <div class="path-grid">
          <div><span>First Misreader</span><strong>{{ row.firstActorId }}</strong></div>
          <div><span>Propagation Target</span><strong>{{ row.targetChannelLabel }}</strong></div>
          <div><span>Cross-Segment Depth</span><strong class="mono">{{ row.crossSegmentDepth }}</strong></div>
          <div><span>Cross-Channel Count</span><strong class="mono">{{ row.crossChannelCount }}</strong></div>
          <div><span>Blocked Nodes</span><strong>{{ row.blockedNodesText }}</strong></div>
          <div><span>Repair Nodes</span><strong>{{ row.repairNodesText }}</strong></div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import { buildPropagationPathRows } from '../../utils/channelPropagation'

const props = defineProps({
  context: {
    type: Object,
    default: () => ({}),
  },
})

const rows = computed(() => buildPropagationPathRows(props.context || {}))
const visible = computed(() => rows.value.length > 0)
</script>

<style scoped>
.path-graph {
  border-bottom: 1px solid #E5E7EB;
  background: #FFFFFF;
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

.path-head span,
.path-grid span {
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

.path-line {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 14px;
  font-weight: 700;
  color: #111827;
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
  color: #111827;
  overflow-wrap: anywhere;
}

.mono {
  font-family: 'JetBrains Mono', monospace;
}
</style>
