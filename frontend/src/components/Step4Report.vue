<template>
  <div class="report-panel">
    <!-- Main Split Layout -->
    <div class="main-split-layout" :class="{ 'technical-open': showTechnical }">
      <!-- LEFT PANEL: Report Style -->
      <div class="left-panel report-style" ref="leftPanel">
        <div v-if="reportOutline" class="report-content-wrapper">
          <!-- Report Header -->
          <ConsumerReportHeader
            :report-id="reportId"
            :title="reportOutline.title"
            :summary="reportOutline.summary"
            :is-consumer-mode="isConsumerMode"
            :consumer-report-tag="consumerContextState.consumerReportTag"
            :consumer-metric-cards="consumerContextState.consumerMetricCards"
            :consumer-report-confidence="consumerContextState.consumerReportConfidence"
            :consumer-replay-alignment="consumerContextState.consumerReplayAlignment"
            :consumer-evidence-validation-summary="consumerContextState.consumerEvidenceValidationSummary"
            :consumer-source-quality-summary="consumerContextState.consumerSourceQualitySummary"
            :consumer-voc-highlights="consumerContextState.consumerVocHighlights"
            :consumer-event-counts="consumerContextState.consumerEventCounts"
            :consumer-risk-findings="consumerContextState.consumerRiskFindings"
            :consumer-clarification-opportunities="consumerContextState.consumerClarificationOpportunities"
            :consumer-causal-chains="consumerContextState.consumerCausalChains"
            :consumer-cascade-metrics="consumerContextState.consumerCascadeMetrics"
            :consumer-persona-group-signals="consumerContextState.consumerPersonaGroupSignals"
            :consumer-research-snapshot="consumerContextState.consumerResearchSnapshot"
            :consumer-source-catalog="consumerContextState.consumerSourceCatalog"
            :consumer-enriched-findings="consumerContextState.consumerEnrichedFindings"
            :consumer-enriched-traces="consumerContextState.consumerEnrichedTraces"
            :consumer-task-type="consumerContextState.consumerTaskType"
            :consumer-packaging-hooks="consumerContextState.consumerPackagingHooks"
            :consumer-packaging-trust-objections="consumerContextState.consumerPackagingTrustObjections"
            :consumer-packaging-confusion-triggers="consumerContextState.consumerPackagingConfusionTriggers"
            :consumer-a-b-winning-variant="consumerContextState.consumerABWinningVariant"
            :consumer-a-b-variant-deltas="consumerContextState.consumerABVariantDeltas"
            :consumer-a-b-persona-divergences="consumerContextState.consumerABPersonaDivergences"
            :consumer-price-acceptable-points="consumerContextState.consumerPriceAcceptablePoints"
            :consumer-price-resisted-points="consumerContextState.consumerPriceResistedPoints"
            :consumer-price-objections="consumerContextState.consumerPriceObjections"
            :consumer-price-context="consumerContextState.consumerPriceContext"
            :branch-comparison-formatted="branchComparisonFormatted"
            :consumer-low-confidence-risk-findings="consumerContextState.consumerLowConfidenceRiskFindings"
            :consumer-findings-requiring-more-evidence="consumerContextState.consumerFindingsRequiringMoreEvidence"
            :consumer-causal-voc-quotes="consumerContextState.consumerCausalVocQuotes"
            :show-technical="showTechnical"
          />

          <SocietyRunSummary
            v-if="isConsumerMode"
            :context="reportContext"
            :show-technical="showTechnical"
          />

          <div v-if="isConsumerMode" class="channel-propagation-stack">
            <ChannelFitPanel :context="reportContext" />
            <ChannelHeatmap :channel-metrics="reportContext.channel_metrics || {}" />
            <PropagationTimeline :context="reportContext" />
          </div>

          <EvidenceGraphPanel
            v-if="showTechnical && isConsumerMode"
            :graph="evidenceGraph"
            :loading="evidenceGraphLoading"
            :error="evidenceGraphError"
          />

          <!-- Research Assets / Comparison Workspace -->
          <ResearchAssetWorkspace
            v-if="showTechnical"
            :project-id="projectId"
            :simulation-id="simulationId"
            :is-consumer-mode="isConsumerMode"
            :is-complete="isComplete"
          >
            <ComparisonWorkspace
              :project-id="projectId"
              :simulation-id="simulationId"
              :is-consumer-mode="isConsumerMode"
              :branch-comparison-formatted="branchComparisonFormatted"
            />
          </ResearchAssetWorkspace>

          <ReportSectionsList
            :sections="reportOutline.sections"
            :generated-sections="generatedSections"
            :collapsed-sections="collapsedSections"
            :current-section-index="currentSectionIndex"
            :is-consumer-mode="isConsumerMode"
            :report-id="reportId"
            :simulation-id="simulationId"
            :branch-id="branchComparisonFormatted?.branchId || ''"
            :disabled="drawerLoading"
            @toggle-section-collapse="toggleSectionCollapse"
            @run-action="handleRunAction"
          />
        </div>

        <!-- Waiting State -->
        <div v-if="!reportOutline" class="waiting-placeholder">
          <div class="waiting-animation">
            <div class="waiting-ring"></div>
            <div class="waiting-ring"></div>
            <div class="waiting-ring"></div>
          </div>
          <span class="waiting-text">正在准备洞察报告...</span>
        </div>
      </div>

      <!-- RIGHT PANEL: Workflow Timeline -->
      <div v-if="showTechnical" class="right-panel" ref="rightPanel">
        <ReportWorkflowPanel
          :is-complete="isComplete"
          :active-step="activeStep"
          :agent-logs="agentLogs"
          :report-outline="reportOutline"
          :completed-sections="completedSections"
          :total-sections="totalSections"
          :elapsed-text="formatElapsedTime"
          :total-tool-calls="totalToolCalls"
          :status-class="statusClass"
          :status-text="statusText"
          :workflow-steps="workflowSteps"
          :display-logs="displayLogs"
          :expanded-logs="expandedLogs"
          :show-raw-result="showRawResult"
          :next-step-label="$t('step4.goToInteraction')"
          @go-to-interaction="goToInteraction"
          @toggle-log-expand="toggleLogExpand"
          @toggle-raw-result="toggleRawResult"
        />
      </div>
    </div>
    <!-- Bottom Console Logs -->
    <div v-if="showTechnical" class="console-logs">
      <div class="log-header">
        <span class="log-title">CONSOLE OUTPUT</span>
        <span class="log-id">{{ reportId || 'NO_REPORT' }}</span>
      </div>
      <div class="log-content" ref="logContent">
        <div class="log-line" v-for="(log, idx) in consoleLogs" :key="idx">
          <span class="log-msg" :class="getLogLevelClass(log)">{{ log }}</span>
        </div>
      </div>
    </div>

    <!-- Consumer Insight Drawer -->
    <ConsumerInsightDrawer
      v-if="showInsightDrawer"
      :result="drawerResult"
      :loading="drawerLoading"
      :error="drawerError"
      @close="closeInsightDrawer"
      @open-handoff="handleOpenHandoff"
    />
  </div>
