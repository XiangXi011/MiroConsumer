<template>
  <div class="survey-container">
    <div class="survey-setup">
      <div class="setup-section">
        <div class="section-header">
          <span class="section-title">{{ t('step5.selectSurveyTarget') }}</span>
          <span class="selection-count">{{ t('step5.selectedCount', { selected: selectedAgents.size, total: profiles.length }) }}</span>
        </div>

        <div class="agents-grid">
          <label
            v-for="(profile, idx) in profiles"
            :key="idx"
            class="agent-checkbox"
            :class="{ checked: selectedAgents.has(idx) }"
          >
            <input
              type="checkbox"
              :checked="selectedAgents.has(idx)"
              @change="emit('toggle-agent-selection', idx)"
            >
            <div class="checkbox-avatar">{{ (profile.username || 'A')[0] }}</div>
            <div class="checkbox-info">
              <span class="checkbox-name">{{ profile.username }}</span>
              <span class="checkbox-role">{{ profile.profession || t('step2.unknownProfession') }}</span>
            </div>
            <div class="checkbox-indicator">
              <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="3">
                <polyline points="20 6 9 17 4 12"></polyline>
              </svg>
            </div>
          </label>
        </div>

        <div class="selection-actions">
          <button class="action-link" @click="emit('select-all-agents')">{{ t('step5.selectAll') }}</button>
          <span class="action-divider">|</span>
          <button class="action-link" @click="emit('clear-agent-selection')">{{ t('step5.clearSelection') }}</button>
        </div>
      </div>

      <div class="setup-section">
        <div class="section-header">
          <span class="section-title">{{ t('step5.surveyQuestions') }}</span>
        </div>
        <textarea
          :value="surveyQuestion"
          class="survey-input"
          :placeholder="t('step5.surveyInputPlaceholder')"
          rows="3"
          @input="emit('update:survey-question', $event.target.value)"
        ></textarea>
      </div>

      <button
        class="survey-submit-btn"
        :disabled="selectedAgents.size === 0 || !surveyQuestion.trim() || isSurveying"
        @click="emit('submit-survey')"
      >
        <span v-if="isSurveying" class="loading-spinner"></span>
        <span v-else>{{ t('step5.submitSurvey') }}</span>
      </button>
    </div>

    <div v-if="surveyResults.length > 0" class="survey-results">
      <div class="results-header">
        <span class="results-title">{{ t('step5.surveyResults') }}</span>
        <span class="results-count">{{ t('step5.surveyResultsCount', { count: surveyResults.length }) }}</span>
      </div>
      <div class="results-list">
        <div
          v-for="(result, idx) in surveyResults"
          :key="idx"
          class="result-card"
        >
          <div class="result-header">
            <div class="result-avatar">{{ (result.agent_name || 'A')[0] }}</div>
            <div class="result-info">
              <span class="result-name">{{ result.agent_name }}</span>
              <span class="result-role">{{ result.profession || t('step2.unknownProfession') }}</span>
            </div>
          </div>
          <div class="result-question">
            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"></circle>
              <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"></path>
              <line x1="12" y1="17" x2="12.01" y2="17"></line>
            </svg>
            <span>{{ result.question }}</span>
          </div>
          <div class="result-answer" v-html="renderMarkdown(result.answer)"></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
// @ts-nocheck
import { useI18n } from 'vue-i18n'
import { renderReportMarkdown as renderMarkdown } from '../../utils/reportMarkdown'

defineProps({
  profiles: { type: Array, default: () => [] },
  selectedAgents: { type: Object, default: () => new Set() },
  surveyQuestion: { type: String, default: '' },
  surveyResults: { type: Array, default: () => [] },
  isSurveying: { type: Boolean, default: false },
})

const emit = defineEmits([
  'toggle-agent-selection',
  'select-all-agents',
  'clear-agent-selection',
  'update:survey-question',
  'submit-survey',
])

const { t } = useI18n()
</script>

<style scoped>
.survey-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.survey-setup {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 24px;
  border-bottom: 1px solid #E5E7EB;
  overflow: hidden;
}

.setup-section {
  margin-bottom: 24px;
}

.setup-section:first-child {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-height: 0;
}

