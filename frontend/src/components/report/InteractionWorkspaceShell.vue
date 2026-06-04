<template>
  <div class="right-panel">
    <InteractionActionBar
      :active-tab="activeTab"
      :chat-target="chatTarget"
      :profiles="profiles"
      :selected-agent="selectedAgent"
      :show-agent-dropdown="showAgentDropdown"
      @select-report-agent-chat="emit('select-report-agent-chat')"
      @toggle-agent-dropdown="emit('toggle-agent-dropdown')"
      @select-agent="(agent, idx) => emit('select-agent', agent, idx)"
      @select-survey-tab="emit('select-survey-tab')"
    />

    <div v-if="activeTab === 'chat'" class="chat-container">
      <ReportAgentToolsCard v-if="showTechnical && chatTarget === 'report_agent'" />

      <ComparisonSnapshotWorkspace
        v-if="showTechnical && chatTarget === 'report_agent' && isConsumerMode"
        :simulation-id="simulationId"
        :is-consumer-mode="isConsumerMode"
        :comparison-snapshot="comparisonSnapshot"
        @update:branch-comparison="emit('update:branch-comparison', $event)"
        @update:comparison-snapshot="emit('update:comparison-snapshot', $event)"
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
        @apply-prompt="prompt => emit('apply-prompt', prompt)"
      />

      <AgentProfileCard v-if="chatTarget === 'agent' && selectedAgent" :agent="selectedAgent" />

      <InteractionChatPanel
        ref="chatPanelRef"
        :chat-history="chatHistory"
        :chat-input="chatInput"
        :is-sending="isSending"
        :chat-target="chatTarget"
        :selected-agent="selectedAgent"
        @update:chat-input="value => emit('update:chat-input', value)"
        @send-message="emit('send-message')"
      />
    </div>

    <div v-if="showTechnical && isConsumerMode" class="consumer-interview-workspace">
      <RepresentativeConsumerInterview
        :simulation-id="simulationId"
        :target-context="interviewHandoffContext"
        @add-log="msg => emit('add-log', msg)"
      />
      <VirtualFocusGroupPanel
        :simulation-id="simulationId"
        :target-context="interviewHandoffContext"
        @add-log="msg => emit('add-log', msg)"
      />
      <InterviewHistoryPanel
        :simulation-id="simulationId"
        @add-log="msg => emit('add-log', msg)"
      />
    </div>

    <InteractionSurveyPanel
      v-if="activeTab === 'survey'"
      :profiles="profiles"
      :selected-agents="selectedAgents"
      :survey-question="surveyQuestion"
      :survey-results="surveyResults"
      :is-surveying="isSurveying"
      @toggle-agent-selection="idx => emit('toggle-agent-selection', idx)"
      @select-all-agents="emit('select-all-agents')"
      @clear-agent-selection="emit('clear-agent-selection')"
      @update:survey-question="value => emit('update:survey-question', value)"
      @submit-survey="emit('submit-survey')"
    />
  </div>
</template>

<script setup lang="ts">
// @ts-nocheck
import { ref } from 'vue'
import ComparisonSnapshotWorkspace from '../consumer/ComparisonSnapshotWorkspace.vue'
import PropagationPathGraph from '../consumer/PropagationPathGraph.vue'
import RepresentativeConsumerInterview from '../consumer/RepresentativeConsumerInterview.vue'
import VirtualFocusGroupPanel from '../consumer/VirtualFocusGroupPanel.vue'
import InterviewHistoryPanel from '../consumer/InterviewHistoryPanel.vue'
import AgentProfileCard from './AgentProfileCard.vue'
import ConsumerChatBrief from './ConsumerChatBrief.vue'
import InteractionActionBar from './InteractionActionBar.vue'
import InteractionChatPanel from './InteractionChatPanel.vue'
import InteractionSurveyPanel from './InteractionSurveyPanel.vue'
import ReportAgentToolsCard from './ReportAgentToolsCard.vue'

defineProps({
  activeTab: { type: String, required: true },
  chatTarget: { type: String, required: true },
  profiles: { type: Array, default: () => [] },
  selectedAgent: { type: Object, default: null },
  showAgentDropdown: { type: Boolean, default: false },
  showTechnical: { type: Boolean, default: false },
  isConsumerMode: { type: Boolean, default: false },
  simulationId: { type: String, default: '' },
  comparisonSnapshot: { type: Object, default: null },
  reportContext: { type: Object, default: () => ({}) },
  consumerQuickPrompts: { type: Array, default: () => [] },
  consumerVocHighlights: { type: Array, default: () => [] },
  consumerSourceCatalog: { type: Array, default: () => [] },
  consumerEnrichedFindings: { type: Array, default: () => [] },
  chatHistory: { type: Array, default: () => [] },
  chatInput: { type: String, default: '' },
  isSending: { type: Boolean, default: false },
  interviewHandoffContext: { type: Object, default: null },
  selectedAgents: { type: Object, default: () => new Set() },
  surveyQuestion: { type: String, default: '' },
  surveyResults: { type: Array, default: () => [] },
  isSurveying: { type: Boolean, default: false },
})

const emit = defineEmits([
  'select-report-agent-chat',
  'toggle-agent-dropdown',
  'select-agent',
  'select-survey-tab',
  'update:branch-comparison',
  'update:comparison-snapshot',
  'apply-prompt',
  'update:chat-input',
  'send-message',
  'add-log',
  'toggle-agent-selection',
  'select-all-agents',
  'clear-agent-selection',
  'update:survey-question',
  'submit-survey',
])

const chatPanelRef = ref(null)

defineExpose({
  chatPanelRef,
})
</script>

<style scoped>
.right-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: var(--mc-bg-subtle);
  overflow: hidden;
}

.chat-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
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

:deep(.md-ul),
:deep(.md-ol) {
  margin: 12px 0;
  padding-left: 24px;
}

:deep(.md-li),
:deep(.md-oli) {
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

@media (max-width: 980px) {
  .right-panel {
    min-height: 56vh;
  }
}
</style>