</template>

<script setup lang="ts">
// @ts-nocheck
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import {
  getAgentLog, getConsoleLog,
} from '../api/report'
import {
  getBranchComparison,
  getReportEvidenceGraph,
} from '../api/consumer'
import {
  loadSelectedBranch,
  formatBranchComparison,
  clearSelectedBranch,
} from '../utils/consumerMode'
import { deriveReportConsumerContext } from '../utils/reportConsumerContext'
import ConsumerReportHeader from './consumer/ConsumerReportHeader.vue'
import ResearchAssetWorkspace from './consumer/ResearchAssetWorkspace.vue'
import ComparisonWorkspace from './consumer/ComparisonWorkspace.vue'
import ConsumerInsightDrawer from './consumer/ConsumerInsightDrawer.vue'
import SocietyRunSummary from './consumer/SocietyRunSummary.vue'
import ChannelFitPanel from './consumer/ChannelFitPanel.vue'
import ChannelHeatmap from './consumer/ChannelHeatmap.vue'
import PropagationTimeline from './consumer/PropagationTimeline.vue'
import EvidenceGraphPanel from './consumer/EvidenceGraphPanel.vue'
import ReportSectionsList from './report/ReportSectionsList.vue'
import ReportWorkflowPanel from './report/ReportWorkflowPanel.vue'
import { useStep4InsightDrawerState } from '../composables/useStep4InsightDrawerState'
import { deriveReportRenderState } from '../utils/reportContent'
import {
  applyAgentLogToReportState,
  applyReportStatePatch,
  buildReportWorkflowSummary,
  formatElapsedTime as formatWorkflowElapsedTime,
  getLogLevelClass,
} from '../utils/reportWorkflow'

const router = useRouter()
const { t } = useI18n()

const props = defineProps({
  reportId: String,
  simulationId: String,
  reportData: Object,
  projectData: Object,
  systemLogs: Array,
  showTechnical: { type: Boolean, default: false }
})

const emit = defineEmits(['add-log', 'update-status'])

// Navigation
const goToInteraction = () => {
  if (props.reportId) {
    router.push({ name: 'Interaction', params: { reportId: props.reportId } })
  }
}

// State
const agentLogs = ref([])
const consoleLogs = ref([])
const agentLogLine = ref(0)
const consoleLogLine = ref(0)
const reportOutline = ref(null)
const currentSectionIndex = ref(null)
const generatedSections = ref({})
const expandedContent = ref(new Set())
const expandedLogs = ref(new Set())
const collapsedSections = ref(new Set())
const isComplete = ref(false)
const startTime = ref(null)
const leftPanel = ref(null)
const rightPanel = ref(null)
const logContent = ref(null)
const showRawResult = reactive({})
const evidenceGraph = ref(null)
const evidenceGraphLoading = ref(false)
const evidenceGraphError = ref('')

const {
  showInsightDrawer,
  drawerResult,
  drawerLoading,
  drawerError,
  closeInsightDrawer,
  handleRunAction,
  handleOpenHandoff,
} = useStep4InsightDrawerState({
  simulationId: computed(() => props.simulationId),
  goToInteraction,
})

const applyReportRenderState = () => {
  const state = deriveReportRenderState(props.reportData)
  if (!state.isComplete) return
  isComplete.value = true
  reportOutline.value = state.outline
  generatedSections.value = state.generatedSections
}

// Branch comparison state
const branchComparisonRaw = ref(null)
const branchComparisonFormatted = computed(() => {
  if (!branchComparisonRaw.value) return null
  return formatBranchComparison(branchComparisonRaw.value, t)
})

const loadEvidenceGraph = async () => {
  if (!props.reportId || !isConsumerMode.value) {
    evidenceGraph.value = null
    evidenceGraphError.value = ''
    evidenceGraphLoading.value = false
    return
  }

  evidenceGraphLoading.value = true
  evidenceGraphError.value = ''
  try {
    const res = await getReportEvidenceGraph(props.reportId)
    if (res.success && res.data) {
      evidenceGraph.value = res.data
    } else {
      evidenceGraph.value = null
      evidenceGraphError.value = res.error || 'Evidence graph unavailable'
    }
  } catch (err) {
    evidenceGraph.value = null
    evidenceGraphError.value = err?.message || 'Evidence graph unavailable'
  } finally {
    evidenceGraphLoading.value = false
  }
}

const projectId = computed(() => props.projectData?.project_id || props.projectData?.projectId || null)

const consumerContextState = computed(() => deriveReportConsumerContext({
  reportData: props.reportData,
  projectData: props.projectData,
  t,
}))
const isConsumerMode = computed(() => consumerContextState.value.isConsumerMode)
const reportContext = computed(() => consumerContextState.value.reportContext)

const loadBranchComparison = async () => {
  if (!props.simulationId || !isConsumerMode.value) {
    branchComparisonRaw.value = null
    return
  }
  const branchId = loadSelectedBranch(props.simulationId)
  if (!branchId) {
    branchComparisonRaw.value = null
    return
  }
  try {
    const res = await getBranchComparison(props.simulationId, branchId)
    if (res.success && res.data) {
      branchComparisonRaw.value = res.data
    } else {
      clearSelectedBranch(props.simulationId)
      branchComparisonRaw.value = null
    }
  } catch (err) {
    console.warn('loadBranchComparison failed:', err)
    clearSelectedBranch(props.simulationId)
    branchComparisonRaw.value = null
  }
}

watch(() => props.simulationId, () => {
  loadBranchComparison()
})

watch([() => props.reportId, isConsumerMode], () => {
  loadEvidenceGraph()
}, { immediate: true })

// Toggle functions
const toggleRawResult = (timestamp, event) => {
  // 保存按钮相对于视口的位置
  const button = event?.target
  const buttonRect = button?.getBoundingClientRect()
  const buttonTopBeforeToggle = buttonRect?.top

  // 切换状态
  showRawResult[timestamp] = !showRawResult[timestamp]

  // 等待 DOM 更新后，调整滚动位置以保持按钮在相同位置
  if (button && buttonTopBeforeToggle !== undefined && rightPanel.value) {
    nextTick(() => {
      const newButtonRect = button.getBoundingClientRect()
      const buttonTopAfterToggle = newButtonRect.top
      const scrollDelta = buttonTopAfterToggle - buttonTopBeforeToggle

      // 调整滚动位置
      rightPanel.value.scrollTop += scrollDelta
    })
  }
}