.setup-section:last-child {
  margin-bottom: 0;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.setup-section .section-header .section-title {
  font-size: 13px;
  font-weight: 600;
  color: #374151;
}

.selection-count {
  font-size: 12px;
  color: #9CA3AF;
}

.agents-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 10px;
  flex: 1;
  overflow-y: auto;
  padding: 4px;
  align-content: start;
}

.agent-checkbox {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  background: #F9FAFB;
  border: 1px solid #E5E7EB;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.agent-checkbox:hover {
  border-color: #D1D5DB;
}

.agent-checkbox.checked {
  background: #F0FDF4;
  border-color: #10B981;
}

.agent-checkbox input {
  display: none;
}

.checkbox-avatar {
  width: 28px;
  height: 28px;
  min-width: 28px;
  min-height: 28px;
  background: #E5E7EB;
  color: #374151;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 600;
  flex-shrink: 0;
}

.agent-checkbox.checked .checkbox-avatar {
  background: #10B981;
  color: #FFFFFF;
}

.checkbox-info {
  flex: 1;
  min-width: 0;
}

.checkbox-name {
  display: block;
  font-size: 12px;
  font-weight: 600;
  color: #1F2937;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.checkbox-role {
  display: block;
  font-size: 10px;
  color: #9CA3AF;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.checkbox-indicator {
  width: 20px;
  height: 20px;
  border: 2px solid #E5E7EB;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: all 0.2s ease;
}

.agent-checkbox.checked .checkbox-indicator {
  background: #10B981;
  border-color: #10B981;
  color: #FFFFFF;
}

.checkbox-indicator svg {
  opacity: 0;
  transform: scale(0.5);
  transition: all 0.2s ease;
}

.agent-checkbox.checked .checkbox-indicator svg {
  opacity: 1;
  transform: scale(1);
}

.selection-actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}

.action-link {
  font-size: 12px;
  color: #6B7280;
  background: none;
  border: none;
  cursor: pointer;
  padding: 0;
}

.action-link:hover {
  color: #1F2937;
  text-decoration: underline;
}

.action-divider {
  color: #E5E7EB;
}

.survey-input {
  width: 100%;
  padding: 14px 16px;
  font-size: 14px;
  border: 1px solid #E5E7EB;
  border-radius: 8px;
  resize: none;
  font-family: inherit;
  line-height: 1.5;
  transition: border-color 0.2s ease;
}

.survey-input:focus {
  outline: none;
  border-color: #1F2937;
}

.survey-submit-btn {
  width: 100%;
  padding: 14px 24px;
  font-size: 14px;
  font-weight: 600;
  color: #FFFFFF;
  background: #1F2937;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-top: 20px;
}

.survey-submit-btn:hover:not(:disabled) {
  background: #374151;
}

.survey-submit-btn:disabled {
  background: #E5E7EB;
  color: #9CA3AF;
  cursor: not-allowed;
}

.loading-spinner {
  width: 18px;
  height: 18px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #FFFFFF;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.survey-results {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}

.results-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.results-title {
  font-size: 14px;
  font-weight: 600;
  color: #1F2937;
}

.results-count {
  font-size: 12px;
  color: #9CA3AF;
}

.results-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.result-card {
  background: #F9FAFB;
  border: 1px solid #E5E7EB;
  border-radius: 12px;
  padding: 20px;
}

.result-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.result-avatar {
  width: 36px;
  height: 36px;
  min-width: 36px;
  min-height: 36px;
  background: #1F2937;
  color: #FFFFFF;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 600;
  flex-shrink: 0;
}

.result-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.result-name {
  font-size: 14px;
  font-weight: 600;
  color: #1F2937;
}

.result-role {
  font-size: 12px;
  color: #9CA3AF;
}

.result-question {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 12px 14px;
  background: #FFFFFF;
  border-radius: 8px;
  margin-bottom: 12px;
  font-size: 13px;
  color: #6B7280;
}

.result-question svg {
  flex-shrink: 0;
  margin-top: 2px;
}

.result-answer {
  font-size: 14px;
  line-height: 1.7;
  color: #374151;
}

.result-answer :deep(.md-quote) {
  margin: 12px 0;
  padding: 12px 16px;
  background: #F9FAFB;
  border-left: 3px solid #1F2937;
  color: #4B5563;
}
</style>
