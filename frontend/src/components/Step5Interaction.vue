<template>
  <div class="interaction-panel">
    <!-- Main Split Layout -->
    <div class="main-split-layout" :class="{ 'technical-open': showTechnical }">
      <InteractionReportShell
        ref="leftPanel"
        :report-outline="reportOutline"
        :generated-sections="generatedSections"
        :collapsed-sections="collapsedSections"
        :current-section-index="currentSectionIndex"
        :is-consumer-mode="isConsumerMode"
        :show-technical="showTechnical"
        :report-id="reportId"
        :interview-handoff-context="interviewHandoffContext"
        @toggle-section-collapse="toggleSectionCollapse"
        @clear-interview-handoff="clearInterviewHandoff"
      />

      <InteractionWorkspaceShell
        ref="chatPanelRef"
        :active-tab="activeTab"
        :chat-target="chatTarget"
        :profiles="profiles"
        :selected-agent="selectedAgent"
        :show-agent-dropdown="showAgentDropdown"
        :show-technical="showTechnical"
        :is-consumer-mode="isConsumerMode"
        :simulation-id="simulationId"
        :comparison-snapshot="comparisonSnapshot"
        :report-context="reportContext"
        :consumer-quick-prompts="consumerQuickPrompts"
        :consumer-voc-highlights="consumerVocHighlights"
        :consumer-source-catalog="consumerSourceCatalog"
        :consumer-enriched-findings="consumerEnrichedFindings"
        :chat-history="chatHistory"
        v-model:chat-input="chatInput"
        :is-sending="isSending"
        :interview-handoff-context="interviewHandoffContext"
        :selected-agents="selectedAgents"
        v-model:survey-question="surveyQuestion"
        :survey-results="surveyResults"
        :is-surveying="isSurveying"
        @select-report-agent-chat="selectReportAgentChat"
        @toggle-agent-dropdown="toggleAgentDropdown"
        @select-agent="selectAgent"
        @select-survey-tab="selectSurveyTab"
        @update:branch-comparison="workspaceBranchComparison = $event"
        @update:comparison-snapshot="workspaceComparisonSnapshot = $event"
        @apply-prompt="applyQuickPrompt"
        @send-message="sendMessage"
        @add-log="addLog"
        @toggle-agent-selection="toggleAgentSelection"
        @select-all-agents="selectAllAgents"
        @clear-agent-selection="clearAgentSelection"
        @submit-survey="submitSurvey"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
