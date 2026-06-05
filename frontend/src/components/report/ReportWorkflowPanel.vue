<template>
  <div class="report-workflow-panel">
    <div class="panel-header" :class="`panel-header--${activeStep.status}`" v-if="!isComplete">
      <span class="header-dot" v-if="activeStep.status === 'active'"></span>
      <span class="header-index mono">{{ activeStep.noLabel }}</span>
      <span class="header-title">{{ activeStep.title }}</span>
      <span class="header-meta mono" v-if="activeStep.meta">{{ activeStep.meta }}</span>
    </div>

    <div class="workflow-overview" v-if="agentLogs.length > 0 || reportOutline">
      <div class="workflow-metrics">
        <div class="metric">
          <span class="metric-label">Sections</span>
          <span class="metric-value mono">{{ completedSections }}/{{ totalSections }}</span>
        </div>
        <div class="metric">
          <span class="metric-label">Elapsed</span>
          <span class="metric-value mono">{{ elapsedText }}</span>
        </div>
        <div class="metric">
          <span class="metric-label">Tools</span>
          <span class="metric-value mono">{{ totalToolCalls }}</span>
        </div>
        <div class="metric metric-right">
          <span class="metric-pill" :class="`pill--${statusClass}`">{{ statusText }}</span>
        </div>
      </div>

      <div class="workflow-steps" v-if="workflowSteps.length > 0">
        <div
          v-for="(step, sidx) in workflowSteps"
          :key="step.key"
          class="wf-step"
          :class="`wf-step--${step.status}`"
        >
          <div class="wf-step-connector">
            <div class="wf-step-dot"></div>
            <div class="wf-step-line" v-if="sidx < workflowSteps.length - 1"></div>
          </div>

          <div class="wf-step-content">
            <div class="wf-step-title-row">
              <span class="wf-step-index mono">{{ step.noLabel }}</span>
              <span class="wf-step-title">{{ step.title }}</span>
              <span class="wf-step-meta mono" v-if="step.meta">{{ step.meta }}</span>
            </div>
          </div>
        </div>
      </div>

      <button v-if="isComplete" class="next-step-btn" @click="$emit('go-to-interaction')">
        <span>{{ nextStepLabel }}</span>
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="5" y1="12" x2="19" y2="12"></line>
          <polyline points="12 5 19 12 12 19"></polyline>
        </svg>
      </button>

      <div class="workflow-divider"></div>
    </div>

    <div class="workflow-timeline">
      <TransitionGroup name="timeline-item">
        <div
          v-for="(log, idx) in displayLogs"
          :key="log.timestamp + '-' + idx"
          class="timeline-item"
          :class="getTimelineItemClass(log, idx, displayLogs.length, isComplete)"
        >
          <div class="timeline-connector">
            <div class="connector-dot" :class="getConnectorClass(log, idx, displayLogs.length, isComplete)"></div>
            <div class="connector-line" v-if="idx < displayLogs.length - 1"></div>
          </div>

          <div class="timeline-content">
            <div class="timeline-header">
              <span class="action-label">{{ getActionLabel(log.action) }}</span>
              <span class="action-time">{{ formatTime(log.timestamp) }}</span>
            </div>

            <div class="timeline-body" :class="{ collapsed: isLogCollapsed(log) }" @click="emitToggleLogExpand(log)">
              <template v-if="log.action === 'report_start'">
                <div class="info-row">
                  <span class="info-key">Simulation</span>
                  <span class="info-val mono">{{ log.details?.simulation_id }}</span>
                </div>
                <div class="info-row" v-if="log.details?.simulation_requirement">
                  <span class="info-key">Requirement</span>
                  <span class="info-val">{{ log.details.simulation_requirement }}</span>
                </div>
              </template>

              <template v-if="log.action === 'planning_start'">
                <div class="status-message planning">{{ log.details?.message }}</div>
              </template>
              <template v-if="log.action === 'planning_complete'">
                <div class="status-message success">{{ log.details?.message }}</div>
                <div class="outline-badge" v-if="log.details?.outline">
                  {{ log.details.outline.sections?.length || 0 }} sections planned
                </div>
              </template>

              <template v-if="log.action === 'section_start'">
                <div class="section-tag">
                  <span class="tag-num">#{{ log.section_index }}</span>
                  <span class="tag-title">{{ log.section_title }}</span>
                </div>
              </template>

              <template v-if="log.action === 'section_content'">
                <div class="section-tag content-ready">
                  <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M12 20h9"></path>
                    <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path>
                  </svg>
                  <span class="tag-title">{{ log.section_title }}</span>
                </div>
              </template>

              <template v-if="log.action === 'section_complete'">
                <div class="section-tag completed">
                  <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="20 6 9 17 4 12"></polyline>
                  </svg>
                  <span class="tag-title">{{ log.section_title }}</span>
                </div>
              </template>

              <template v-if="log.action === 'tool_call'">
                <div class="tool-badge" :class="'tool-' + getToolColor(log.details?.tool_name)">
                  <svg v-if="getToolIcon(log.details?.tool_name) === 'lightbulb'" class="tool-icon" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M9 18h6M10 22h4M12 2a7 7 0 0 0-4 12.5V17a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1v-2.5A7 7 0 0 0 12 2z"></path>
                  </svg>
                  <svg v-else-if="getToolIcon(log.details?.tool_name) === 'globe'" class="tool-icon" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="10"></circle>
                    <path d="M2 12h20M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path>
                  </svg>
                  <svg v-else-if="getToolIcon(log.details?.tool_name) === 'users'" class="tool-icon" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
                    <circle cx="9" cy="7" r="4"></circle>
                    <path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"></path>
                  </svg>
                  <svg v-else-if="getToolIcon(log.details?.tool_name) === 'zap'" class="tool-icon" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
                    <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon>
                  </svg>
                  <svg v-else-if="getToolIcon(log.details?.tool_name) === 'chart'" class="tool-icon" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
                    <line x1="18" y1="20" x2="18" y2="10"></line>
                    <line x1="12" y1="20" x2="12" y2="4"></line>
                    <line x1="6" y1="20" x2="6" y2="14"></line>
                  </svg>
                  <svg v-else-if="getToolIcon(log.details?.tool_name) === 'database'" class="tool-icon" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
                    <ellipse cx="12" cy="5" rx="9" ry="3"></ellipse>
                    <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"></path>
                    <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"></path>
                  </svg>
                  <svg v-else class="tool-icon" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"></path>
                  </svg>
                  {{ getToolDisplayName(log.details?.tool_name) }}
                </div>
                <div v-if="log.details?.parameters && expandedLogs.has(log.timestamp)" class="tool-params">
                  <pre>{{ formatParams(log.details.parameters) }}</pre>
                </div>
              </template>

              <template v-if="log.action === 'tool_result'">
                <div class="result-wrapper" :class="'result-' + log.details?.tool_name">
                  <div v-if="!['interview_agents', 'insight_forge', 'panorama_search', 'quick_search'].includes(log.details?.tool_name)" class="result-meta">
                    <span class="result-tool">{{ getToolDisplayName(log.details?.tool_name) }}</span>
                    <span class="result-size">{{ formatResultSize(log.details?.result_length) }}</span>
                  </div>

                  <div v-if="!showRawResult[log.timestamp]" class="result-structured">
                    <template v-if="log.details?.tool_name === 'interview_agents'">
                      <InterviewDisplay :result="parseInterview(log.details.result)" :result-length="log.details?.result_length" />
                    </template>

                    <template v-else-if="log.details?.tool_name === 'insight_forge'">
                      <InsightDisplay :result="parseInsightForge(log.details.result)" :result-length="log.details?.result_length" />
                    </template>

                    <template v-else-if="log.details?.tool_name === 'panorama_search'">
                      <PanoramaDisplay :result="parsePanorama(log.details.result)" :result-length="log.details?.result_length" />
                    </template>

                    <template v-else-if="log.details?.tool_name === 'quick_search'">
                      <QuickSearchDisplay :result="parseQuickSearch(log.details.result)" :result-length="log.details?.result_length" />
                    </template>

                    <template v-else>
                      <pre class="raw-preview">{{ truncateText(log.details?.result, 300) }}</pre>
                    </template>
                  </div>

                  <div v-else class="result-raw">
                    <pre>{{ log.details?.result }}</pre>
                  </div>
                </div>
              </template>

              <template v-if="log.action === 'llm_response'">
                <div class="llm-meta">
                  <span class="meta-tag">Iteration {{ log.details?.iteration }}</span>
                  <span class="meta-tag" :class="{ active: log.details?.has_tool_calls }">
                    Tools: {{ log.details?.has_tool_calls ? 'Yes' : 'No' }}
                  </span>
                  <span class="meta-tag" :class="{ active: log.details?.has_final_answer, 'final-answer': log.details?.has_final_answer }">
                    Final: {{ log.details?.has_final_answer ? 'Yes' : 'No' }}
                  </span>
                </div>
                <div v-if="log.details?.has_final_answer" class="final-answer-hint">
                  <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="20 6 9 17 4 12"></polyline>
                  </svg>
                  <span>Section "{{ log.section_title }}" content generated</span>
                </div>
                <div v-if="expandedLogs.has(log.timestamp) && log.details?.response" class="llm-content">
                  <pre>{{ log.details.response }}</pre>
                </div>
              </template>

              <template v-if="log.action === 'report_complete'">
                <div class="complete-banner">
                  <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                    <polyline points="22 4 12 14.01 9 11.01"></polyline>
                  </svg>
                  <span>Report Generation Complete</span>
                </div>
              </template>
            </div>

            <div class="timeline-footer" v-if="log.elapsed_seconds || (log.action === 'tool_call' && log.details?.parameters) || log.action === 'tool_result' || (log.action === 'llm_response' && log.details?.response)">
              <span v-if="log.elapsed_seconds" class="elapsed-badge">+{{ log.elapsed_seconds.toFixed(1) }}s</span>
              <span v-else class="elapsed-placeholder"></span>

              <div class="footer-actions">
                <button v-if="log.action === 'tool_call' && log.details?.parameters" class="action-btn" @click.stop="emitToggleLogExpand(log)">
                  {{ expandedLogs.has(log.timestamp) ? 'Hide Params' : 'Show Params' }}
                </button>

                <button v-if="log.action === 'tool_result'" class="action-btn" @click.stop="emitToggleRawResult(log.timestamp, $event)">
                  {{ showRawResult[log.timestamp] ? 'Structured View' : 'Raw Output' }}
                </button>

                <button v-if="log.action === 'llm_response' && log.details?.response" class="action-btn" @click.stop="emitToggleLogExpand(log)">
                  {{ expandedLogs.has(log.timestamp) ? 'Hide Response' : 'Show Response' }}
                </button>
              </div>
            </div>
          </div>
        </div>
      </TransitionGroup>

      <div v-if="agentLogs.length === 0 && !isComplete" class="workflow-empty">
        <div class="empty-pulse"></div>
        <span>Waiting for agent activity...</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
