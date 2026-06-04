<template>
  <div class="interaction-panel">
    <!-- Main Split Layout -->
    <div class="main-split-layout" :class="{ 'technical-open': showTechnical }">
      <!-- LEFT PANEL: Report Style -->
      <div class="left-panel report-style" ref="leftPanel">
        <div v-if="reportOutline" class="report-content-wrapper">
          <!-- Report Header -->
          <div class="report-header-block">
            <div class="report-meta">
              <span class="report-tag">{{ isConsumerMode ? $t('consumer.reportTag') : 'Prediction Report' }}</span>
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
            @toggle-section-collapse="toggleSectionCollapse"
          />

          <!-- Consumer Interview Handoff Panel -->
          <div v-if="showTechnical && interviewHandoffContext" class="handoff-panel">
            <div class="handoff-panel-header">
              <span class="handoff-panel-title">{{ $t('step5.technicalInterviewContext') }}</span>
              <button class="handoff-panel-clear" @click="clearInterviewHandoff">
                <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
                  <line x1="18" y1="6" x2="6" y2="18"></line>
                  <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
              </button>
            </div>
            <div class="handoff-panel-body">
              <div v-if="interviewHandoffContext.report_id" class="handoff-row">
                <span class="handoff-key">Report</span>
                <span class="handoff-value mono">{{ interviewHandoffContext.report_id }}</span>
              </div>
              <div v-if="interviewHandoffContext.section_index !== undefined && interviewHandoffContext.section_index !== null" class="handoff-row">
                <span class="handoff-key">Section</span>
                <span class="handoff-value mono">{{ interviewHandoffContext.section_index }}</span>
              </div>
              <div v-if="interviewHandoffContext.finding_id" class="handoff-row">
                <span class="handoff-key">Finding</span>
                <span class="handoff-value mono">{{ interviewHandoffContext.finding_id }}</span>
              </div>
              <div v-if="interviewHandoffContext.claim" class="handoff-row">
                <span class="handoff-key">Claim</span>
                <span class="handoff-value">{{ interviewHandoffContext.claim }}</span>
              </div>
              <div v-if="interviewHandoffContext.branch_id" class="handoff-row">
                <span class="handoff-key">Branch</span>
                <span class="handoff-value mono">{{ interviewHandoffContext.branch_id }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Waiting State -->
        <div v-if="!reportOutline" class="waiting-placeholder">
          <div class="waiting-animation">
            <div class="waiting-ring"></div>
            <div class="waiting-ring"></div>
            <div class="waiting-ring"></div>
          </div>
          <span class="waiting-text">{{ $t('step5.loadingInteraction') }}</span>
        </div>
      </div>

      <!-- RIGHT PANEL: Interaction Interface -->
      <div class="right-panel" ref="rightPanel">
        <InteractionActionBar
          :active-tab="activeTab"
          :chat-target="chatTarget"
          :profiles="profiles"
          :selected-agent="selectedAgent"
          :show-agent-dropdown="showAgentDropdown"
          @select-report-agent-chat="selectReportAgentChat"
          @toggle-agent-dropdown="toggleAgentDropdown"
          @select-agent="selectAgent"
          @select-survey-tab="selectSurveyTab"
        />

        <!-- Chat Mode -->
        <div v-if="activeTab === 'chat'" class="chat-container">

          <ReportAgentToolsCard v-if="showTechnical && chatTarget === 'report_agent'" />

          <ComparisonSnapshotWorkspace
            v-if="showTechnical && chatTarget === 'report_agent' && isConsumerMode"
            :simulation-id="simulationId"
            :is-consumer-mode="isConsumerMode"
            :comparison-snapshot="comparisonSnapshot"
            @update:branch-comparison="workspaceBranchComparison = $event"
            @update:comparison-snapshot="workspaceComparisonSnapshot = $event"
          />

          <PropagationPathGraph
            v-if="showTechnical && chatTarget === 'report_agent' && isConsumerMode"
            :context="reportContext"
          />

          <ConsumerChatBrief
            v-if="chatTarget === 'report_agent' && isConsumerMode && (consumerQuickPrompts.length > 0 || consumerVocHighlights.length > 0)"
            :quick-prompts="consumerQuickPrompts"
            :voc-highlights="consumerVocHighlights"
            :source-catalog="consumerSourceCatalog"
            :enriched-findings="consumerEnrichedFindings"
            :show-technical="showTechnical"
            @apply-prompt="applyQuickPrompt"
          />

          <AgentProfileCard v-if="chatTarget === 'agent' && selectedAgent" :agent="selectedAgent" />

          <InteractionChatPanel
            ref="chatPanelRef"
            :chat-history="chatHistory"
            v-model:chat-input="chatInput"
            :is-sending="isSending"
            :chat-target="chatTarget"
            :selected-agent="selectedAgent"
            @send-message="sendMessage"
          />
        </div>

        <!-- Consumer Interview Workspace -->
        <div v-if="showTechnical && isConsumerMode" class="consumer-interview-workspace">
          <RepresentativeConsumerInterview
            :simulation-id="simulationId"
            :target-context="interviewHandoffContext"
            @add-log="addLog"
          />
          <VirtualFocusGroupPanel
            :simulation-id="simulationId"
            :target-context="interviewHandoffContext"
            @add-log="addLog"
          />
          <InterviewHistoryPanel
            :simulation-id="simulationId"
            @add-log="addLog"
          />
        </div>

        <InteractionSurveyPanel
          v-if="activeTab === 'survey'"
          :profiles="profiles"
          :selected-agents="selectedAgents"
          v-model:survey-question="surveyQuestion"
          :survey-results="surveyResults"
          :is-surveying="isSurveying"
          @toggle-agent-selection="toggleAgentSelection"
          @select-all-agents="selectAllAgents"
          @clear-agent-selection="clearAgentSelection"
          @submit-survey="submitSurvey"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
// @ts-nocheck
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import { chatWithReport, getReport, getAgentLog } from '../api/report'
import { interviewAgents, getSimulationProfilesRealtime } from '../api/simulation'
import {
  buildConsumerQuickPrompts,
  buildBranchAwarePrompts,
  buildCascadeAwarePrompts,
  buildComparisonAwarePrompts,
  buildReplayAwarePrompts,
  isConsumerProject,
  pickTopVocQuotes,
} from '../utils/consumerMode'
import {
  loadConsumerInterviewHandoff,
  clearConsumerInterviewHandoff,
} from '../utils/consumerResearchActions'
import {
  buildSurveyInterviewRequests,
  extractAgentChatResponse,
  normalizeSurveyResults,
} from '../utils/step5Survey'
import ComparisonSnapshotWorkspace from './consumer/ComparisonSnapshotWorkspace.vue'
import PropagationPathGraph from './consumer/PropagationPathGraph.vue'
import RepresentativeConsumerInterview from './consumer/RepresentativeConsumerInterview.vue'
import VirtualFocusGroupPanel from './consumer/VirtualFocusGroupPanel.vue'
import InterviewHistoryPanel from './consumer/InterviewHistoryPanel.vue'
import AgentProfileCard from './report/AgentProfileCard.vue'
import ConsumerChatBrief from './report/ConsumerChatBrief.vue'
import InteractionActionBar from './report/InteractionActionBar.vue'
import InteractionChatPanel from './report/InteractionChatPanel.vue'
import InteractionSurveyPanel from './report/InteractionSurveyPanel.vue'
import ReportAgentToolsCard from './report/ReportAgentToolsCard.vue'
import ReportSectionsList from './report/ReportSectionsList.vue'

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

// State
const activeTab = ref('chat')
const chatTarget = ref('report_agent')
const showAgentDropdown = ref(false)
const selectedAgent = ref(null)
const selectedAgentIndex = ref(null)

// Chat State
const chatInput = ref('')
const chatHistory = ref([])
const chatHistoryCache = ref({}) // 缓存所有对话记录: { 'report_agent': [], 'agent_0': [], 'agent_1': [], ... }
const isSending = ref(false)
const chatPanelRef = ref(null)

// Survey State
const selectedAgents = ref(new Set())
const surveyQuestion = ref('')
const surveyResults = ref([])
const isSurveying = ref(false)

// Consumer interview handoff state
const interviewHandoffContext = ref(null)

// Report Data
const reportOutline = ref(null)
const generatedSections = ref({})
const collapsedSections = ref(new Set())
const currentSectionIndex = ref(null)
const profiles = ref([])

const isConsumerMode = computed(() => (
  isConsumerProject(props.reportData) || isConsumerProject(props.projectData)
))

const reportContext = computed(() => props.reportData?.report_context || {})

const workspaceBranchComparison = ref(null)
const workspaceComparisonSnapshot = ref(null)

const effectiveComparisonSnapshot = computed(() => props.comparisonSnapshot || workspaceComparisonSnapshot.value)

const consumerQuickPrompts = computed(() => {
  if (!isConsumerMode.value) return []
  const basePrompts = props.reportData?.report_context
    ? buildConsumerQuickPrompts(props.reportData.report_context, t)
    : []
  const branchPrompts = workspaceBranchComparison.value
    ? buildBranchAwarePrompts(workspaceBranchComparison.value, t)
    : []
  const cascadePrompts = props.reportData?.report_context
    ? buildCascadeAwarePrompts(props.reportData.report_context, t)
    : []
  const snapshot = effectiveComparisonSnapshot.value
  const comparisonPrompts = snapshot
    ? buildComparisonAwarePrompts(snapshot, t)
    : []
  const replayPrompts = props.reportData?.report_context
    ? buildReplayAwarePrompts(props.reportData.report_context, t)
    : []
  return [...basePrompts, ...branchPrompts, ...cascadePrompts, ...comparisonPrompts, ...replayPrompts]
})

const consumerVocHighlights = computed(() => (
  isConsumerMode.value && props.reportData?.report_context
    ? pickTopVocQuotes(props.reportData.report_context, t)
    : []
))

const consumerSourceCatalog = computed(() => (
  isConsumerMode.value && props.reportData?.report_context
    ? (props.reportData.report_context.source_catalog || [])
    : []
))

const consumerEnrichedFindings = computed(() => {
  if (!isConsumerMode.value || !props.reportData?.report_context) return []
  const enriched = props.reportData.report_context.enriched_findings || []
  if (enriched.length > 0) {
    return enriched.filter(f => f && f.summary)
  }
  return (props.reportData.report_context.research_findings || []).filter(f => f && f.summary)
})

// Refs
const leftPanel = ref(null)
const rightPanel = ref(null)

// Methods
const addLog = (msg) => {
  emit('add-log', msg)
}

const applyQuickPrompt = (prompt) => {
  chatInput.value = prompt
  activeTab.value = 'chat'
  chatTarget.value = 'report_agent'
  nextTick(() => {
    chatPanelRef.value?.chatInputRef?.focus()
  })
}


const toggleSectionCollapse = (idx) => {
  if (!generatedSections.value[idx + 1]) return
  const newSet = new Set(collapsedSections.value)
  if (newSet.has(idx)) {
    newSet.delete(idx)
  } else {
    newSet.add(idx)
  }
  collapsedSections.value = newSet
}

const selectChatTarget = (target) => {
  chatTarget.value = target
  if (target === 'report_agent') {
    showAgentDropdown.value = false
  }
}

// 保存当前对话记录到缓存
const saveChatHistory = () => {
  if (chatHistory.value.length === 0) return
  
  if (chatTarget.value === 'report_agent') {
    chatHistoryCache.value['report_agent'] = [...chatHistory.value]
  } else if (selectedAgentIndex.value !== null) {
    chatHistoryCache.value[`agent_${selectedAgentIndex.value}`] = [...chatHistory.value]
  }
}

const selectReportAgentChat = () => {
  // 保存当前对话记录
  saveChatHistory()
  
  activeTab.value = 'chat'
  chatTarget.value = 'report_agent'
  selectedAgent.value = null
  selectedAgentIndex.value = null
  showAgentDropdown.value = false
  
  // 恢复 Report Agent 的对话记录
  chatHistory.value = chatHistoryCache.value['report_agent'] || []
}

const selectSurveyTab = () => {
  activeTab.value = 'survey'
  selectedAgent.value = null
  selectedAgentIndex.value = null
  showAgentDropdown.value = false
}

const toggleAgentDropdown = () => {
  showAgentDropdown.value = !showAgentDropdown.value
  if (showAgentDropdown.value) {
    activeTab.value = 'chat'
    chatTarget.value = 'agent'
  }
}

const selectAgent = (agent, idx) => {
  // 保存当前对话记录
  saveChatHistory()
  
  selectedAgent.value = agent
  selectedAgentIndex.value = idx
  chatTarget.value = 'agent'
  showAgentDropdown.value = false
  
  // 恢复该 Agent 的对话记录
  chatHistory.value = chatHistoryCache.value[`agent_${idx}`] || []
  addLog(t('log.selectChatTarget', { name: agent.username }))
}

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

const scrollToBottom = () => {
  nextTick(() => {
    const chatMessages = chatPanelRef.value?.chatMessages
    if (chatMessages) {
      chatMessages.scrollTop = chatMessages.scrollHeight
    }
  })
}

// Survey Methods
const toggleAgentSelection = (idx) => {
  const newSet = new Set(selectedAgents.value)
  if (newSet.has(idx)) {
    newSet.delete(idx)
  } else {
    newSet.add(idx)
  }
  selectedAgents.value = newSet
}

const selectAllAgents = () => {
  const newSet = new Set()
  profiles.value.forEach((_, idx) => newSet.add(idx))
  selectedAgents.value = newSet
}

const clearAgentSelection = () => {
  selectedAgents.value = new Set()
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
      
      logs.forEach(log => {
        if (log.action === 'planning_complete' && log.details?.outline) {
          reportOutline.value = log.details.outline
        }
        
        if (log.action === 'section_complete' && log.section_index < 100 && log.details?.content) {
          generatedSections.value[log.section_index] = log.details.content
        }
      })
      
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
      profiles.value = res.data.profiles || []
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

.main-split-layout:not(.technical-open) .left-panel.report-style {
  width: 42%;
  min-width: 360px;
  padding: 28px 34px 56px;
  background: var(--mc-bg-subtle);
}

.main-split-layout:not(.technical-open) .report-content-wrapper {
  max-width: 620px;
}

.main-split-layout:not(.technical-open) .right-panel {
  flex: 1.2;
}

/* Left Panel - Report Style (与 Step4Report.vue 完全一致) */
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

/* Report Header */
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

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Waiting Placeholder */
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

/* Right Panel - Interaction */
.right-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: var(--mc-bg-subtle);
  overflow: hidden;
}

/* Interaction Header */
.interaction-header {
  padding: 16px 24px;
  border-bottom: 1px solid #E5E7EB;
  background: #FAFAFA;
}

.tab-switcher {
  display: flex;
  gap: 8px;
}

.tab-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  font-size: 13px;
  font-weight: 600;
  color: #6B7280;
  background: transparent;
  border: 1px solid #E5E7EB;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.tab-btn:hover {
  background: #F9FAFB;
  border-color: #D1D5DB;
}