// @ts-nocheck
import { ref, watch, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { chatWithReport, getReport, getAgentLog } from '../api/report'
import { interviewAgents, getSimulationProfilesRealtime } from '../api/simulation'
import { useStep5ChatState } from '../composables/useStep5ChatState'
import { useStep5ConsumerContextState } from '../composables/useStep5ConsumerContextState'
import { useStep5ReportDataState } from '../composables/useStep5ReportDataState'
import { useStep5SurveyState } from '../composables/useStep5SurveyState'
import {
  loadConsumerInterviewHandoff,
  clearConsumerInterviewHandoff,
} from '../utils/consumerResearchActions'
import {
  buildSurveyInterviewRequests,
  extractAgentChatResponse,
  normalizeSurveyResults,
} from '../utils/step5Survey'
import InteractionReportShell from './report/InteractionReportShell.vue'
import InteractionWorkspaceShell from './report/InteractionWorkspaceShell.vue'

const { t } = useI18n()

const props = defineProps({
  reportId: String,
  simulationId: String,
  reportData: Object,
  projectData: Object,
  comparisonSnapshot: Object,
  showTechnical: { type: Boolean, default: false },
})

const emit = defineEmits(['add-log', 'update-status'])

const addLog = (msg) => {
  emit('add-log', msg)
}

const {
  activeTab,
  chatTarget,
  showAgentDropdown,
  selectedAgent,
  selectedAgentIndex,
  chatInput,
  chatHistory,
  isSending,
  chatPanelRef,
  applyQuickPrompt,
  selectChatTarget,
  saveChatHistory,
  selectReportAgentChat,
  selectSurveyTab,
  toggleAgentDropdown,
  selectAgent,
  scrollToBottom,
} = useStep5ChatState({
  addLog,
  formatSelectChatTargetLog: agent => t('log.selectChatTarget', { name: agent.username }),
})

// Consumer interview handoff state
const interviewHandoffContext = ref(null)

const {
  reportOutline,
  generatedSections,
  collapsedSections,
  currentSectionIndex,
  profiles,
  toggleSectionCollapse,
  applyReportLogs,
  setProfiles,
} = useStep5ReportDataState()

const {
  selectedAgents,
  surveyQuestion,
  surveyResults,
  isSurveying,
  toggleAgentSelection,
  selectAllAgents,
  clearAgentSelection,
} = useStep5SurveyState({ profiles })

const {
  isConsumerMode,
  reportContext,
  workspaceBranchComparison,
  workspaceComparisonSnapshot,
  consumerQuickPrompts,
  consumerVocHighlights,
  consumerSourceCatalog,
  consumerEnrichedFindings,
} = useStep5ConsumerContextState({ props, t })

// Refs
const leftPanel = ref(null)

// Chat Methods
const sendMessage = async () => {
  if (!chatInput.value.trim() || isSending.value) return
  
  const message = chatInput.value.trim()
  chatInput.value = ''
  
  // Add user message
  chatHistory.value.push({
    role: 'user',
    content: message,
    timestamp: new Date().toISOString()
  })
  
  scrollToBottom()
  isSending.value = true
  
  try {
    if (chatTarget.value === 'report_agent') {
      await sendToReportAgent(message)
    } else {
      await sendToAgent(message)
    }
  } catch (err) {
    addLog(t('log.sendFailed', { error: err.message }))
    chatHistory.value.push({
      role: 'assistant',
      content: t('step5.errorOccurred', { error: err.message }),
      timestamp: new Date().toISOString()
    })
  } finally {
    isSending.value = false
    scrollToBottom()
    // 自动保存对话记录到缓存
    saveChatHistory()
  }
}

const sendToReportAgent = async (message) => {
  addLog(t('log.sendToReportAgent', { message: message.substring(0, 50) }))
  
  // Build chat history for API
  const historyForApi = chatHistory.value
    .filter(msg => msg.role !== 'user' || msg.content !== message)
    .slice(-10) // Keep last 10 messages
    .map(msg => ({
      role: msg.role,
      content: msg.content
    }))
  
  const res = await chatWithReport({
    simulation_id: props.simulationId,
    message: message,
    chat_history: historyForApi
  })
  
  if (res.success && res.data) {
    chatHistory.value.push({
      role: 'assistant',
      content: res.data.response || res.data.answer || t('step5.noResponse'),
      timestamp: new Date().toISOString()
    })
    addLog(t('log.reportAgentReplied'))
  } else {
    throw new Error(res.error || t('step5.requestFailed'))
  }
}

const sendToAgent = async (message) => {
  if (!selectedAgent.value || selectedAgentIndex.value === null) {
    throw new Error(t('step5.selectAgentFirst'))
  }
  
  addLog(t('log.sendToAgent', { name: selectedAgent.value.username, message: message.substring(0, 50) }))
  
  // Build prompt with chat history
  let prompt = message
  if (chatHistory.value.length > 1) {
    const historyContext = chatHistory.value
      .filter(msg => msg.content !== message)
      .slice(-6)
      .map(msg => `${msg.role === 'user' ? '提问者' : '你'}：${msg.content}`)
      .join('\n')
    prompt = `以下是我们之前的对话：\n${historyContext}\n\n现在我的新问题是：${message}`
  }
  
  const res = await interviewAgents({
    simulation_id: props.simulationId,
    interviews: [{
      agent_id: selectedAgentIndex.value,
      prompt: prompt
    }]
  })
  
  if (res.success && res.data) {
    const resultData = res.data.result || res.data
    const responseContent = extractAgentChatResponse({
      resultData,
      agentId: selectedAgentIndex.value,
    })
    
    if (responseContent) {
      chatHistory.value.push({
        role: 'assistant',
        content: responseContent,
        timestamp: new Date().toISOString()
      })
      addLog(t('log.agentReplied', { name: selectedAgent.value.username }))
    } else {
      throw new Error(t('step5.noResponse'))
    }
  } else {
    throw new Error(res.error || t('step5.requestFailed'))
  }
}

const submitSurvey = async () => {
  if (selectedAgents.value.size === 0 || !surveyQuestion.value.trim()) return
  
  isSurveying.value = true
  addLog(t('log.sendSurvey', { count: selectedAgents.value.size }))
  
  try {
    const question = surveyQuestion.value.trim()
    const interviews = buildSurveyInterviewRequests(selectedAgents.value, question)
    
    const res = await interviewAgents({
      simulation_id: props.simulationId,
      interviews: interviews
    })
    
    if (res.success && res.data) {
      const resultData = res.data.result || res.data
      surveyResults.value = normalizeSurveyResults({
        interviews,
        profiles: profiles.value,
        resultData,
        question,
        noResponseText: t('step5.noResponse'),
      })
      addLog(t('log.receivedReplies', { count: surveyResults.value.length }))
    } else {
      throw new Error(res.error || t('step5.requestFailed'))
    }
  } catch (err) {
    addLog(t('log.surveySendFailed', { error: err.message }))
  } finally {
    isSurveying.value = false
  }
}

// Load Report Data
const loadReportData = async () => {
  if (!props.reportId) return
  
  try {
    addLog(t('log.loadReportData', { id: props.reportId }))
    
    // Get report info
    const reportRes = await getReport(props.reportId)
    if (reportRes.success && reportRes.data) {
      // Load agent logs to get report outline and sections
      await loadAgentLogs()
    }
  } catch (err) {
    addLog(t('log.loadReportFailed', { error: err.message }))
  }
}

const loadAgentLogs = async () => {
  if (!props.reportId) return
  
  try {
    const res = await getAgentLog(props.reportId, 0)
    if (res.success && res.data) {
      const logs = res.data.logs || []
      
      applyReportLogs(logs)
      
      addLog(t('log.reportDataLoaded'))
    }
  } catch (err) {
    addLog(t('log.loadReportLogFailed', { error: err.message }))
  }
}

const loadProfiles = async () => {
  if (!props.simulationId) return
  
  try {
    const res = await getSimulationProfilesRealtime(props.simulationId, 'reddit')
    if (res.success && res.data) {
      setProfiles(res.data.profiles || [])
      addLog(t('log.loadedProfiles', { count: profiles.value.length }))
    }
  } catch (err) {
    addLog(t('log.loadProfilesFailed', { error: err.message }))
  }
}

// Click outside to close dropdown
const handleClickOutside = (e) => {
  const dropdown = document.querySelector('.agent-dropdown')
  if (dropdown && !dropdown.contains(e.target)) {
    showAgentDropdown.value = false
  }
}

const loadInterviewHandoff = () => {
  if (!props.simulationId) {
    interviewHandoffContext.value = null
    return
  }
  interviewHandoffContext.value = loadConsumerInterviewHandoff(props.simulationId)
}

const clearInterviewHandoff = () => {
  if (!props.simulationId) return
  clearConsumerInterviewHandoff(props.simulationId)
  interviewHandoffContext.value = null
}

// Lifecycle
onMounted(() => {
  addLog(t('log.step5Init'))
  loadReportData()
  loadProfiles()
  loadInterviewHandoff()
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})

watch(() => props.reportId, (newId) => {
  if (newId) {
    loadReportData()
  }
}, { immediate: true })

watch(() => props.simulationId, (newId) => {
  if (newId) {
    loadProfiles()
    loadInterviewHandoff()
  }
}, { immediate: true })
</script>

<style scoped>
.interaction-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--mc-bg-canvas);
  font-family: var(--mc-font-body);
  overflow: hidden;
}

/* Utility Classes */
.mono {
  font-family: var(--mc-font-mono);
}

/* Main Split Layout */
.main-split-layout {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.main-split-layout:not(.technical-open) :deep(.left-panel.report-style) {
  width: 42%;
  min-width: 360px;
  padding: 28px 34px 56px;
  background: var(--mc-bg-subtle);
}

.main-split-layout:not(.technical-open) :deep(.report-content-wrapper) {
  max-width: 620px;
}

.main-split-layout:not(.technical-open) :deep(.right-panel) {
  flex: 1.2;
}

@media (max-width: 980px) {
  .main-split-layout,
  .main-split-layout:not(.technical-open) {
    flex-direction: column;
    overflow-y: auto;
  }

  :deep(.left-panel.report-style),
  .main-split-layout:not(.technical-open) :deep(.left-panel.report-style) {
    width: 100%;
    min-width: 0;
    max-height: 44vh;
    border-right: none;
    border-bottom: 1px solid #E5E7EB;
    padding: 22px 18px 28px;
  }

  :deep(.right-panel) {
    min-height: 56vh;
  }

}
</style>
