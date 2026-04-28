<template>
  <section
    v-if="visible"
    class="society-run-summary"
    aria-label="Society Mode Agents Rounds LLM Budget Reach Misread Trust Recovery Purchase Intent"
  >
    <div class="society-summary-head">
      <span class="society-kicker">Consumer Society Runtime</span>
      <strong>大社会运行摘要</strong>
    </div>
    <div class="society-summary-grid">
      <div v-for="item in items" :key="item.key" class="society-summary-item">
        <span class="society-summary-label">{{ item.label }}</span>
        <span class="society-summary-value mono">{{ item.value }}</span>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import { buildSocietyRunSummaryItems } from '../../utils/societyRunSummary'

const props = defineProps({
  context: {
    type: Object,
    default: () => ({}),
  },
})

const items = computed(() => buildSocietyRunSummaryItems(props.context || {}))

const visible = computed(() => {
  const context = props.context || {}
  return Boolean(
    context.society_mode ||
    context.society_agents_count ||
    context.society_metrics,
  )
})
</script>

<style scoped>
.society-run-summary {
  border: 1px solid #E5E7EB;
  background: #FFFFFF;
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.society-summary-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 16px;
}

.society-kicker {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #6B7280;
}

.society-summary-head strong {
  font-size: 14px;
  color: #111827;
}

.society-summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
}

.society-summary-item {
  border: 1px solid #F3F4F6;
  background: #FAFAFA;
  padding: 9px 10px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.society-summary-label {
  font-size: 10px;
  color: #6B7280;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.society-summary-value {
  font-size: 16px;
  font-weight: 700;
  color: #111827;
  word-break: break-word;
}

.mono {
  font-family: 'JetBrains Mono', monospace;
}

@media (max-width: 760px) {
  .society-summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