.tab-btn.active {
  background: #1F2937;
  color: #FFFFFF;
  border-color: #1F2937;
}

.tab-btn svg {
  flex-shrink: 0;
}

/* Chat Container */
.chat-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* Target Selector */
.target-selector {
  padding: 16px 24px;
  border-bottom: 1px solid #E5E7EB;
}

.selector-label {
  font-size: 11px;
  font-weight: 600;
  color: #9CA3AF;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 10px;
}

.selector-options {
  display: flex;
  gap: 12px;
}

.target-option {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  font-size: 13px;
  font-weight: 500;
  color: #374151;
  background: #F9FAFB;
  border: 1px solid #E5E7EB;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.target-option:hover {
  border-color: #D1D5DB;
}

.target-option.active {
  background: #1F2937;
  color: #FFFFFF;
  border-color: #1F2937;
}

/* Markdown Styles */
:deep(.md-p) {
  margin: 0 0 12px 0;
}

:deep(.md-h2) {
  font-size: 20px;
  font-weight: 700;
  color: #1F2937;
  margin: 24px 0 12px 0;
}

:deep(.md-h3) {
  font-size: 16px;
  font-weight: 600;
  color: #374151;
  margin: 20px 0 10px 0;
}

:deep(.md-h4) {
  font-size: 14px;
  font-weight: 600;
  color: #4B5563;
  margin: 16px 0 8px 0;
}