// @ts-nocheck
import {
  InsightDisplay,
  InterviewDisplay,
  PanoramaDisplay,
  QuickSearchDisplay,
} from './ReportToolDisplays'
import {
  getToolColor,
  getToolDisplayName,
  getToolIcon,
} from '../../utils/reportToolMetadata'
import {
  parseInsightForge,
  parseInterview,
  parsePanorama,
  parseQuickSearch,
} from '../../utils/reportToolResults'
import {
  formatParams,
  formatResultSize,
  formatTime,
  getActionLabel,
  getConnectorClass,
  getTimelineItemClass,
  truncateText,
} from '../../utils/reportWorkflow'

const props = defineProps({
  isComplete: { type: Boolean, default: false },
  activeStep: { type: Object, default: () => ({ status: 'todo', noLabel: '--', title: '', meta: '' }) },
  agentLogs: { type: Array, default: () => [] },
  reportOutline: { type: Object, default: null },
  completedSections: { type: Number, default: 0 },
  totalSections: { type: Number, default: 0 },
  elapsedText: { type: String, default: '0s' },
  totalToolCalls: { type: Number, default: 0 },
  statusClass: { type: String, default: 'pending' },
  statusText: { type: String, default: 'Waiting' },
  workflowSteps: { type: Array, default: () => [] },
  displayLogs: { type: Array, default: () => [] },
  expandedLogs: { type: Object, default: () => new Set() },
  showRawResult: { type: Object, default: () => ({}) },
  nextStepLabel: { type: String, default: 'Next Step' },
})

const emit = defineEmits(['go-to-interaction', 'toggle-log-expand', 'toggle-raw-result'])

const isLogCollapsed = (log) => {
  if (['tool_call', 'tool_result', 'llm_response'].includes(log.action)) {
    return !props.expandedLogs.has(log.timestamp)
  }
  return false
}

const emitToggleLogExpand = (log) => {
  emit('toggle-log-expand', log)
}

const emitToggleRawResult = (timestamp, event) => {
  emit('toggle-raw-result', timestamp, event)
}
</script>

<style scoped src="./ReportWorkflowPanel.scoped.css"></style>
