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

<style scoped>
.report-workflow-panel {
  display: flex;
  flex: 1;
  min-height: 0;
  flex-direction: column;

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

.mono {
  font-family: 'JetBrains Mono', monospace;
}

.panel-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 20px;
  background: var(--mc-surface);
  border-bottom: 1px solid var(--mc-border);
  font-size: 13px;
  font-weight: 600;
  color: var(--mc-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  position: sticky;
  top: 0;
  z-index: 10;
}

.header-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--mc-accent);
  box-shadow: 0 0 0 3px rgba(34, 92, 75, 0.15);
  margin-right: 10px;
  flex-shrink: 0;
  animation: pulse-dot 1.5s ease-in-out infinite;
}

@keyframes pulse-dot {
  0%, 100% { box-shadow: 0 0 0 3px rgba(34, 92, 75, 0.15); }
  50% { box-shadow: 0 0 0 5px rgba(34, 92, 75, 0.1); }
}

.header-index {
  font-size: 12px;
  font-weight: 600;
  color: var(--mc-text-tertiary);
  margin-right: 10px;
  flex-shrink: 0;
}

.header-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--mc-text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  text-transform: none;
  letter-spacing: 0;
}

.header-meta {
  margin-left: auto;
  font-size: 10px;
  font-weight: 600;
  color: #6B7280;
  flex-shrink: 0;
}

.panel-header--active {
  background: var(--mc-accent-wash);
  border-color: var(--mc-accent);
}

.panel-header--active .header-index,
.panel-header--active .header-meta {
  color: var(--mc-accent);
}

.panel-header--active .header-title {
  color: var(--mc-text-primary);
}

.panel-header--done {
  background: var(--mc-status-success-bg);
}

.panel-header--done .header-index {
  color: var(--mc-status-success);
}

.panel-header--todo .header-index,
.panel-header--todo .header-title {
  color: var(--mc-text-tertiary);
}

.workflow-overview {
  padding: 16px 20px 0 20px;
}

.workflow-metrics {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}

.metric {
  display: inline-flex;
  align-items: baseline;
  gap: 6px;
}

.metric-right {
  margin-left: auto;
}

.metric-label {
  font-size: 11px;
  font-weight: 600;
  color: #9CA3AF;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.metric-value {
  font-size: 12px;
  color: #374151;
}

.metric-pill {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  padding: 4px 10px;
  border-radius: 999px;
  border: 1px solid var(--wf-border);
  background: #F9FAFB;
  color: #6B7280;
}

.metric-pill.pill--processing {
  background: var(--wf-active-bg);
  border-color: var(--wf-active-border);
  color: var(--wf-active-text);
}

.metric-pill.pill--completed {
  background: #ECFDF5;
  border-color: #A7F3D0;
  color: #065F46;
}

.metric-pill.pill--pending {
  background: transparent;
  border-style: dashed;
  color: #6B7280;
}

.workflow-steps {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding-bottom: 10px;
}

.wf-step {
  display: grid;
  grid-template-columns: 24px 1fr;
  gap: 12px;
  padding: 10px 12px;
  border: 1px solid var(--wf-divider);
  border-radius: 8px;
  background: #FFFFFF;
}

.wf-step--active {
  background: var(--wf-active-bg);
  border-color: var(--wf-active-border);
}

.wf-step--done {
  background: var(--wf-done-bg);
  border-color: var(--wf-done-border);
}

.wf-step--todo {
  background: transparent;
  border-color: var(--wf-border);
  border-style: dashed;
}

.wf-step-connector {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 24px;
  flex-shrink: 0;
}

.wf-step-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--wf-muted-dot);
  border: 2px solid #FFFFFF;
  z-index: 1;
}

.wf-step-line {
  width: 2px;
  flex: 1;
  background: var(--wf-divider);
  margin-top: -2px;
}

.wf-step--active .wf-step-dot {
  background: var(--wf-active-dot);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.12);
}

.wf-step--done .wf-step-dot {
  background: var(--wf-done-dot);
}

.wf-step-title-row {
  display: flex;
  align-items: baseline;
  gap: 10px;
  min-width: 0;
}

.wf-step-index {
  font-size: 11px;
  font-weight: 700;
  color: var(--mc-text-tertiary);
  letter-spacing: 0.02em;
  flex-shrink: 0;
}

