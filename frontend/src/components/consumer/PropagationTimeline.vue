<template>
  <section
    v-if="visible"
    class="propagation-timeline"
    aria-label="Propagation Timeline Initial reaction Claim amplification Objection emergence Misread spread Evidence repair"
  >
    <div class="timeline-head">
      <span>Propagation Timeline</span>
      <strong>传播阶段</strong>
    </div>
    <div class="timeline-list">
      <div v-for="item in items" :key="item.phase" class="timeline-row">
        <span class="timeline-range mono">{{ item.roundRange }}</span>
        <div class="timeline-copy">
          <strong>{{ item.phase }}</strong>
          <p>{{ item.summary }}</p>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
// @ts-nocheck
import { computed } from 'vue'
import { buildPropagationTimelineItems } from '../../utils/channelPropagation'

const props = defineProps({
  context: {
    type: Object,
    default: () => ({}),
  },
})

const items = computed(() => buildPropagationTimelineItems(props.context || {}))
const visible = computed(() => items.value.length > 0)
</script>

<style scoped>
.propagation-timeline {
  border: 1px solid #E5E7EB;
  background: #FFFFFF;
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.timeline-head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
}

.timeline-head span {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: #6B7280;
}

.timeline-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.timeline-row {
  display: grid;
  grid-template-columns: 72px 1fr;
  gap: 12px;
  border-left: 2px solid #111827;
  padding-left: 12px;
}

.timeline-range {
  font-size: 12px;
  color: #111827;
}

.timeline-copy strong {
  font-size: 13px;
  color: #111827;
}

.timeline-copy p {
  margin: 4px 0 0;
  color: #4B5563;
  font-size: 12px;
  line-height: 1.5;
}

.mono {
  font-family: 'JetBrains Mono', monospace;
}
</style>