const toggleSectionContent = (idx) => {
  if (!generatedSections.value[idx + 1]) return
  const newSet = new Set(expandedContent.value)
  if (newSet.has(idx)) {
    newSet.delete(idx)
  } else {
    newSet.add(idx)
  }
  expandedContent.value = newSet
}

const toggleSectionCollapse = (idx) => {
  // 只有已完成的章节才能折叠
  if (!generatedSections.value[idx + 1]) return
  const newSet = new Set(collapsedSections.value)
  if (newSet.has(idx)) {
    newSet.delete(idx)
  } else {
    newSet.add(idx)
  }
  collapsedSections.value = newSet
}

const toggleLogExpand = (log) => {
  const newSet = new Set(expandedLogs.value)
  if (newSet.has(log.timestamp)) {
    newSet.delete(log.timestamp)
  } else {
    newSet.add(log.timestamp)
  }
  expandedLogs.value = newSet
}

// Computed
const workflowSummary = computed(() => buildReportWorkflowSummary({
  isComplete: isComplete.value,
  reportOutline: reportOutline.value,
  generatedSections: generatedSections.value,
  currentSectionIndex: currentSectionIndex.value,
  agentLogs: agentLogs.value,
}))

const statusClass = computed(() => workflowSummary.value.statusClass)
const statusText = computed(() => workflowSummary.value.statusText)
const totalSections = computed(() => workflowSummary.value.totalSections)
const completedSections = computed(() => workflowSummary.value.completedSections)
const totalToolCalls = computed(() => workflowSummary.value.totalToolCalls)
const formatElapsedTime = computed(() => formatWorkflowElapsedTime(startTime.value, agentLogs.value))
const displayLogs = computed(() => agentLogs.value)
const activeStep = computed(() => workflowSummary.value.activeStep)
const workflowSteps = computed(() => workflowSummary.value.workflowSteps)

// Methods
const addLog = (msg) => {
  emit('add-log', msg)
}

const applyAgentLogStatePatch = (patch) => applyReportStatePatch(patch, {
  reportOutline,
  currentSectionIndex,
  generatedSections,
  expandedContent,
  isComplete,
  startTime,
  emitUpdateStatus: status => emit('update-status', status),
  stopPolling,
})

// Polling
let agentLogTimer = null
let consoleLogTimer = null

const fetchAgentLog = async () => {
  if (!props.reportId) return

  try {
    const res = await getAgentLog(props.reportId, agentLogLine.value)

    if (res.success && res.data) {
      const newLogs = res.data.logs || []

      if (newLogs.length > 0) {
        newLogs.forEach(log => {
          agentLogs.value.push(log)

          applyAgentLogStatePatch(applyAgentLogToReportState(log))
        })

        agentLogLine.value = res.data.from_line + newLogs.length

        nextTick(() => {
          if (rightPanel.value) {
            // 如果任务已完成，滚动到顶部；否则滚动到底部跟随最新日志
            if (isComplete.value) {
              rightPanel.value.scrollTop = 0
            } else {
              rightPanel.value.scrollTop = rightPanel.value.scrollHeight
            }
          }
        })
      }
    }
  } catch (err) {
    console.warn('Failed to fetch agent log:', err)
  }
}

const fetchConsoleLog = async () => {
  if (!props.reportId) return

  try {
    const res = await getConsoleLog(props.reportId, consoleLogLine.value)

    if (res.success && res.data) {
      const newLogs = res.data.logs || []

      if (newLogs.length > 0) {
        consoleLogs.value.push(...newLogs)
        consoleLogLine.value = res.data.from_line + newLogs.length

        nextTick(() => {
          if (logContent.value) {
            logContent.value.scrollTop = logContent.value.scrollHeight
          }
        })
      }
    }
  } catch (err) {
    console.warn('Failed to fetch console log:', err)
  }
}

const startPolling = () => {
  if (agentLogTimer || consoleLogTimer) return

  fetchAgentLog()
  fetchConsoleLog()

  agentLogTimer = setInterval(fetchAgentLog, 2000)
  consoleLogTimer = setInterval(fetchConsoleLog, 1500)
}

const stopPolling = () => {
  if (agentLogTimer) {
    clearInterval(agentLogTimer)
    agentLogTimer = null
  }
  if (consoleLogTimer) {
    clearInterval(consoleLogTimer)
    consoleLogTimer = null
  }
}

// Lifecycle
onMounted(() => {
  applyReportRenderState()
  if (props.reportId) {
    addLog(`Report Agent initialized: ${props.reportId}`)
    startPolling()
  }
  loadBranchComparison()
  loadEvidenceGraph()
})

onUnmounted(() => {
  stopPolling()
})

watch(() => props.reportId, (newId) => {
  if (newId) {
    agentLogs.value = []
    consoleLogs.value = []
    agentLogLine.value = 0
    consoleLogLine.value = 0
    reportOutline.value = null
    currentSectionIndex.value = null
    generatedSections.value = {}
    expandedContent.value = new Set()
    expandedLogs.value = new Set()
    collapsedSections.value = new Set()
    isComplete.value = false
    startTime.value = null
    evidenceGraph.value = null
    evidenceGraphError.value = ''
    applyReportRenderState()

    startPolling()
    loadEvidenceGraph()
  }
}, { immediate: true })

watch(() => props.reportData, () => {
  applyReportRenderState()
}, { deep: true })
</script>

<style scoped>
.report-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--mc-bg-canvas);
  font-family: var(--mc-font-body);
  overflow: hidden;
}

/* Main Split Layout */
.main-split-layout {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.main-split-layout:not(.technical-open) .left-panel.report-style {
  width: 100%;
  min-width: 0;
  max-width: 1040px;
  margin: 0 auto;
  border-right: none;
}

/* Left Panel - Report Style */
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
  background: rgba(0, 0, 0, 0.15);
}

.left-panel::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 0, 0, 0.25);
}

/* Slide Content Transition */
.slide-content-enter-active {
  transition: opacity 0.3s ease-out;
}

.slide-content-leave-active {
  transition: opacity 0.2s ease-in;
}

.slide-content-enter-from,
.slide-content-leave-to {
  opacity: 0;
}

.slide-content-enter-to,
.slide-content-leave-from {
  opacity: 1;
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
  color: #9CA3AF;
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

/* Right Panel */
.right-panel {
  flex: 1;
  background: #FFFFFF;
  overflow-y: auto;
  display: flex;
  flex-direction: column;

  /* Functional palette (low saturation, status-based) */
  --wf-border: #E5E7EB;
  --wf-divider: #F3F4F6;

  --wf-active-bg: #FAFAFA;
  --wf-active-border: #1F2937;
  --wf-active-dot: #1F2937;
  --wf-active-text: #1F2937;

  --wf-done-bg: #F9FAFB;
  --wf-done-border: #E5E7EB;
  --wf-done-dot: #10B981;

  --wf-muted-dot: #D1D5DB;
  --wf-todo-text: #9CA3AF;
}

.right-panel::-webkit-scrollbar {
  width: 6px;
}

.right-panel::-webkit-scrollbar-track {
  background: transparent;
}

.right-panel::-webkit-scrollbar-thumb {
  background: transparent;
  border-radius: 3px;
  transition: background 0.3s ease;
}

.right-panel:hover::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.15);
}

