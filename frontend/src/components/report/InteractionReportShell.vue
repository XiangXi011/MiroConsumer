<template>
  <div class="left-panel report-style">
    <div v-if="reportOutline" class="report-content-wrapper">
      <div class="report-header-block">
        <div class="report-meta">
          <span class="report-tag">{{ isConsumerMode ? t('consumer.reportTag') : 'Prediction Report' }}</span>
          <span v-if="showTechnical" class="report-id">ID: {{ reportId || 'REF-2024-X92' }}</span>
        </div>
        <h1 class="main-title">{{ reportOutline.title }}</h1>
        <p class="sub-title">{{ reportOutline.summary }}</p>
        <div class="header-divider"></div>
      </div>

      <ReportSectionsList
        :sections="reportOutline.sections"
        :generated-sections="generatedSections"
        :collapsed-sections="collapsedSections"
        :current-section-index="currentSectionIndex"
        :is-consumer-mode="false"
        @toggle-section-collapse="idx => emit('toggle-section-collapse', idx)"
      />

      <InteractionHandoffPanel
        v-if="showTechnical && interviewHandoffContext"
        :handoff-context="interviewHandoffContext"
        @clear-handoff="emit('clear-interview-handoff')"
      />
    </div>

    <div v-if="!reportOutline" class="waiting-placeholder">
      <div class="waiting-animation">
        <div class="waiting-ring"></div>
        <div class="waiting-ring"></div>
        <div class="waiting-ring"></div>
      </div>
      <span class="waiting-text">{{ t('step5.loadingInteraction') }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
// @ts-nocheck
import { useI18n } from 'vue-i18n'
import InteractionHandoffPanel from './InteractionHandoffPanel.vue'
import ReportSectionsList from './ReportSectionsList.vue'

defineProps({
  reportOutline: { type: Object, default: null },
  generatedSections: { type: Object, default: () => ({}) },
  collapsedSections: { type: Object, default: () => new Set() },
  currentSectionIndex: { type: Number, default: null },
  isConsumerMode: { type: Boolean, default: false },
  showTechnical: { type: Boolean, default: false },
  reportId: { type: String, default: '' },
  interviewHandoffContext: { type: Object, default: null },
})

const emit = defineEmits(['toggle-section-collapse', 'clear-interview-handoff'])

const { t } = useI18n()
</script>

<style scoped>
.left-panel.report-style {
  width: 45%;
  min-width: 450px;
  background: var(--mc-bg-subtle);
  border-right: 1px solid var(--mc-border);
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  padding: 30px 50px 60px 50px;
}

.left-panel::-webkit-scrollbar {
  width: 6px;
}

.left-panel::-webkit-scrollbar-track {
  background: transparent;
}

.left-panel::-webkit-scrollbar-thumb {
  background: transparent;
  border-radius: 3px;
  transition: background 0.3s ease;
}

.left-panel:hover::-webkit-scrollbar-thumb {
  background: rgba(34, 92, 75, 0.18);
}

.left-panel::-webkit-scrollbar-thumb:hover {
  background: rgba(34, 92, 75, 0.28);
}

.report-content-wrapper {
  max-width: 800px;
  margin: 0 auto;
  width: 100%;
}

.report-header-block {
  margin-bottom: 30px;
}

.report-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 24px;
}

.report-tag {
  background: var(--mc-accent);
  color: #fffdfa;
  font-size: 11px;
  font-weight: 700;
  padding: 4px 8px;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.report-id {
  font-size: 11px;
  color: var(--mc-text-tertiary);
  font-weight: 500;
  letter-spacing: 0.02em;
}

.main-title {
  font-family: var(--mc-font-display);
  font-size: 36px;
  font-weight: 700;
  color: var(--mc-text-primary);
  line-height: 1.2;
  margin: 0 0 16px 0;
  letter-spacing: 0;
}

:global(html[lang="en"]) .report-header-block .main-title {
  font-size: 28px;
}

.sub-title {
  font-family: var(--mc-font-body);
  font-size: 16px;
  color: var(--mc-text-secondary);
  font-style: normal;
  line-height: 1.6;
  margin: 0 0 30px 0;
  font-weight: 400;
}

.header-divider {
  height: 1px;
  background: var(--mc-border);
  width: 100%;
}

.waiting-placeholder {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 20px;
  padding: 40px;
  color: var(--mc-text-tertiary);
}

.waiting-animation {
  position: relative;
  width: 48px;
  height: 48px;
}

.waiting-ring {
  position: absolute;
  width: 100%;
  height: 100%;
  border: 2px solid #E5E7EB;
  border-radius: 50%;
  animation: ripple 2s cubic-bezier(0.4, 0, 0.2, 1) infinite;
}

.waiting-ring:nth-child(2) {
  animation-delay: 0.4s;
}

.waiting-ring:nth-child(3) {
  animation-delay: 0.8s;
}

@keyframes ripple {
  0% { transform: scale(0.5); opacity: 1; }
  100% { transform: scale(2); opacity: 0; }
}

.waiting-text {
  font-size: 14px;
}

@media (max-width: 980px) {
  .left-panel.report-style {
    width: 100%;
    min-width: 0;
  }
}
</style>
