<template>
  <div class="explainability-panel">
    <div class="section-label">Explainability</div>

    <div v-if="data.source_visibility !== undefined" class="xp-row">
      <span class="xp-key">Source Visibility</span>
      <span class="xp-value">{{ data.source_visibility }}</span>
    </div>

    <div v-if="data.source_type" class="xp-row">
      <span class="xp-key">Source Type</span>
      <span
        class="xp-value xp-badge"
        :class="`xp-badge--${data.source_type}`"
      >
        {{ data.source_type }}
      </span>
    </div>

    <div v-if="data.llm_invoked !== undefined" class="xp-row">
      <span class="xp-key">LLM Invoked</span>
      <span class="xp-value">{{ data.llm_invoked ? 'Yes' : 'No' }}</span>
    </div>

    <div v-if="data.reasoning_backend" class="xp-row">
      <span class="xp-key">Reasoning Backend</span>
      <span class="xp-value mono">{{ data.reasoning_backend }}</span>
    </div>

    <div v-if="data.reasoning_error" class="xp-row xp-error">
      <span class="xp-key">Reasoning Error</span>
      <span class="xp-value">{{ data.reasoning_error }}</span>
    </div>

    <div v-if="isTemplateFallback" class="xp-row xp-warning">
      <span class="xp-key">Template Fallback</span>
      <span class="xp-value">Active</span>
    </div>

    <div v-if="data.confidence !== undefined" class="xp-row">
      <span class="xp-key">Confidence</span>
      <span class="xp-value">{{ formatConfidence(data.confidence) }}</span>
    </div>

    <div v-if="data.evidence_validation_result" class="xp-row">
      <span class="xp-key">Evidence Validation</span>
      <span
        class="xp-value xp-badge"
        :class="`xp-badge--${data.evidence_validation_result}`"
      >
        {{ data.evidence_validation_result }}
      </span>
    </div>

    <div v-if="data.evidence_gatekeeping_result" class="xp-row">
      <span class="xp-key">Evidence Gatekeeping</span>
      <span
        class="xp-value xp-badge"
        :class="`xp-badge--${data.evidence_gatekeeping_result}`"
      >
        {{ data.evidence_gatekeeping_result }}
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
// @ts-nocheck
import { computed } from 'vue'

const props = defineProps({
  data: {
    type: Object,
    required: true,
  },
})

const isTemplateFallback = computed(() => {
  const backend = String(props.data.reasoning_backend || '')
  return backend === 'template_fallback' || backend === 'template' || backend === 'mock'
})

function formatConfidence(value) {
  if (typeof value === 'number') {
    return `${Math.round(value * 100)}%`
  }
  return String(value)
}
</script>

<style scoped>
.explainability-panel {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 12px;
  background: #F9FAFB;
  border: 1px solid #E5E7EB;
  border-radius: 8px;
}

.xp-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}

.xp-key {
  color: #6B7280;
  min-width: 130px;
}

.xp-value {
  color: #374151;
  font-weight: 500;
}

.xp-value.mono {
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
}

.xp-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
  text-transform: capitalize;
}

.xp-badge--material {
  background: #DBEAFE;
  color: #1E40AF;
}

.xp-badge--simulation {
  background: #D1FAE5;
  color: #065F46;
}

.xp-badge--mixed {
  background: #FEF3C7;
  color: #92400E;
}

.xp-badge--supported,
.xp-badge--PASS {
  background: #D1FAE5;
  color: #065F46;
}

.xp-badge--weak_support,
.xp-badge--downgraded {
  background: #FEF3C7;
  color: #92400E;
}

.xp-badge--insufficient_support,
.xp-badge--blocked,
.xp-badge--BLOCKED {
  background: #FEE2E2;
  color: #991B1B;
}

.xp-error {
  color: #B91C1C;
}

.xp-error .xp-key {
  color: #B91C1C;
}

.xp-error .xp-value {
  color: #991B1B;
}

.xp-warning {
  color: #92400E;
}

.xp-warning .xp-key {
  color: #92400E;
}

.xp-warning .xp-value {
  color: #B45309;
}
</style>
