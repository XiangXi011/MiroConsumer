<template>
  <div class="chat-messages" ref="chatMessages">
    <div v-if="chatHistory.length === 0" class="chat-empty">
      <div class="empty-icon">
        <svg viewBox="0 0 24 24" width="48" height="48" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
        </svg>
      </div>
      <p class="empty-text">
        {{ chatTarget === 'report_agent' ? t('step5.chatEmptyReportAgent') : t('step5.chatEmptyAgent') }}
      </p>
    </div>

    <div
      v-for="(msg, idx) in chatHistory"
      :key="idx"
      class="chat-message"
      :class="msg.role"
    >
      <div class="message-avatar">
        <span v-if="msg.role === 'user'">U</span>
        <span v-else>{{ msg.role === 'assistant' && chatTarget === 'report_agent' ? 'R' : (selectedAgent?.username?.[0] || 'A') }}</span>
      </div>
      <div class="message-content">
        <div class="message-header">
          <span class="sender-name">
            {{ msg.role === 'user' ? t('step5.senderUser') : (chatTarget === 'report_agent' ? t('step5.reportInsightAssistantName') : (selectedAgent?.username || t('step5.consumerPersonaFallback'))) }}
          </span>
          <span class="message-time">{{ formatTime(msg.timestamp) }}</span>
        </div>
        <div class="message-text" v-html="renderMarkdown(msg.content)"></div>
      </div>
    </div>

    <div v-if="isSending" class="chat-message assistant">
      <div class="message-avatar">
        <span>{{ chatTarget === 'report_agent' ? 'R' : (selectedAgent?.username?.[0] || 'A') }}</span>
      </div>
      <div class="message-content">
        <div class="typing-indicator">
          <span></span>
          <span></span>
          <span></span>
        </div>
      </div>
    </div>
  </div>

  <div class="chat-input-area">
    <textarea
      :value="chatInput"
      class="chat-input"
      :placeholder="t('step5.chatInputPlaceholder')"
      :disabled="isInputDisabled"
      rows="1"
      ref="chatInputRef"
      @input="emit('update:chat-input', $event.target.value)"
      @keydown.enter.exact.prevent="emit('send-message')"
    ></textarea>
    <button
      class="send-btn"
      :disabled="isSendDisabled"
      @click="emit('send-message')"
    >
      <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
        <line x1="22" y1="2" x2="11" y2="13"></line>
        <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
      </svg>
    </button>
  </div>
</template>

<script setup lang="ts">
// @ts-nocheck
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { renderReportMarkdown as renderMarkdown } from '../../utils/reportMarkdown'

const props = defineProps({
  chatHistory: { type: Array, default: () => [] },
  chatInput: { type: String, default: '' },
  isSending: { type: Boolean, default: false },
  chatTarget: { type: String, required: true },
  selectedAgent: { type: Object, default: null },
})

const emit = defineEmits(['update:chat-input', 'send-message'])

const { t } = useI18n()

const chatMessages = ref(null)
const chatInputRef = ref(null)

const isInputDisabled = computed(() => props.isSending || (!props.selectedAgent && props.chatTarget === 'agent'))
const isSendDisabled = computed(() => !props.chatInput.trim() || isInputDisabled.value)

const formatTime = (timestamp) => {
  if (!timestamp) return ''
  try {
    return new Date(timestamp).toLocaleTimeString('en-US', {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return ''
  }
}

defineExpose({
  chatMessages,
  chatInputRef,
})
</script>

<style scoped>
.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.chat-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  color: #9CA3AF;
}

.empty-icon {
  opacity: 0.3;
}

.empty-text {
  font-size: 14px;
  text-align: center;
  max-width: 280px;
  line-height: 1.6;
}

.chat-message {
  display: flex;
  gap: 12px;
}

.chat-message.user {
  flex-direction: row-reverse;
}

.message-avatar {
  width: 36px;
  height: 36px;
  min-width: 36px;
  min-height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 600;
  flex-shrink: 0;
}

.chat-message.user .message-avatar {
  background: #1F2937;
  color: #FFFFFF;
}

.chat-message.assistant .message-avatar {
  background: #F3F4F6;
  color: #374151;
}

.message-content {
  max-width: 70%;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.chat-message.user .message-content {
  align-items: flex-end;
}

.message-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.chat-message.user .message-header {
  flex-direction: row-reverse;
}

.sender-name {
  font-size: 12px;
  font-weight: 600;
  color: #374151;
}

.message-time {
  font-size: 11px;
  color: #9CA3AF;
}

.message-text {
  padding: 10px 14px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.5;
  counter-reset: list-counter;
}

.chat-message.user .message-text {
  background: #1F2937;
  color: #FFFFFF;
  border-bottom-right-radius: 4px;
}

.chat-message.assistant .message-text {
  background: #F3F4F6;
  color: #374151;
  border-bottom-left-radius: 4px;
}

.message-text :deep(.md-p) {
  margin: 0;
}

.message-text :deep(.md-p:last-child) {
  margin-bottom: 0;
}

.message-text :deep(.md-ol) {
  list-style: none;
  padding-left: 0;
  margin: 8px 0;
}

.message-text :deep(.md-oli) {
  counter-increment: list-counter;
  display: flex;
  gap: 8px;
  margin: 4px 0;
}

.message-text :deep(.md-oli)::before {
  content: counter(list-counter) ".";
  font-weight: 600;
  color: #374151;
  min-width: 20px;
  flex-shrink: 0;
}

.message-text :deep(.md-ul) {
  padding-left: 20px;
  margin: 8px 0;
}

.message-text :deep(.md-li) {
  margin: 4px 0;
}

.typing-indicator {
  display: flex;
  gap: 4px;
  padding: 10px 14px;
  background: #F3F4F6;
  border-radius: 12px;
  border-bottom-left-radius: 4px;
}

.typing-indicator span {
  width: 8px;
  height: 8px;
  background: #9CA3AF;
  border-radius: 50%;
  animation: typing 1.4s infinite ease-in-out;
}

.typing-indicator span:nth-child(1) { animation-delay: 0s; }
.typing-indicator span:nth-child(2) { animation-delay: 0.2s; }
.typing-indicator span:nth-child(3) { animation-delay: 0.4s; }

@keyframes typing {
  0%, 60%, 100% { transform: translateY(0); }
  30% { transform: translateY(-8px); }
}

.chat-input-area {
  padding: 16px 24px;
  border-top: 1px solid #E5E7EB;
  display: flex;
  gap: 12px;
  align-items: flex-end;
}

.chat-input {
  flex: 1;
  padding: 12px 16px;
  font-size: 14px;
  border: 1px solid #E5E7EB;
  border-radius: 8px;
  resize: none;
  font-family: inherit;
  line-height: 1.5;
  transition: border-color 0.2s ease;
}

.chat-input:focus {
  outline: none;
  border-color: #1F2937;
}

.chat-input:disabled {
  background: #F9FAFB;
  cursor: not-allowed;
}

.send-btn {
  width: 44px;
  height: 44px;
  background: #1F2937;
  color: #FFFFFF;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s ease;
}

.send-btn:hover:not(:disabled) {
  background: #374151;
}

.send-btn:disabled {
  background: #E5E7EB;
  color: #9CA3AF;
  cursor: not-allowed;
}

.message-text :deep(.md-quote) {
  margin: 12px 0;
  padding: 12px 16px;
  background: #F9FAFB;
  border-left: 3px solid #1F2937;
  color: #4B5563;
}

@media (max-width: 768px) {
  .message-content {
    max-width: 84%;
  }
}
</style>
