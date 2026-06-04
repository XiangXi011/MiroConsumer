<template>
  <div class="handoff-panel">
    <div class="handoff-panel-header">
      <span class="handoff-panel-title">{{ t('step5.technicalInterviewContext') }}</span>
      <button class="handoff-panel-clear" @click="emit('clear-handoff')">
        <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="18" y1="6" x2="6" y2="18"></line>
          <line x1="6" y1="6" x2="18" y2="18"></line>
        </svg>
      </button>
    </div>

    <div class="handoff-panel-body">
      <div v-if="handoffContext.report_id" class="handoff-row">
        <span class="handoff-key">Report</span>
        <span class="handoff-value mono">{{ handoffContext.report_id }}</span>
      </div>
      <div v-if="handoffContext.section_index !== undefined && handoffContext.section_index !== null" class="handoff-row">
        <span class="handoff-key">Section</span>
        <span class="handoff-value mono">{{ handoffContext.section_index }}</span>
      </div>
      <div v-if="handoffContext.finding_id" class="handoff-row">
        <span class="handoff-key">Finding</span>
        <span class="handoff-value mono">{{ handoffContext.finding_id }}</span>
      </div>
      <div v-if="handoffContext.claim" class="handoff-row">
        <span class="handoff-key">Claim</span>
        <span class="handoff-value">{{ handoffContext.claim }}</span>
      </div>
      <div v-if="handoffContext.branch_id" class="handoff-row">
        <span class="handoff-key">Branch</span>
        <span class="handoff-value mono">{{ handoffContext.branch_id }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
// @ts-nocheck
import { useI18n } from 'vue-i18n'

defineProps({
  handoffContext: { type: Object, required: true },
})

const emit = defineEmits(['clear-handoff'])

const { t } = useI18n()
</script>

<style scoped>
.handoff-panel {
  margin-top: 24px;
  padding: 16px;
  background: #F8FAFC;
  border: 1px solid #E2E8F0;
  border-radius: 8px;
}

.handoff-panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.handoff-panel-title {
  font-size: 12px;
  font-weight: 600;
  color: #475569;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.handoff-panel-clear {
  width: 24px;
  height: 24px;
  background: #E2E8F0;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #64748B;
  transition: all 0.2s ease;
}

.handoff-panel-clear:hover {
  background: #CBD5E1;
  color: #334155;
}

.handoff-panel-body {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.handoff-row {
  display: flex;
  align-items: baseline;
  gap: 8px;
  font-size: 12px;
}

.handoff-key {
  color: #94A3B8;
  min-width: 60px;
  font-weight: 500;
}

.handoff-value {
  color: #334155;
  font-weight: 500;
  word-break: break-word;
}

.mono {
  font-family: var(--mc-font-mono);
}
</style>
