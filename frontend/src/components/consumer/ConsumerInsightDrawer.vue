<template>
  <div class="insight-drawer-overlay" @click.self="emit('close')">
    <div class="insight-drawer">
      <div class="drawer-header">
        <h3 class="drawer-title">{{ result?.title || '' }}</h3>
        <button class="drawer-close" @click="emit('close')">
          <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      </div>

      <div class="drawer-body">
        <div v-if="loading" class="drawer-loading">
          <div class="loading-spinner"></div>
          <span>Loading...</span>
        </div>

        <div v-else-if="error" class="drawer-error">
          {{ error }}
        </div>

        <div v-else-if="result" class="drawer-content">
          <div v-if="result.summary" class="content-section">
            <div class="section-label">Summary</div>
            <div class="section-text">{{ result.summary }}</div>
          </div>

          <div v-if="result.details_markdown" class="content-section">
            <div class="section-label">Details</div>
            <div class="section-markdown" v-html="renderMarkdown(result.details_markdown)"></div>
          </div>

          <div v-if="result.evidence" class="content-section">
            <div class="section-label">Evidence</div>
            <div class="evidence-row">
              <span class="evidence-key">Support Level</span>
              <span class="evidence-value">{{ result.evidence.support_level }}</span>
            </div>
            <div class="evidence-row">
              <span class="meta-key">Sources</span>
              <span class="meta-value mono">{{ result.evidence.source_count }}</span>
            </div>
            <div class="evidence-row">
              <span class="meta-key">Simulation Quotes</span>
              <span class="meta-value mono">{{ result.evidence.simulation_quote_count }}</span>
            </div>
            <div class="evidence-row">
              <span class="meta-key">Gatekeeping</span>
              <span class="meta-value">{{ result.evidence.gatekeeping_status }}</span>
            </div>
          </div>

          <div v-if="result.tool_trace" class="content-section">
            <div class="section-label">Tool Trace</div>
            <div class="trace-row">
              <span class="trace-key">Tool</span>
              <span class="trace-value mono">{{ result.tool_trace.tool_name }}</span>
            </div>
            <div v-if="result.tool_trace.consumer_tool_label" class="trace-row">
              <span class="trace-key">Label</span>
              <span class="trace-value">{{ result.tool_trace.consumer_tool_label }}</span>
            </div>
            <div v-if="result.tool_trace.query" class="trace-row">
              <span class="trace-key">Query</span>
              <span class="trace-value">{{ result.tool_trace.query }}</span>
            </div>
          </div>

          <div v-if="isPhase6IInterviewHandoff(result)" class="content-section handoff-section">
            <button class="handoff-btn" @click="emitOpenHandoff">
              进入消费者追问工作台
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { isPhase6IInterviewHandoff } from '../../utils/consumerResearchActions'

const props = defineProps({
  result: Object,
  loading: Boolean,
  error: String,
})

const emit = defineEmits(['close', 'open-handoff'])

function emitOpenHandoff() {
  if (props.result && props.result.handoff && props.result.handoff.target_context) {
    emit('open-handoff', props.result.handoff.target_context)
  }
}

function renderMarkdown(content) {
  if (!content) return ''
  let html = content
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>')
    .replace(/^### (.+)$/gm, '<h4 class="md-h4">$1</h4>')
    .replace(/^## (.+)$/gm, '<h3 class="md-h3">$1</h3>')
    .replace(/^- (.+)$/gm, '<li class="md-li">$1</li>')
    .replace(/\n\n/g, '</p><p class="md-p">')
    .replace(/\n/g, '<br>')
  html = '<p class="md-p">' + html + '</p>'
  html = html.replace(/<p class="md-p"><\/p>/g, '')
  html = html.replace(/(<li class="md-li"[^>]*>.*?<\/li>\s*)+/g, '<ul class="md-ul">$&</ul>')
  return html
}
</script>

<style scoped>
.insight-drawer-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.35);
  z-index: 200;
  display: flex;
  justify-content: flex-end;
}

.insight-drawer {
  width: 480px;
  max-width: 90vw;
  height: 100%;
  background: #FFFFFF;
  display: flex;
  flex-direction: column;
  box-shadow: -4px 0 24px rgba(0, 0, 0, 0.1);
}

.drawer-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid #E5E7EB;
}

.drawer-title {
  font-size: 15px;
  font-weight: 600;
  color: #1F2937;
  margin: 0;
}

.drawer-close {
  width: 28px;
  height: 28px;
  background: #F3F4F6;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #6B7280;
  transition: all 0.2s ease;
}

.drawer-close:hover {
  background: #E5E7EB;
  color: #374151;
}

.drawer-body {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.drawer-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 40px 0;
  color: #6B7280;
  font-size: 14px;
}

.loading-spinner {
  width: 18px;
  height: 18px;
  border: 2px solid #E5E7EB;
  border-top-color: #4B5563;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.drawer-error {
  padding: 20px;
  background: #FEF2F2;
  border: 1px solid #FECACA;
  border-radius: 8px;
  color: #B91C1C;
  font-size: 14px;
}

.drawer-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.content-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.section-label {
  font-size: 11px;
  font-weight: 600;
  color: #9CA3AF;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.section-text {
  font-size: 14px;
  line-height: 1.6;
  color: #374151;
}

.section-markdown :deep(.md-p) {
  margin: 0 0 8px 0;
  font-size: 14px;
  line-height: 1.6;
  color: #374151;
}

.section-markdown :deep(.md-h3) {
  font-size: 15px;
  font-weight: 600;
  color: #1F2937;
  margin: 12px 0 6px 0;
}

.section-markdown :deep(.md-h4) {
  font-size: 14px;
  font-weight: 600;
  color: #374151;
  margin: 10px 0 4px 0;
}

.section-markdown :deep(.md-ul) {
  margin: 8px 0;
  padding-left: 20px;
}

.section-markdown :deep(.md-li) {
  margin: 4px 0;
  font-size: 14px;
}

.section-markdown :deep(.inline-code) {
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  background: #F3F4F6;
  padding: 2px 6px;
  border-radius: 4px;
  color: #1F2937;
}

.evidence-row,
.meta-row,
.trace-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}

.evidence-key,
.meta-key,
.trace-key {
  color: #6B7280;
  min-width: 100px;
}

.evidence-value,
.meta-value,
.trace-value {
  color: #374151;
  font-weight: 500;
}

.handoff-section {
  padding-top: 12px;
  border-top: 1px solid #E5E7EB;
}

.handoff-btn {
  width: 100%;
  padding: 12px 16px;
  font-size: 14px;
  font-weight: 600;
  color: #FFFFFF;
  background: #1F2937;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.2s ease;
}

.handoff-btn:hover {
  background: #374151;
}
</style>
