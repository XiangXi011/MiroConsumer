<template>
  <div class="sections-list">
    <div
      v-for="(section, idx) in sections"
      :key="idx"
      class="report-section-item"
      :class="{
        'is-active': currentSectionIndex === idx + 1,
        'is-completed': isSectionCompleted(idx + 1),
        'is-pending': !isSectionCompleted(idx + 1) && currentSectionIndex !== idx + 1
      }"
    >
      <div
        class="section-header-row"
        :class="{ clickable: isSectionCompleted(idx + 1) }"
        @click="emit('toggle-section-collapse', idx)"
      >
        <span class="section-number">{{ String(idx + 1).padStart(2, '0') }}</span>
        <h3 class="section-title">{{ section.title }}</h3>
        <svg
          v-if="isSectionCompleted(idx + 1)"
          class="collapse-icon"
          :class="{ 'is-collapsed': collapsedSections.has(idx) }"
          viewBox="0 0 24 24"
          width="20"
          height="20"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
        >
          <polyline points="6 9 12 15 18 9"></polyline>
        </svg>
      </div>

      <div class="section-body" v-show="!collapsedSections.has(idx)">
        <div
          v-if="generatedSections[idx + 1]"
          class="generated-content"
          v-html="renderMarkdown(generatedSections[idx + 1])"
        ></div>

        <ConsumerResearchActionBar
          v-if="isConsumerMode && generatedSections[idx + 1]"
          :report-id="reportId"
          :simulation-id="simulationId"
          :section-index="idx + 1"
          :section-title="section.title"
          :section-content="generatedSections[idx + 1]"
          :branch-id="branchId"
          :disabled="disabled"
          @run-action="payload => emit('run-action', payload)"
        />

        <div v-else-if="currentSectionIndex === idx + 1" class="loading-state">
          <div class="loading-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <circle cx="12" cy="12" r="10" stroke-width="4" stroke="#E5E7EB"></circle>
              <path d="M12 2a10 10 0 0 1 10 10" stroke-width="4" stroke="#4B5563" stroke-linecap="round"></path>
            </svg>
          </div>
          <span class="loading-text">{{ t('step4.generatingSection', { title: section.title }) }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
// @ts-nocheck
import { useI18n } from 'vue-i18n'
import ConsumerResearchActionBar from '../consumer/ConsumerResearchActionBar.vue'
import { renderReportMarkdown as renderMarkdown } from '../../utils/reportMarkdown'

const { t } = useI18n()

const props = defineProps({
  sections: { type: Array, default: () => [] },
  generatedSections: { type: Object, default: () => ({}) },
  collapsedSections: { type: Object, default: () => new Set() },
  currentSectionIndex: { type: Number, default: null },
  isConsumerMode: { type: Boolean, default: false },
  reportId: { type: String, default: '' },
  simulationId: { type: String, default: '' },
  branchId: { type: String, default: '' },
  disabled: { type: Boolean, default: false },
})

const emit = defineEmits(['toggle-section-collapse', 'run-action'])

const isSectionCompleted = (sectionIndex) => {
  return !!props.generatedSections[sectionIndex]
}
</script>

<style scoped>
.sections-list {
  display: flex;
  flex-direction: column;
  gap: 32px;
}

.report-section-item {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.section-header-row {
  display: flex;
  align-items: baseline;
  gap: 12px;
  transition: background-color 0.2s ease;
  padding: 8px 12px;
  margin: -8px -12px;
  border-radius: 8px;
}

.section-header-row.clickable {
  cursor: pointer;
}

.section-header-row.clickable:hover {
  background-color: var(--mc-surface-muted);
}

.collapse-icon {
  margin-left: auto;
  color: var(--mc-text-tertiary);
  transition: transform 0.3s ease;
  flex-shrink: 0;
  align-self: center;
}

.collapse-icon.is-collapsed {
  transform: rotate(-90deg);
}

.section-number {
  font-family: var(--mc-font-mono);
  font-size: 16px;
  color: var(--mc-text-tertiary);
  font-weight: 500;
}

.section-title {
  font-family: var(--mc-font-display);
  font-size: 24px;
  font-weight: 600;
  color: var(--mc-text-primary);
  margin: 0;
  transition: color 0.3s ease;
}

.report-section-item.is-pending .section-title {
  color: var(--mc-border-strong);
}

.report-section-item.is-active .section-title,
.report-section-item.is-completed .section-title {
  color: var(--mc-text-primary);
}

.section-body {
  padding-left: 28px;
  overflow: hidden;
}

.generated-content {
  font-family: var(--mc-font-body);
  font-size: 14px;
  line-height: 1.8;
  color: var(--mc-text-secondary);
}

.generated-content :deep(p) {
  margin-bottom: 1em;
}

.generated-content :deep(.md-h2),
.generated-content :deep(.md-h3),
.generated-content :deep(.md-h4) {
  font-family: var(--mc-font-display);
  color: var(--mc-text-primary);
  margin-top: 1.5em;
  margin-bottom: 0.8em;
  font-weight: 700;
}

.generated-content :deep(.md-h2) {
  font-size: 18px;
  border-bottom: 1px solid var(--mc-border);
  padding-bottom: 8px;
  margin-top: 0;
}

.generated-content :deep(.md-h3) {
  font-size: 18px;
}

.generated-content :deep(.md-h4) {
  font-size: 16px;
}

.generated-content :deep(.md-ul),
.generated-content :deep(.md-ol) {
  padding-left: 24px;
  margin: 12px 0;
}

.generated-content :deep(.md-li),
.generated-content :deep(.md-oli) {
  margin: 6px 0;
}

.generated-content :deep(.md-quote) {
  border-left: 3px solid var(--mc-accent-soft);
  padding-left: 16px;
  margin: 1.5em 0;
  color: var(--mc-text-secondary);
  font-style: italic;
  font-family: var(--mc-font-body);
}

.generated-content :deep(.code-block) {
  background: var(--mc-surface-muted);
  padding: 12px;
  border-radius: 6px;
  font-family: var(--mc-font-mono);
  font-size: 12px;
  overflow-x: auto;
  margin: 1em 0;
  border: 1px solid var(--mc-border);
}

.generated-content :deep(strong) {
  font-weight: 600;
  color: var(--mc-text-primary);
}

.loading-state {
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--mc-text-secondary);
  font-size: 14px;
  margin-top: 4px;
}

.loading-icon {
  width: 18px;
  height: 18px;
  animation: spin 1s linear infinite;
  display: flex;
  align-items: center;
  justify-content: center;
}

.loading-text {
  font-family: var(--mc-font-body);
  font-size: 15px;
  color: var(--mc-text-secondary);
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
