<template>
  <section
    v-if="visible"
    class="channel-heatmap"
    aria-label="Channel performance matrix"
  >
    <div class="heatmap-head">
      <span>Channel Matrix</span>
      <strong>渠道 × 指标</strong>
    </div>
    <div class="heatmap-grid">
      <div v-for="row in rows" :key="row.key" class="heatmap-row">
        <div class="heatmap-row-label">{{ row.label }}</div>
        <div class="heatmap-cells">
          <div
            v-for="cell in row.cells"
            :key="`${row.key}-${cell.channelId}`"
            class="heatmap-cell"
            :style="{ opacity: 0.35 + cell.value * 0.65 }"
          >
            <span>{{ cell.channelLabel }}</span>
            <strong class="mono">{{ cell.valueText }}</strong>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
// @ts-nocheck
import { computed } from 'vue'
import { buildChannelHeatmapRows } from '../../utils/channelPropagation'

const props = defineProps({
  channelMetrics: {
    type: Object,
    default: () => ({}),
  },
})

const rows = computed(() => buildChannelHeatmapRows(props.channelMetrics || {}))
const visible = computed(() => rows.value.some(row => row.cells.length > 0))
</script>

<style scoped>
.channel-heatmap {
  border: 1px solid #E5E7EB;
  background: #FFFFFF;
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.heatmap-head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
}

.heatmap-head span,
.heatmap-row-label {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: #6B7280;
}

.heatmap-grid {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.heatmap-row {
  display: grid;
  grid-template-columns: 190px 1fr;
  gap: 12px;
  align-items: stretch;
}

.heatmap-cells {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(110px, 1fr));
  gap: 8px;
}

.heatmap-cell {
  background: #ECFDF5;
  border: 1px solid #D1FAE5;
  padding: 9px 10px;
  display: flex;
  justify-content: space-between;
  gap: 8px;
  color: #064E3B;
  min-width: 0;
}

.heatmap-cell span {
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.mono {
  font-family: 'JetBrains Mono', monospace;
}

@media (max-width: 760px) {
  .heatmap-row {
    grid-template-columns: 1fr;
  }
}
</style>