.wf-step-title {
  font-family: var(--mc-font-body);
  font-size: 13px;
  font-weight: 600;
  color: var(--mc-text-primary);
  line-height: 1.35;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.wf-step-meta {
  margin-left: auto;
  font-size: 10px;
  font-weight: 700;
  color: var(--wf-active-text);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  flex-shrink: 0;
}

.wf-step--todo .wf-step-title,
.wf-step--todo .wf-step-index {
  color: var(--wf-todo-text);
}

.workflow-divider {
  height: 1px;
  background: var(--wf-divider);
  margin: 14px 0 0 0;
}

.workflow-timeline {
  padding: 14px 20px 24px;
  flex: 1;
}

.timeline-item {
  display: grid;
  grid-template-columns: 24px 1fr;
  gap: 12px;
  padding: 10px 12px;
  margin-bottom: 10px;
  border: 1px solid var(--wf-divider);
  border-radius: 8px;
  background: #FFFFFF;
  transition: background-color 0.15s ease, border-color 0.15s ease;
}

.timeline-item:hover {
  background: #F9FAFB;
  border-color: var(--wf-border);
}

.timeline-item.node--active {
  background: var(--wf-active-bg);
  border-color: var(--wf-active-border);
}

.timeline-item.node--done {
  background: var(--wf-done-bg);
  border-color: var(--wf-done-border);
}

.timeline-connector {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 24px;
  flex-shrink: 0;
}

.connector-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: var(--wf-muted-dot);
  border: 2px solid #FFFFFF;
  z-index: 1;
}

.connector-line {
  width: 2px;
  flex: 1;
  background: var(--wf-divider);
  margin-top: -2px;
}

.dot-active {
  background: var(--wf-active-dot);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.12);
}

.dot-done {
  background: var(--wf-done-dot);
}

.dot-muted {
  background: var(--wf-muted-dot);
}

.timeline-content {
  min-width: 0;
}

.timeline-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.action-label {
  font-size: 12px;
  font-weight: 600;
  color: #374151;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.action-time {
  font-size: 11px;
  color: #9CA3AF;
  font-family: 'JetBrains Mono', monospace;
}

.timeline-body {
  font-size: 13px;
  color: #4B5563;
}

.timeline-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid #F3F4F6;
}

.elapsed-placeholder {
  flex-shrink: 0;
}

.footer-actions {
  display: flex;
  gap: 8px;
  margin-left: auto;
}

.elapsed-badge {
  font-size: 11px;
  color: #6B7280;
  background: #F3F4F6;
  padding: 2px 8px;
  border-radius: 10px;
  font-family: 'JetBrains Mono', monospace;
}

.info-row {
  display: flex;
  gap: 8px;
  margin-bottom: 6px;
}

.info-key {
  font-size: 11px;
  color: #9CA3AF;
  min-width: 80px;
}

.info-val {
  color: #374151;
}

.status-message {
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 13px;
  border: 1px solid transparent;
}

.status-message.planning {
  background: var(--wf-active-bg);
  border-color: var(--wf-active-border);
  color: var(--wf-active-text);
}

.status-message.success {
  background: #ECFDF5;
  border-color: #A7F3D0;
  color: #065F46;
}

.outline-badge {
  display: inline-block;
  margin-top: 8px;
  padding: 4px 10px;
  background: #F9FAFB;
  color: #6B7280;
  border: 1px solid #E5E7EB;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 500;
}

.section-tag {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  background: #F9FAFB;
  border: 1px solid var(--wf-border);
  border-radius: 6px;
}

.section-tag.content-ready {
  background: var(--wf-active-bg);
  border: 1px dashed var(--wf-active-border);
}

.section-tag.content-ready svg {
  color: var(--wf-active-dot);
}

.section-tag.completed {
  background: #ECFDF5;
  border: 1px solid #A7F3D0;
}

.section-tag.completed svg,
.section-tag.completed .tag-num {
  color: #059669;
}

.tag-num {
  font-size: 11px;
  font-weight: 700;
  color: #6B7280;
}

.tag-title {
  font-size: 13px;
  font-weight: 500;
  color: #374151;
}

.tool-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: #F9FAFB;
  color: #374151;
  border: 1px solid var(--wf-border);
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  transition: all 0.2s ease;
}

.tool-icon {
  flex-shrink: 0;
}

.tool-badge.tool-purple {
  background: linear-gradient(135deg, var(--mc-accent-wash) 0%, var(--mc-bg-subtle) 100%);
  border-color: var(--mc-border);
  color: var(--mc-accent);
}

.tool-badge.tool-blue {
  background: linear-gradient(135deg, var(--mc-status-info-bg) 0%, var(--mc-bg-subtle) 100%);
  border-color: var(--mc-border);
  color: var(--mc-status-info);
}

