<template>
  <section v-if="visible" class="channel-fit-panel" aria-label="Channel Fit Panel">
    <div class="channel-fit-head">
      <span class="channel-fit-kicker">Channel Runtime</span>
      <strong>多渠道适配</strong>
    </div>

    <div class="channel-fit-summary">
      <div class="summary-item">
        <span>Best Launch Channel</span>
        <strong>{{ fitItems.summary.bestLaunchChannel }}</strong>
      </div>
      <div class="summary-item">
        <span>Highest Misread Channel</span>
        <strong>{{ fitItems.summary.highestMisreadChannel }}</strong>
      </div>
      <div class="summary-item">
        <span>Evidence Demand Channel</span>
        <strong>{{ fitItems.summary.highestEvidenceDemandChannel }}</strong>
      </div>
      <div class="summary-item">
        <span>Price Resistance Channel</span>
        <strong>{{ fitItems.summary.highestPriceResistanceChannel }}</strong>
      </div>
    </div>

    <div class="channel-fit-list">
      <div v-for="channel in fitItems.channels" :key="channel.channelId" class="channel-fit-row">
        <div class="channel-name">{{ channel.label }}</div>
        <div class="fit-track" aria-hidden="true">
          <span :style="{ width: channel.fitScoreText }"></span>
        </div>
        <div class="fit-score mono">{{ channel.fitScoreText }}</div>
        <div class="fit-risk">{{ channel.primaryRisk }}</div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
// @ts-nocheck
import { computed } from 'vue'
import { buildChannelFitItems } from '../../utils/channelPropagation'

const props = defineProps({
  context: {
    type: Object,
    default: () => ({}),
  },
})

const fitItems = computed(() => buildChannelFitItems(props.context || {}))
const visible = computed(() => fitItems.value.channels.length > 0)
</script>

<style scoped>
.channel-fit-panel {
  border: 1px solid #E5E7EB;
  background: #FFFFFF;
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.channel-fit-head,
.channel-fit-summary,
.channel-fit-row {
  display: grid;
  gap: 10px;
}

.channel-fit-head {
  grid-template-columns: 1fr auto;
  align-items: baseline;
}

.channel-fit-kicker,
.summary-item span {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: #6B7280;
}

.channel-fit-summary {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.summary-item {
  border: 1px solid #F3F4F6;
  background: #FAFAFA;
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.summary-item strong,
.channel-name {
  color: #111827;
  font-size: 13px;
}

.channel-fit-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.channel-fit-row {
  grid-template-columns: minmax(96px, 150px) minmax(120px, 1fr) 52px minmax(90px, 140px);
  align-items: center;
}

.fit-track {
  height: 8px;
  background: #F3F4F6;
  overflow: hidden;
}

.fit-track span {
  display: block;
  height: 100%;
  background: #1F2937;
}

.fit-score,
.fit-risk {
  font-size: 12px;
  color: #374151;
}

.mono {
  font-family: 'JetBrains Mono', monospace;
}

@media (max-width: 900px) {
  .channel-fit-summary,
  .channel-fit-row {
    grid-template-columns: 1fr;
  }
}
</style>