.right-panel::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 0, 0, 0.25);
}

.mono {
  font-family: 'JetBrains Mono', monospace;
}

/* ========== Structured Result Display Components ========== */

/* Common Styles - using :deep() for dynamic components */
:deep(.stat-row) {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

:deep(.stat-box) {
  flex: 1;
  background: #FFFFFF;
  border: 1px solid #E5E7EB;
  border-radius: 6px;
  padding: 10px 8px;
  text-align: center;
}

:deep(.stat-box .stat-num) {
  display: block;
  font-size: 20px;
  font-weight: 700;
  color: #111827;
  font-family: 'JetBrains Mono', monospace;
}

:deep(.stat-box .stat-label) {
  display: block;
  font-size: 10px;
  color: #9CA3AF;
  margin-top: 2px;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

:deep(.stat-box.highlight) {
  background: #ECFDF5;
  border-color: #A7F3D0;
}

:deep(.stat-box.highlight .stat-num) {
  color: #059669;
}

:deep(.stat-box.muted) {
  background: #F9FAFB;
  border-color: #E5E7EB;
}

:deep(.stat-box.muted .stat-num) {
  color: #6B7280;
}

:deep(.query-display) {
  background: #F9FAFB;
  padding: 10px 14px;
  border-radius: 6px;
  font-size: 12px;
  color: #374151;
  margin-bottom: 12px;
  border: 1px solid #E5E7EB;
  line-height: 1.5;
}

:deep(.expand-details) {
  background: #FFFFFF;
  border: 1px solid #E5E7EB;
  padding: 8px 14px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 500;
  color: #6B7280;
  cursor: pointer;
  transition: all 0.15s ease;
}

:deep(.expand-details:hover) {
  border-color: #D1D5DB;
  color: #374151;
}

:deep(.detail-content) {
  margin-top: 14px;
  background: #FFFFFF;
  border: 1px solid #E5E7EB;
  border-radius: 8px;
  padding: 14px;
}

:deep(.section-label) {
  font-size: 11px;
  font-weight: 600;
  color: #6B7280;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-bottom: 10px;
  padding-bottom: 6px;
  border-bottom: 1px solid #F3F4F6;
}

/* Facts Section */
:deep(.facts-section) {
  margin-bottom: 14px;
}

:deep(.fact-row) {
  display: flex;
  gap: 10px;
  padding: 8px 0;
  border-bottom: 1px solid #F3F4F6;
}

:deep(.fact-row:last-child) {
  border-bottom: none;
}

:deep(.fact-row.active) {
  background: #ECFDF5;
  margin: 0 -10px;
  padding: 8px 10px;
  border-radius: 6px;
  border-bottom: none;
}

:deep(.fact-idx) {
  min-width: 22px;
  height: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #F3F4F6;
  border-radius: 6px;
  font-size: 10px;
  font-weight: 700;
  color: #6B7280;
  flex-shrink: 0;
}

:deep(.fact-row.active .fact-idx) {
  background: #A7F3D0;
  color: #065F46;
}

:deep(.fact-text) {
  font-size: 12px;
  color: #4B5563;
  line-height: 1.6;
}

/* Entities Section */
:deep(.entities-section) {
  margin-bottom: 14px;
}

:deep(.entity-chips) {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

:deep(.entity-chip) {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: #F9FAFB;
  border: 1px solid #E5E7EB;
  border-radius: 6px;
  padding: 6px 12px;
}

:deep(.chip-name) {
  font-size: 12px;
  font-weight: 500;
  color: #111827;
}

:deep(.chip-type) {
  font-size: 10px;
  color: #9CA3AF;
  background: #E5E7EB;
  padding: 1px 6px;
  border-radius: 3px;
}

/* Relations Section */
:deep(.relations-section) {
  margin-bottom: 14px;
}

:deep(.relation-row) {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 0;
  flex-wrap: wrap;
  border-bottom: 1px solid #F3F4F6;
}

:deep(.relation-row:last-child) {
  border-bottom: none;
}

:deep(.rel-node) {
  font-size: 12px;
  font-weight: 500;
  color: #111827;
  background: #F3F4F6;
  padding: 4px 10px;
  border-radius: 4px;
}

:deep(.rel-edge) {
  font-size: 10px;
  font-weight: 600;
  color: #FFFFFF;
  background: #4F46E5;
  padding: 3px 10px;
  border-radius: 10px;
}

/* ========== Interview Display - Conversation Style ========== */
:deep(.interview-display) {
  padding: 0;
}

/* Header */
:deep(.interview-display .interview-header) {
  padding: 0;
  background: transparent;
  border-bottom: none;
  margin-bottom: 16px;
}

:deep(.interview-display .header-main) {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

:deep(.interview-display .header-title) {
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
  font-weight: 600;
  color: #111827;
  letter-spacing: -0.01em;
}

:deep(.interview-display .header-stats) {
  display: flex;
  align-items: center;
  gap: 6px;
}

:deep(.interview-display .stat-item) {
  display: flex;
  align-items: baseline;
  gap: 4px;
}

:deep(.interview-display .stat-value) {
  font-size: 14px;
  font-weight: 600;
  color: #4F46E5;
  font-family: 'JetBrains Mono', monospace;
}

:deep(.interview-display .stat-label) {
  font-size: 11px;
  color: #9CA3AF;
  text-transform: lowercase;
}

:deep(.interview-display .stat-divider) {
  color: #D1D5DB;
  font-size: 12px;
}

:deep(.interview-display .stat-size) {
  font-size: 11px;
  color: #9CA3AF;
  font-family: 'JetBrains Mono', monospace;
}

:deep(.interview-display .header-topic) {
  margin-top: 4px;
  font-size: 12px;
  color: #6B7280;
  line-height: 1.5;
}

/* Agent Tabs - Card Style */
:deep(.interview-display .agent-tabs) {
  display: flex;
  gap: 8px;
  padding: 0 0 14px 0;
  background: transparent;
  border-bottom: 1px solid #F3F4F6;
  overflow-x: auto;
  overflow-y: hidden;
  scrollbar-width: thin;
  scrollbar-color: #E5E7EB transparent;
}

:deep(.interview-display .agent-tabs::-webkit-scrollbar) {
  height: 4px;
}

:deep(.interview-display .agent-tabs::-webkit-scrollbar-track) {
  background: transparent;
}

:deep(.interview-display .agent-tabs::-webkit-scrollbar-thumb) {
  background: #E5E7EB;
  border-radius: 2px;
}

:deep(.interview-display .agent-tabs::-webkit-scrollbar-thumb:hover) {
  background: #D1D5DB;
}

:deep(.interview-display .agent-tab) {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: #F9FAFB;
  border: 1px solid #E5E7EB;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 500;
  color: #6B7280;
  cursor: pointer;
  transition: all 0.15s ease;
  white-space: nowrap;
}

:deep(.interview-display .agent-tab:hover) {
  background: #F3F4F6;
  border-color: #D1D5DB;
  color: #374151;
}

:deep(.interview-display .agent-tab.active) {
  background: linear-gradient(135deg, #EEF2FF 0%, #E0E7FF 100%);
  border-color: #A5B4FC;
  color: #4338CA;
  box-shadow: 0 1px 2px rgba(99, 102, 241, 0.1);
}

:deep(.interview-display .tab-avatar) {
  width: 18px;
  height: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #E5E7EB;
  color: #6B7280;
  font-size: 10px;
  font-weight: 700;
  border-radius: 50%;
  flex-shrink: 0;
}

:deep(.interview-display .agent-tab:hover .tab-avatar) {
  background: #D1D5DB;
}

:deep(.interview-display .agent-tab.active .tab-avatar) {
  background: #6366F1;
  color: #FFFFFF;
}

:deep(.interview-display .tab-name) {
  max-width: 100px;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Interview Detail */
:deep(.interview-display .interview-detail) {
  padding: 12px 0;
  background: transparent;
}

/* Agent Profile - No card */
:deep(.interview-display .agent-profile) {
  display: flex;
  gap: 12px;
  padding: 0;
  background: transparent;
  border: none;
  margin-bottom: 16px;
}

:deep(.interview-display .profile-avatar) {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #E5E7EB;
  color: #6B7280;
  font-size: 14px;
  font-weight: 600;
  border-radius: 50%;
  flex-shrink: 0;
}

:deep(.interview-display .profile-info) {
  flex: 1;
  min-width: 0;
}

:deep(.interview-display .profile-name) {
  font-size: 13px;
  font-weight: 600;
  color: #111827;
  margin-bottom: 2px;
}

:deep(.interview-display .profile-role) {
  font-size: 11px;
  color: #6B7280;
  margin-bottom: 4px;
}

:deep(.interview-display .profile-bio) {
  font-size: 11px;
  color: #9CA3AF;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* Selection Reason - 选择理由 */
:deep(.interview-display .selection-reason) {
  background: #F8FAFC;
  border: 1px solid #E2E8F0;
  border-radius: 8px;
  padding: 12px 14px;
  margin-bottom: 16px;
}

:deep(.interview-display .reason-label) {
  font-size: 11px;
  font-weight: 600;
  color: #64748B;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  margin-bottom: 6px;
}

:deep(.interview-display .reason-content) {
  font-size: 12px;
  color: #475569;
  line-height: 1.6;
}

/* Q&A Thread - Clean list */
:deep(.interview-display .qa-thread) {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

:deep(.interview-display .qa-pair) {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 0;
  background: transparent;
  border: none;
  border-radius: 0;
}

:deep(.interview-display .qa-question),
:deep(.interview-display .qa-answer) {
  display: flex;
  gap: 12px;
}

:deep(.interview-display .qa-badge) {
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  font-weight: 700;
  border-radius: 4px;
  flex-shrink: 0;
}

:deep(.interview-display .q-badge) {
  background: transparent;
  color: #9CA3AF;
  border: 1px solid #E5E7EB;
}

:deep(.interview-display .a-badge) {
  background: #4F46E5;
  color: #FFFFFF;
  border: 1px solid #4F46E5;
}

:deep(.interview-display .qa-content) {
  flex: 1;
  min-width: 0;
}

:deep(.interview-display .qa-sender) {
  font-size: 11px;
  font-weight: 600;
  color: #9CA3AF;
  margin-bottom: 4px;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

:deep(.interview-display .qa-text) {
  font-size: 13px;
  color: #374151;
  line-height: 1.6;
}

:deep(.interview-display .qa-answer) {
  background: transparent;
  padding: 0;
  border: none;
  margin-top: 0;
}

:deep(.interview-display .answer-placeholder) {
  opacity: 0.6;
}

:deep(.interview-display .placeholder-text) {
  font-style: italic;
  color: #9CA3AF;
}

:deep(.interview-display .qa-answer-header) {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

/* Platform Switch */
:deep(.interview-display .platform-switch) {
  display: flex;
  gap: 2px;
  background: transparent;
  padding: 0;
  border-radius: 0;
}

:deep(.interview-display .platform-btn) {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 2px 6px;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 500;
  color: #9CA3AF;
  cursor: pointer;
  transition: all 0.15s ease;
}

:deep(.interview-display .platform-btn:hover) {
  color: #6B7280;
}

:deep(.interview-display .platform-btn.active) {
  background: transparent;
  color: #4F46E5;
  border-color: #E5E7EB;
  box-shadow: none;
}

:deep(.interview-display .platform-icon) {
  flex-shrink: 0;
}

:deep(.interview-display .answer-text) {
  font-size: 13px;
  color: #111827;
  line-height: 1.6;
}

:deep(.interview-display .answer-text strong) {
  color: #111827;
  font-weight: 600;
}

:deep(.interview-display .expand-answer-btn) {
  display: inline-block;
  margin-top: 8px;
  padding: 0;
  background: transparent;
  border: none;
  border-bottom: 1px dotted #D1D5DB;
  border-radius: 0;
  font-size: 11px;
  font-weight: 500;
  color: #9CA3AF;
  cursor: pointer;
  transition: all 0.15s ease;
}

:deep(.interview-display .expand-answer-btn:hover) {
  background: transparent;
  color: #6B7280;
  border-bottom-style: solid;
}

/* Quotes Section - Clean list */
:deep(.interview-display .quotes-section) {
  background: transparent;
  border: none;
  border-top: 1px solid #F3F4F6;
  border-radius: 0;
  padding: 16px 0 0 0;
  margin-top: 16px;
}

:deep(.interview-display .quotes-header) {
  font-size: 11px;
  font-weight: 600;
  color: #9CA3AF;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-bottom: 12px;
}

:deep(.interview-display .quotes-list) {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

:deep(.interview-display .quote-item) {
  margin: 0;
  padding: 10px 12px;
  background: #FFFFFF;
  border: 1px solid #E5E7EB;
  border-radius: 6px;
  font-size: 12px;
  font-style: italic;
  color: #4B5563;
  line-height: 1.5;
}

/* Summary Section */
:deep(.interview-display .summary-section) {
  margin-top: 20px;
  padding: 16px 0 0 0;
  background: transparent;
  border: none;
  border-top: 1px solid #F3F4F6;
  border-radius: 0;
}

:deep(.interview-display .summary-header) {
  font-size: 11px;
  font-weight: 600;
  color: #9CA3AF;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-bottom: 8px;
}

:deep(.interview-display .summary-content) {
  font-size: 13px;
  color: #374151;
  line-height: 1.6;
}

/* Markdown styles in summary */
:deep(.interview-display .summary-content h2),
:deep(.interview-display .summary-content h3),
:deep(.interview-display .summary-content h4),
:deep(.interview-display .summary-content h5) {
  margin: 12px 0 8px 0;
  font-weight: 600;
  color: #111827;
}

:deep(.interview-display .summary-content h2) {
  font-size: 15px;
}

:deep(.interview-display .summary-content h3) {
  font-size: 14px;
}

:deep(.interview-display .summary-content h4),
:deep(.interview-display .summary-content h5) {
  font-size: 13px;
}

:deep(.interview-display .summary-content p) {
  margin: 8px 0;
}

:deep(.interview-display .summary-content strong) {
  font-weight: 600;
  color: #111827;
}

:deep(.interview-display .summary-content em) {
  font-style: italic;
}

:deep(.interview-display .summary-content ul),
:deep(.interview-display .summary-content ol) {
  margin: 8px 0;
  padding-left: 20px;
}

:deep(.interview-display .summary-content li) {
  margin: 4px 0;
}

:deep(.interview-display .summary-content blockquote) {
  margin: 8px 0;
  padding-left: 12px;
  border-left: 3px solid #E5E7EB;
  color: #6B7280;
  font-style: italic;
}

/* Markdown styles in quotes */
:deep(.interview-display .quote-item strong) {
  font-weight: 600;
  color: #374151;
}

:deep(.interview-display .quote-item em) {
  font-style: italic;
}

/* ========== Enhanced Insight Display Styles ========== */
:deep(.insight-display) {
  padding: 0;
}

:deep(.insight-header) {
  padding: 12px 16px;
  background: linear-gradient(135deg, var(--mc-accent-wash) 0%, var(--mc-bg-subtle) 100%);
  border-radius: 8px 8px 0 0;
  border: 1px solid var(--mc-border);
  border-bottom: none;
}

:deep(.insight-header .header-main) {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

:deep(.insight-header .header-title) {
  font-size: 14px;
  font-weight: 700;
  color: var(--mc-accent);
}

:deep(.insight-header .header-stats) {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
}

:deep(.insight-header .stat-item) {
  display: flex;
  align-items: baseline;
  gap: 2px;
}

:deep(.insight-header .stat-value) {
  font-family: 'JetBrains Mono', monospace;
  font-weight: 700;
  color: var(--mc-accent);
}

:deep(.insight-header .stat-label) {
  color: var(--mc-text-tertiary);
  font-size: 10px;
}

:deep(.insight-header .stat-divider) {
  color: var(--mc-border-strong);
  margin: 0 4px;
}

:deep(.insight-header .stat-size) {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  color: #9CA3AF;
}

:deep(.insight-header .header-topic) {
  font-size: 13px;
  color: var(--mc-text-secondary);
  line-height: 1.5;
}

:deep(.insight-header .header-scenario) {
  margin-top: 6px;
  font-size: 11px;
  color: var(--mc-accent);
}

:deep(.insight-header .scenario-label) {
  font-weight: 600;
}

:deep(.insight-tabs) {
  display: flex;
  gap: 2px;
  padding: 8px 12px;
  background: var(--mc-bg-subtle);
  border: 1px solid var(--mc-border);
  border-top: none;
}

:deep(.insight-tab) {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 10px;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 500;
  color: #6B7280;
  cursor: pointer;
  transition: all 0.15s ease;
}

:deep(.insight-tab:hover) {
  background: #F3F4F6;
  color: #374151;
}

:deep(.insight-tab.active) {
  background: var(--mc-surface);
  color: var(--mc-accent);
  border-color: var(--mc-border-strong);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

:deep(.insight-content) {
  padding: 12px;
  background: #FFFFFF;
  border: 1px solid #E5E7EB;
  border-top: none;
  border-radius: 0 0 8px 8px;
}

:deep(.insight-display .panel-header) {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid #F3F4F6;
}

:deep(.insight-display .panel-title) {
  font-size: 12px;
  font-weight: 600;
  color: #374151;
}

:deep(.insight-display .panel-count) {
  font-size: 10px;
  color: #9CA3AF;
}

:deep(.insight-display .facts-list),
:deep(.insight-display .relations-list),
:deep(.insight-display .subqueries-list) {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

:deep(.insight-display .entities-grid) {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

:deep(.insight-display .fact-item) {
  display: flex;
  gap: 10px;
  padding: 10px 12px;
  background: #F9FAFB;
  border: 1px solid #E5E7EB;
  border-radius: 6px;
}

:deep(.insight-display .fact-number) {
  flex-shrink: 0;
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #E5E7EB;
  border-radius: 50%;
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  font-weight: 700;
  color: #6B7280;
}

:deep(.insight-display .fact-content) {
  flex: 1;
  font-size: 12px;
  color: #374151;
  line-height: 1.6;
}

/* Entity Tag Styles - Compact multi-column layout */
:deep(.insight-display .entity-tag) {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  background: #F9FAFB;
  border: 1px solid #E5E7EB;
  border-radius: 6px;
  cursor: default;
  transition: all 0.15s ease;
}

:deep(.insight-display .entity-tag:hover) {
  background: #F3F4F6;
  border-color: #D1D5DB;
}

:deep(.insight-display .entity-tag .entity-name) {
  font-size: 12px;
  font-weight: 500;
  color: #111827;
}

:deep(.insight-display .entity-tag .entity-type) {
  font-size: 9px;
  color: var(--mc-accent);
  background: var(--mc-accent-wash);
  padding: 1px 4px;
  border-radius: 3px;
}

:deep(.insight-display .entity-tag .entity-fact-count) {
  font-size: 9px;
  color: #9CA3AF;
  margin-left: 2px;
}

/* Legacy entity card styles for backwards compatibility */
:deep(.insight-display .entity-card) {
  padding: 12px;
  background: #F9FAFB;
  border: 1px solid #E5E7EB;
  border-radius: 8px;
}

:deep(.insight-display .entity-header) {
  display: flex;
  align-items: center;
  gap: 10px;
}

:deep(.insight-display .entity-info) {
  flex: 1;
}

:deep(.insight-display .entity-card .entity-name) {
  font-size: 13px;
  font-weight: 600;
  color: #111827;
}

:deep(.insight-display .entity-card .entity-type) {
  font-size: 10px;
  color: var(--mc-accent);
  background: var(--mc-accent-wash);
  padding: 2px 6px;
  border-radius: 4px;
  display: inline-block;
  margin-top: 2px;
}

:deep(.insight-display .entity-card .entity-fact-count) {
  font-size: 10px;
  color: #9CA3AF;
  background: #F3F4F6;
  padding: 2px 6px;
  border-radius: 4px;
}

:deep(.insight-display .entity-summary) {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid #E5E7EB;
  font-size: 11px;
  color: #6B7280;
  line-height: 1.5;
}

/* Relation Item Styles */
:deep(.insight-display .relation-item) {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  background: #F9FAFB;
  border: 1px solid #E5E7EB;
  border-radius: 6px;
}

:deep(.insight-display .rel-source),
:deep(.insight-display .rel-target) {
  padding: 4px 8px;
  background: #FFFFFF;
  border: 1px solid #D1D5DB;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
  color: #374151;
}

:deep(.insight-display .rel-arrow) {
  display: flex;
  align-items: center;
  gap: 4px;
  flex: 1;
}

:deep(.insight-display .rel-line) {
  flex: 1;
  height: 1px;
  background: #D1D5DB;
}

:deep(.insight-display .rel-label) {
  padding: 2px 6px;
  background: var(--mc-accent-wash);
  border-radius: 4px;
  font-size: 10px;
  font-weight: 500;
  color: var(--mc-accent);
  white-space: nowrap;
}

/* Sub-query Styles */
:deep(.insight-display .subquery-item) {
  display: flex;
  gap: 10px;
  padding: 10px 12px;
  background: #F9FAFB;
  border: 1px solid #E5E7EB;
  border-radius: 6px;
}

:deep(.insight-display .subquery-number) {
  flex-shrink: 0;
  padding: 2px 6px;
  background: var(--mc-accent);
  border-radius: 4px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  font-weight: 700;
  color: #FFFFFF;
}

:deep(.insight-display .subquery-text) {
  font-size: 12px;
  color: #374151;
  line-height: 1.5;
}

/* Expand Button */
:deep(.insight-display .expand-btn),
:deep(.panorama-display .expand-btn),
:deep(.quick-search-display .expand-btn) {
  display: block;
  width: 100%;
  margin-top: 12px;
  padding: 8px 12px;
  background: #F9FAFB;
  border: 1px solid #E5E7EB;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 500;
  color: #6B7280;
  cursor: pointer;
  transition: all 0.15s ease;
  text-align: center;
}

:deep(.insight-display .expand-btn:hover),
:deep(.panorama-display .expand-btn:hover),
:deep(.quick-search-display .expand-btn:hover) {
  background: #F3F4F6;
  color: #374151;
  border-color: #D1D5DB;
}

/* Empty State */
:deep(.insight-display .empty-state),
:deep(.panorama-display .empty-state),
:deep(.quick-search-display .empty-state) {
  padding: 24px;
  text-align: center;
  font-size: 12px;
  color: #9CA3AF;
}

/* ========== Enhanced Panorama Display Styles ========== */
:deep(.panorama-display) {
  padding: 0;
}

:deep(.panorama-header) {
  padding: 12px 16px;
  background: linear-gradient(135deg, #EFF6FF 0%, #DBEAFE 100%);
  border-radius: 8px 8px 0 0;
  border: 1px solid #93C5FD;
  border-bottom: none;
}

:deep(.panorama-header .header-main) {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

:deep(.panorama-header .header-title) {
  font-size: 14px;
  font-weight: 700;
  color: #1D4ED8;
}

:deep(.panorama-header .header-stats) {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
}

:deep(.panorama-header .stat-item) {
  display: flex;
  align-items: baseline;
  gap: 2px;
}

:deep(.panorama-header .stat-value) {
  font-family: 'JetBrains Mono', monospace;
  font-weight: 700;
  color: var(--mc-status-info);
}

:deep(.panorama-header .stat-label) {
  color: var(--mc-text-tertiary);
  font-size: 10px;
}

:deep(.panorama-header .stat-divider) {
  color: var(--mc-border-strong);
  margin: 0 4px;
}

:deep(.panorama-header .stat-size) {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  color: #9CA3AF;
}

:deep(.panorama-header .header-topic) {
  font-size: 13px;
  color: var(--mc-text-secondary);
  line-height: 1.5;
}

:deep(.panorama-tabs) {
  display: flex;
  gap: 2px;
  padding: 8px 12px;
  background: var(--mc-bg-subtle);
  border: 1px solid var(--mc-border);
  border-top: none;
}

:deep(.panorama-tab) {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 10px;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 500;
  color: var(--mc-text-secondary);
  cursor: pointer;
  transition: all 0.15s ease;
}

:deep(.panorama-tab:hover) {
  background: var(--mc-surface-muted);
  color: var(--mc-text-primary);
}

:deep(.panorama-tab.active) {
  background: var(--mc-surface);
  color: var(--mc-status-info);
  border-color: var(--mc-border-strong);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

:deep(.panorama-content) {
  padding: 12px;
  background: var(--mc-surface);
  border: 1px solid var(--mc-border);
  border-top: none;
  border-radius: 0 0 8px 8px;
}

:deep(.panorama-display .panel-header) {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid #F3F4F6;
}

:deep(.panorama-display .panel-title) {
  font-size: 12px;
  font-weight: 600;
  color: #374151;
}

:deep(.panorama-display .panel-count) {
  font-size: 10px;
  color: #9CA3AF;
}

:deep(.panorama-display .facts-list) {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

:deep(.panorama-display .fact-item) {
  display: flex;
  gap: 10px;
  padding: 10px 12px;
  background: #F9FAFB;
  border: 1px solid #E5E7EB;
  border-radius: 6px;
}

:deep(.panorama-display .fact-item.active) {
  background: #F9FAFB;
  border-color: #E5E7EB;
}

:deep(.panorama-display .fact-item.historical) {
  background: #F9FAFB;
  border-color: #E5E7EB;
}

:deep(.panorama-display .fact-number) {
  flex-shrink: 0;
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #E5E7EB;
  border-radius: 50%;
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  font-weight: 700;
  color: #6B7280;
}

:deep(.panorama-display .fact-item.active .fact-number) {
  background: #E5E7EB;
  color: #6B7280;
}

:deep(.panorama-display .fact-item.historical .fact-number) {
  background: #9CA3AF;
  color: #FFFFFF;
}

:deep(.panorama-display .fact-content) {
  flex: 1;
  font-size: 12px;
  color: #374151;
  line-height: 1.6;
}

:deep(.panorama-display .fact-time) {
  display: block;
  font-size: 10px;
  color: #9CA3AF;
  margin-bottom: 4px;
  font-family: 'JetBrains Mono', monospace;
}

:deep(.panorama-display .fact-text) {
  display: block;
}

/* Entities Grid */
:deep(.panorama-display .entities-grid) {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

:deep(.panorama-display .entity-tag) {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  background: #F9FAFB;
  border: 1px solid #E5E7EB;
  border-radius: 6px;
}

:deep(.panorama-display .entity-name) {
  font-size: 12px;
  font-weight: 500;
  color: #374151;
}

:deep(.panorama-display .entity-type) {
  font-size: 10px;
  color: var(--mc-status-info);
  background: var(--mc-status-info-bg);
  padding: 2px 6px;
  border-radius: 4px;
}

/* ========== Enhanced Quick Search Display Styles ========== */
:deep(.quick-search-display) {
  padding: 0;
}

:deep(.quicksearch-header) {
  padding: 12px 16px;
  background: linear-gradient(135deg, #FFF7ED 0%, #FFEDD5 100%);
  border-radius: 8px 8px 0 0;
  border: 1px solid #FDBA74;
  border-bottom: none;
}

:deep(.quicksearch-header .header-main) {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

:deep(.quicksearch-header .header-title) {
  font-size: 14px;
  font-weight: 700;
  color: #C2410C;
}

:deep(.quicksearch-header .header-stats) {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
}

:deep(.quicksearch-header .stat-item) {
  display: flex;
  align-items: baseline;
  gap: 2px;
}

:deep(.quicksearch-header .stat-value) {
  font-family: 'JetBrains Mono', monospace;
  font-weight: 700;
  color: #EA580C;
}

:deep(.quicksearch-header .stat-label) {
  color: #FB923C;
  font-size: 10px;
}

:deep(.quicksearch-header .stat-divider) {
  color: #FDBA74;
  margin: 0 4px;
}

:deep(.quicksearch-header .stat-size) {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  color: #9CA3AF;
}

:deep(.quicksearch-header .header-query) {
  font-size: 13px;
  color: #9A3412;
  line-height: 1.5;
}

:deep(.quicksearch-header .query-label) {
  font-weight: 600;
}

:deep(.quicksearch-tabs) {
  display: flex;
  gap: 2px;
  padding: 8px 12px;
  background: #FAFAFA;
  border: 1px solid #E5E7EB;
  border-top: none;
}

:deep(.quicksearch-tab) {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 10px;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 500;
  color: #6B7280;
  cursor: pointer;
  transition: all 0.15s ease;
}

:deep(.quicksearch-tab:hover) {
  background: #F3F4F6;
  color: #374151;
}

:deep(.quicksearch-tab.active) {
  background: #FFFFFF;
  color: #EA580C;
  border-color: #FDBA74;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

:deep(.quicksearch-content) {
  padding: 12px;
  background: #FFFFFF;
  border: 1px solid #E5E7EB;
  border-top: none;
  border-radius: 0 0 8px 8px;
}

/* When there are no tabs, content connects directly to header */
:deep(.quicksearch-content.no-tabs) {
  border-top: none;
}

:deep(.quick-search-display .panel-header) {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid #F3F4F6;
}

:deep(.quick-search-display .panel-title) {
  font-size: 12px;
  font-weight: 600;
  color: #374151;
}

:deep(.quick-search-display .panel-count) {
  font-size: 10px;
  color: #9CA3AF;
}

:deep(.quick-search-display .facts-list) {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

:deep(.quick-search-display .fact-item) {
  display: flex;
  gap: 10px;
  padding: 10px 12px;
  background: #F9FAFB;
  border: 1px solid #E5E7EB;
  border-radius: 6px;
}

:deep(.quick-search-display .fact-item.active) {
  background: #F9FAFB;
  border-color: #E5E7EB;
}

:deep(.quick-search-display .fact-number) {
  flex-shrink: 0;
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #E5E7EB;
  border-radius: 50%;
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  font-weight: 700;
  color: #6B7280;
}

:deep(.quick-search-display .fact-item.active .fact-number) {
  background: #E5E7EB;
  color: #6B7280;
}

:deep(.quick-search-display .fact-content) {
  flex: 1;
  font-size: 12px;
  color: #374151;
  line-height: 1.6;
}

/* Edges Panel */
:deep(.quick-search-display .edges-list) {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

:deep(.quick-search-display .edge-item) {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  background: #F9FAFB;
  border: 1px solid #E5E7EB;
  border-radius: 6px;
}

:deep(.quick-search-display .edge-source),
:deep(.quick-search-display .edge-target) {
  padding: 4px 8px;
  background: #FFFFFF;
  border: 1px solid #D1D5DB;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
  color: #374151;
}

:deep(.quick-search-display .edge-arrow) {
  display: flex;
  align-items: center;
  gap: 4px;
  flex: 1;
}

:deep(.quick-search-display .edge-line) {
  flex: 1;
  height: 1px;
  background: #D1D5DB;
}

:deep(.quick-search-display .edge-label) {
  padding: 2px 6px;
  background: #FFEDD5;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 500;
  color: #C2410C;
  white-space: nowrap;
}

/* Nodes Grid */
:deep(.quick-search-display .nodes-grid) {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

:deep(.quick-search-display .node-tag) {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  background: #F9FAFB;
  border: 1px solid #E5E7EB;
  border-radius: 6px;
}

:deep(.quick-search-display .node-name) {
  font-size: 12px;
  font-weight: 500;
  color: #374151;
}

:deep(.quick-search-display .node-type) {
  font-size: 10px;
  color: #EA580C;
  background: #FFEDD5;
  padding: 2px 6px;
  border-radius: 4px;
}

/* Console Logs - 与 Step3Simulation.vue 保持一致 */
.console-logs {
  background: #211b14;
  color: #eadfcd;
  padding: 16px;
  font-family: 'JetBrains Mono', monospace;
  border-top: 1px solid rgba(255, 253, 250, 0.12);
  flex-shrink: 0;
}

.log-header {
  display: flex;
  justify-content: space-between;
  border-bottom: 1px solid rgba(255, 253, 250, 0.14);
  padding-bottom: 8px;
  margin-bottom: 8px;
  font-size: 10px;
  color: rgba(234, 223, 205, 0.58);
}

.log-title {
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.log-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
  height: 100px;
  overflow-y: auto;
  padding-right: 4px;
}

.log-content::-webkit-scrollbar { width: 4px; }
.log-content::-webkit-scrollbar-thumb { background: #333; border-radius: 2px; }

.log-line {
  font-size: 11px;
  line-height: 1.5;
}

.log-msg {
  color: #BBB;
  word-break: break-all;
}

.log-msg.error { color: #EF5350; }
.log-msg.warning { color: #FFA726; }
.log-msg.success { color: #66BB6A; }

</style>

<style>
/* English locale: smaller report title */
html[lang="en"] .report-header-block .main-title {
  font-size: 28px;
}
</style>
