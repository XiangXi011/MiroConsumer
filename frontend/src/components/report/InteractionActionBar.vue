<template>
  <div class="action-bar">
    <div class="action-bar-header">
      <svg class="action-bar-icon" viewBox="0 0 24 24" width="28" height="28" fill="none" stroke="currentColor" stroke-width="1.5">
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
      </svg>
      <div class="action-bar-text">
        <span class="action-bar-title">{{ t('step5.businessTitle') }}</span>
        <span class="action-bar-subtitle">{{ t('step5.businessSubtitle', { count: profiles.length }) }}</span>
      </div>
    </div>

    <div class="action-bar-tabs">
      <button
        class="tab-pill"
        :class="{ active: activeTab === 'chat' && chatTarget === 'report_agent' }"
        @click="emit('select-report-agent-chat')"
      >
        <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"></path>
        </svg>
        <span>{{ t('step5.chatWithReportAgent') }}</span>
      </button>

      <div class="agent-dropdown" v-if="profiles.length > 0">
        <button
          class="tab-pill agent-pill"
          :class="{ active: activeTab === 'chat' && chatTarget === 'agent' }"
          @click="emit('toggle-agent-dropdown')"
        >
          <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
            <circle cx="12" cy="7" r="4"></circle>
          </svg>
          <span>{{ selectedAgent ? selectedAgent.username : t('step5.chatWithAgent') }}</span>
          <svg class="dropdown-arrow" :class="{ open: showAgentDropdown }" viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="6 9 12 15 18 9"></polyline>
          </svg>
        </button>
        <div v-if="showAgentDropdown" class="dropdown-menu">
          <div class="dropdown-header">{{ t('step5.selectChatTarget') }}</div>
          <div
            v-for="(agent, idx) in profiles"
            :key="idx"
            class="dropdown-item"
            @click="emit('select-agent', agent, idx)"
          >
            <div class="agent-avatar">{{ (agent.username || 'A')[0] }}</div>
            <div class="agent-info">
              <span class="agent-name">{{ agent.username }}</span>
              <span class="agent-role">{{ agent.profession || t('step2.unknownProfession') }}</span>
            </div>
          </div>
        </div>
      </div>

      <div class="tab-divider"></div>
      <button
        class="tab-pill survey-pill"
        :class="{ active: activeTab === 'survey' }"
        @click="emit('select-survey-tab')"
      >
        <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M9 11l3 3L22 4"></path>
          <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"></path>
        </svg>
        <span>{{ t('step5.sendSurvey') }}</span>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
// @ts-nocheck
import { useI18n } from 'vue-i18n'

defineProps({
  activeTab: { type: String, required: true },
  chatTarget: { type: String, required: true },
  profiles: { type: Array, default: () => [] },
  selectedAgent: { type: Object, default: null },
  showAgentDropdown: { type: Boolean, default: false },
})

const emit = defineEmits([
  'select-report-agent-chat',
  'toggle-agent-dropdown',
  'select-agent',
  'select-survey-tab',
])

const { t } = useI18n()
</script>

<style scoped>
.action-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px;
  border-bottom: 1px solid var(--mc-border);
  background: linear-gradient(180deg, var(--mc-surface) 0%, var(--mc-bg-subtle) 100%);
  gap: 16px;
}

.action-bar-header {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 160px;
}

.action-bar-icon {
  color: var(--mc-accent);
  flex-shrink: 0;
}

.action-bar-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.action-bar-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--mc-text-primary);
  letter-spacing: -0.01em;
}

.action-bar-subtitle {
  font-size: 11px;
  color: var(--mc-text-secondary);
}

.action-bar-subtitle.mono {
  font-family: var(--mc-font-mono);
}

.action-bar-tabs {
  display: flex;
  align-items: center;
  gap: 6px;
  flex: 1;
  justify-content: flex-end;
}

.tab-pill {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  font-size: 12px;
  font-weight: 500;
  color: var(--mc-text-secondary);
  background: var(--mc-surface);
  border: 1px solid var(--mc-border);
  border-radius: var(--mc-radius-pill);
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;
}

.tab-pill:hover {
  background: var(--mc-accent-wash);
  color: var(--mc-accent);
}

.tab-pill.active {
  background: var(--mc-accent);
  color: #fffdfa;
  box-shadow: 0 8px 18px rgba(34, 92, 75, 0.16);
}

.tab-pill svg {
  flex-shrink: 0;
  opacity: 0.7;
}

.tab-pill.active svg {
  opacity: 1;
}

.tab-divider {
  width: 1px;
  height: 24px;
  background: #E5E7EB;
  margin: 0 6px;
}

.agent-pill {
  width: 200px;
  justify-content: space-between;
}

.agent-pill span {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  text-align: left;
}

.survey-pill {
  background: #ECFDF5;
  color: #047857;
}

.survey-pill:hover {
  background: #D1FAE5;
  color: #065F46;
}

.survey-pill.active {
  background: #047857;
  color: #FFFFFF;
  box-shadow: 0 2px 8px rgba(4, 120, 87, 0.2);
}

.agent-dropdown {
  position: relative;
}

.dropdown-arrow {
  margin-left: 4px;
  transition: transform 0.2s ease;
  opacity: 0.6;
}

.dropdown-arrow.open {
  transform: rotate(180deg);
}

.dropdown-menu {
  position: absolute;
  top: calc(100% + 6px);
  left: 50%;
  transform: translateX(-50%);
  min-width: 240px;
  background: #FFFFFF;
  border: 1px solid #E5E7EB;
  border-radius: 12px;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.12), 0 4px 12px rgba(0, 0, 0, 0.06);
  max-height: 320px;
  overflow-y: auto;
  z-index: 100;
}

.dropdown-header {
  padding: 12px 16px 8px;
  font-size: 11px;
  font-weight: 600;
  color: #9CA3AF;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  border-bottom: 1px solid #F3F4F6;
}

.dropdown-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
  cursor: pointer;
  transition: all 0.15s ease;
  border-left: 3px solid transparent;
}

.dropdown-item:hover {
  background: #F9FAFB;
  border-left-color: #1F2937;
}

.dropdown-item:first-of-type {
  margin-top: 4px;
}

.dropdown-item:last-child {
  margin-bottom: 4px;
}

.agent-avatar {
  width: 32px;
  height: 32px;
  min-width: 32px;
  min-height: 32px;
  background: linear-gradient(135deg, #1F2937 0%, #374151 100%);
  color: #FFFFFF;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
  flex-shrink: 0;
  box-shadow: 0 2px 4px rgba(31, 41, 55, 0.1);
}

.agent-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1;
  min-width: 0;
}

.agent-name {
  font-size: 13px;
  font-weight: 600;
  color: #1F2937;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.agent-role {
  font-size: 11px;
  color: #9CA3AF;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

@media (max-width: 768px) {
  .action-bar {
    flex-direction: column;
    align-items: stretch;
  }

  .action-bar-tabs {
    justify-content: flex-start;
    overflow-x: auto;
  }
}
</style>
