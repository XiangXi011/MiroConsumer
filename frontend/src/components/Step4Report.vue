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
import { useStep4BranchComparisonState } from '../composables/useStep4BranchComparisonState'
import { useStep4EvidenceGraphState } from '../composables/useStep4EvidenceGraphState'
import { useStep4InsightDrawerState } from '../composables/useStep4InsightDrawerState'
import { useStep4ReportPollingState } from '../composables/useStep4ReportPollingState'
import { useStep4ReportRenderState } from '../composables/useStep4ReportRenderState'
import {
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
const expandedLogs = ref(new Set())
const leftPanel = ref(null)
const rightPanel = ref(null)
const logContent = ref(null)
const showRawResult = reactive({})

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

const {
  reportOutline,
  currentSectionIndex,
  generatedSections,
  expandedContent,
  collapsedSections,
  isComplete,
  startTime,
  applyReportRenderState,
  resetReportRenderState,
  toggleSectionContent,
  toggleSectionCollapse,
  applyAgentLogStatePatch,
} = useStep4ReportRenderState({
  emitUpdateStatus: status => emit('update-status', status),
  stopPolling: () => stopPolling(),
})

const {
  agentLogs,
  consoleLogs,
  resetPollingState,
  startPolling,
  stopPolling,
} = useStep4ReportPollingState({
  reportId: computed(() => props.reportId),
  isComplete,
  rightPanel,
  logContent,
  applyAgentLogStatePatch,
})

const projectId = computed(() => props.projectData?.project_id || props.projectData?.projectId || null)

const consumerContextState = computed(() => deriveReportConsumerContext({
  reportData: props.reportData,
  projectData: props.projectData,
  t,
}))
const isConsumerMode = computed(() => consumerContextState.value.isConsumerMode)
const reportContext = computed(() => consumerContextState.value.reportContext)

const {
  branchComparisonFormatted,
  loadBranchComparison,
} = useStep4BranchComparisonState({
  simulationId: computed(() => props.simulationId),
  isConsumerMode,
  t,
})

const {
  evidenceGraph,
  evidenceGraphLoading,
  evidenceGraphError,
  resetEvidenceGraph,
  loadEvidenceGraph,
} = useStep4EvidenceGraphState({
  reportId: computed(() => props.reportId),
  isConsumerMode,
})

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

// Lifecycle
onMounted(() => {
  applyReportRenderState(props.reportData)
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
    resetPollingState()
    expandedLogs.value = new Set()
    resetReportRenderState()
    resetEvidenceGraph()
    applyReportRenderState(props.reportData)

    startPolling()
    loadEvidenceGraph()
  }
}, { immediate: true })

watch(() => props.reportData, () => {
  applyReportRenderState(props.reportData)
}, { deep: true })
</script>

<style scoped src="./report/Step4Report.scoped.css"></style>
<style src="./report/Step4Report.global.css"></style>