.tool-badge.tool-green {
  background: linear-gradient(135deg, #F0FDF4 0%, #DCFCE7 100%);
  border-color: #86EFAC;
  color: #15803D;
}

.tool-badge.tool-orange {
  background: linear-gradient(135deg, #FFF7ED 0%, #FFEDD5 100%);
  border-color: #FDBA74;
  color: #C2410C;
}

.tool-badge.tool-cyan {
  background: linear-gradient(135deg, #ECFEFF 0%, #CFFAFE 100%);
  border-color: #67E8F9;
  color: #0E7490;
}

.tool-badge.tool-pink {
  background: linear-gradient(135deg, #FDF2F8 0%, #FCE7F3 100%);
  border-color: #F9A8D4;
  color: #BE185D;
}

.tool-badge.tool-gray {
  background: linear-gradient(135deg, #F9FAFB 0%, #F3F4F6 100%);
  border-color: #D1D5DB;
  color: #374151;
}

.tool-params {
  margin-top: 10px;
  background: transparent;
  border-radius: 0;
  padding: 10px 0 0 0;
  border-top: 1px dashed var(--wf-divider);
  overflow-x: auto;
}

.tool-params pre {
  margin: 0;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  color: #4B5563;
  white-space: pre-wrap;
  word-break: break-all;
  background: #F9FAFB;
  border: 1px solid #E5E7EB;
  border-radius: 6px;
  padding: 10px;
}

.action-btn {
  background: #F3F4F6;
  border: 1px solid #E5E7EB;
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
  color: #6B7280;
  cursor: pointer;
  transition: all 0.15s ease;
  white-space: nowrap;
}

.action-btn:hover {
  background: #E5E7EB;
  color: #374151;
  border-color: #D1D5DB;
}

.result-wrapper {
  background: transparent;
  border: none;
  border-top: 1px solid var(--wf-divider);
  border-radius: 0;
  padding: 12px 0 0 0;
}

.result-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.result-tool {
  font-size: 12px;
  font-weight: 600;
  color: #374151;
}

.result-size {
  font-size: 10px;
  color: #6B7280;
  font-family: 'JetBrains Mono', monospace;
}

.result-raw {
  margin-top: 10px;
  max-height: 300px;
  overflow-y: auto;
}

.result-raw pre {
  margin: 0;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  white-space: pre-wrap;
  word-break: break-word;
  color: #374151;
  background: #FFFFFF;
  border: 1px solid #E5E7EB;
  padding: 10px;
  border-radius: 6px;
}

.raw-preview {
  margin: 0;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  white-space: pre-wrap;
  word-break: break-word;
  color: #6B7280;
}

.llm-meta {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.meta-tag {
  font-size: 11px;
  padding: 3px 8px;
  background: #F3F4F6;
  color: #6B7280;
  border-radius: 4px;
}

.meta-tag.active {
  background: #DBEAFE;
  color: #1E40AF;
}

.meta-tag.final-answer {
  background: #D1FAE5;
  color: #059669;
  font-weight: 600;
}

.final-answer-hint,
.complete-banner {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 10px;
  padding: 10px 14px;
  background: #ECFDF5;
  border: 1px solid #A7F3D0;
  border-radius: 6px;
  color: #065F46;
  font-size: 12px;
  font-weight: 500;
}

.complete-banner {
  gap: 10px;
  margin-top: 0;
  padding: 12px 16px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
}

.llm-content {
  margin-top: 10px;
  max-height: 200px;
  overflow-y: auto;
}

.llm-content pre {
  margin: 0;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  white-space: pre-wrap;
  word-break: break-word;
  color: #4B5563;
  background: #F3F4F6;
  padding: 10px;
  border-radius: 6px;
}

.next-step-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  width: calc(100% - 40px);
  margin: 4px 20px 0 20px;
  padding: 14px 20px;
  font-size: 14px;
  font-weight: 600;
  color: #FFFFFF;
  background: #1F2937;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.next-step-btn:hover {
  background: #374151;
}

.next-step-btn svg {
  transition: transform 0.2s ease;
}

.next-step-btn:hover svg {
  transform: translateX(4px);
}

.workflow-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  color: #9CA3AF;
  font-size: 13px;
}

.empty-pulse {
  width: 24px;
  height: 24px;
  background: #E5E7EB;
  border-radius: 50%;
  margin-bottom: 16px;
  animation: pulse-ring 1.5s infinite;
}

@keyframes pulse-ring {
  0%, 100% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.2); opacity: 0.5; }
}

.timeline-item-enter-active {
  transition: all 0.4s ease;
}

.timeline-item-enter-from {
  opacity: 0;
  transform: translateX(-20px);
}
</style>