:deep(.md-h5) {
  font-size: 13px;
  font-weight: 600;
  color: #6B7280;
  margin: 12px 0 6px 0;
}

:deep(.md-ul), :deep(.md-ol) {
  margin: 12px 0;
  padding-left: 24px;
}

:deep(.md-li), :deep(.md-oli) {
  margin: 6px 0;
}

:deep(.code-block) {
  margin: 12px 0;
  padding: 12px 16px;
  background: #1F2937;
  border-radius: 6px;
  overflow-x: auto;
}

:deep(.code-block code) {
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
  color: #E5E7EB;
}

:deep(.inline-code) {
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
  background: #F3F4F6;
  padding: 2px 6px;
  border-radius: 4px;
  color: #1F2937;
}

:deep(.md-hr) {
  border: none;
  border-top: 1px solid #E5E7EB;
  margin: 24px 0;
}

/* Consumer Interview Handoff Panel */
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

@media (max-width: 980px) {
  .main-split-layout,
  .main-split-layout:not(.technical-open) {
    flex-direction: column;
    overflow-y: auto;
  }

  .left-panel.report-style,
  .main-split-layout:not(.technical-open) .left-panel.report-style {
    width: 100%;
    min-width: 0;
    max-height: 44vh;
    border-right: none;
    border-bottom: 1px solid #E5E7EB;
    padding: 22px 18px 28px;
  }

  .right-panel {
    min-height: 56vh;
  }

}
</style>

<style>
/* English locale: smaller report title */
html[lang="en"] .report-header-block .main-title {
  font-size: 28px;
}
</style>
