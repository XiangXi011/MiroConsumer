<template>
  <div class="consumer-chat-brief">
    <div v-if="quickPrompts.length > 0" class="consumer-chat-section">
      <div class="consumer-chat-label">{{ t('consumer.recommendedFollowUps') }}</div>
      <div class="consumer-chat-prompts">
        <button
          v-for="prompt in quickPrompts"
          :key="prompt"
          class="consumer-prompt-chip"
          @click="emit('apply-prompt', prompt)"
        >
          {{ prompt }}
        </button>
      </div>
    </div>

    <div v-if="vocHighlights.length > 0" class="consumer-chat-section">
      <div class="consumer-chat-label">{{ t('consumer.vocHighlights') }}</div>
      <div class="consumer-chat-quotes">
        <div v-for="quote in vocHighlights" :key="quote.bucket" class="consumer-chat-quote">
          <span class="consumer-chat-bucket">{{ quote.label }}</span>
          <span class="consumer-chat-text">"{{ quote.quote }}"</span>
        </div>
      </div>
    </div>

    <div v-if="showTechnical && (sourceCatalog.length > 0 || enrichedFindings.length > 0)" class="consumer-chat-section">
      <div class="consumer-chat-label">{{ t('consumer.sourcesUsed') }}</div>
      <div class="consumer-source-strip">
        <div v-for="source in sourceCatalog.slice(0, 4)" :key="source.source_id" class="consumer-source-mini">
          <span class="source-mini-label">{{ source.label }}</span>
          <span v-if="source.lane" class="source-mini-lane">{{ source.lane }}</span>
        </div>
        <div v-if="enrichedFindings.length > 0" class="source-mini-evidence">
          <span class="evidence-mini-count">{{ enrichedFindings.length }} {{ t('consumer.evidenceItems') }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
// @ts-nocheck
import { useI18n } from 'vue-i18n'

defineProps({
  quickPrompts: { type: Array, default: () => [] },
  vocHighlights: { type: Array, default: () => [] },
  sourceCatalog: { type: Array, default: () => [] },
  enrichedFindings: { type: Array, default: () => [] },
  showTechnical: { type: Boolean, default: false },
})

const emit = defineEmits(['apply-prompt'])

const { t } = useI18n()
</script>

<style scoped>
.consumer-chat-brief {
  border-bottom: 1px solid #E5E7EB;
  background: #FFFDFB;
  padding: 18px 24px;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.consumer-chat-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.consumer-chat-label {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #6B7280;
}

.consumer-chat-prompts {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.consumer-prompt-chip {
  border: 1px solid #FED7AA;
  background: #FFF7ED;
  color: #9A3412;
  padding: 8px 12px;
  border-radius: 999px;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s ease;
}

.consumer-prompt-chip:hover {
  background: #FFEDD5;
  border-color: #FB923C;
}

.consumer-chat-quotes {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.consumer-chat-quote {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}

.consumer-chat-bucket {
  min-width: 82px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--mc-accent);
}

.consumer-chat-text {
  color: var(--mc-text-primary);
  line-height: 1.6;
}

.consumer-source-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.consumer-source-mini {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 3px 8px;
  background: #F3F4F6;
  border: 1px solid #E5E7EB;
  border-radius: 999px;
  font-size: 11px;
}

.source-mini-label {
  color: #374151;
  font-weight: 500;
}

.source-mini-lane {
  font-size: 0.6rem;
  font-family: 'JetBrains Mono', monospace;
  padding: 1px 4px;
  background: #E0F2FE;
  color: #0369A1;
  border-radius: 3px;
}

.source-mini-evidence {
  font-size: 11px;
  color: #6B7280;
}

.evidence-mini-count {
  font-family: 'JetBrains Mono', monospace;
}
</style>
