<template>
  <header class="business-flow-header">
    <div class="brand-area">
      <button class="brand-button" type="button" @click="$emit('home')">MIROCONSUMER</button>
      <div class="status-copy">
        <span class="status-label" :class="'status-' + statusCopy.status">{{ statusCopy.label }}</span>
        <span class="status-description">{{ statusCopy.description }}</span>
      </div>
    </div>

    <nav class="flow-steps" aria-label="消费者测试流程">
      <div
        v-for="(step, idx) in steps"
        :key="step.key"
        class="flow-step"
        :class="{
          active: idx + 1 === currentStep,
          completed: idx + 1 < currentStep,
        }"
      >
        <span class="step-dot">{{ idx + 1 }}</span>
        <span class="step-title">{{ step.title }}</span>
      </div>
    </nav>

    <div class="header-actions">
      <button class="detail-toggle" type="button" @click="$emit('toggle-technical')">
        {{ showTechnical ? '隐藏技术详情' : '技术详情' }}
      </button>
      <LanguageSwitcher />
    </div>
  </header>
</template>

<script setup lang="ts">
// @ts-nocheck
import { computed } from 'vue'
import LanguageSwitcher from './LanguageSwitcher.vue'
import { getBusinessFlowSteps, getBusinessStatusCopy } from '../utils/businessUx'

const props = defineProps({
  currentStep: { type: Number, default: 1 },
  status: { type: String, default: 'idle' },
  showTechnical: { type: Boolean, default: false },
})

defineEmits(['home', 'toggle-technical'])

const steps = computed(() => getBusinessFlowSteps())
const statusCopy = computed(() => getBusinessStatusCopy(
  steps.value[Math.max(0, Math.min(steps.value.length - 1, props.currentStep - 1))]?.key,
  props.status,
))
</script>

<style scoped>
.business-flow-header {
  min-height: 72px;
  border-bottom: 1px solid var(--mc-border);
  background: rgba(255, 253, 250, 0.96);
  display: grid;
  grid-template-columns: minmax(240px, 0.9fr) minmax(420px, 1.7fr) minmax(180px, 0.7fr);
  align-items: center;
  gap: 20px;
  padding: 12px 24px;
  position: relative;
  z-index: 100;
  backdrop-filter: blur(14px);
  box-shadow: 0 1px 0 rgba(24, 45, 35, 0.04);
}

.brand-area {
  display: flex;
  align-items: center;
  gap: 16px;
  min-width: 0;
}

.brand-button {
  border: none;
  background: transparent;
  font-family: var(--mc-font-mono);
  font-weight: 800;
  font-size: 16px;
  letter-spacing: 1px;
  cursor: pointer;
  color: var(--mc-text-primary);
  padding: 0;
  flex-shrink: 0;
}

.status-copy {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
}

.status-label {
  font-size: 13px;
  font-weight: 700;
  color: var(--mc-text-primary);
}

.status-label.status-processing {
  color: var(--mc-accent);
}

.status-label.status-completed {
  color: var(--mc-status-success);
}

.status-label.status-error {
  color: var(--mc-status-error);
}

.status-description {
  font-size: 12px;
  color: var(--mc-text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.flow-steps {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 8px;
  min-width: 0;
}

.flow-step {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  color: var(--mc-text-tertiary);
}

.step-dot {
  width: 24px;
  height: 24px;
  border-radius: 999px;
  border: 1px solid var(--mc-border);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-family: var(--mc-font-mono);
  flex-shrink: 0;
}

.step-title {
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.flow-step.completed {
  color: var(--mc-status-success);
}

.flow-step.completed .step-dot {
  background: var(--mc-status-success-bg);
  border-color: rgba(23, 122, 88, 0.24);
}

.flow-step.active {
  color: var(--mc-text-primary);
}

.flow-step.active .step-dot {
  background: var(--mc-accent);
  border-color: var(--mc-accent);
  color: #fffdfa;
}

.header-actions {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 10px;
}

.detail-toggle {
  border: 1px solid var(--mc-border);
  background: var(--mc-surface);
  color: var(--mc-text-secondary);
  border-radius: var(--mc-radius-control);
  padding: 7px 10px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}

.detail-toggle:hover {
  border-color: var(--mc-accent);
  color: var(--mc-accent);
  background: var(--mc-accent-wash);
}

@media (max-width: 1100px) {
  .business-flow-header {
    grid-template-columns: 1fr;
    gap: 12px;
  }

  .header-actions {
    justify-content: flex-start;
  }
}

@media (max-width: 720px) {
  .business-flow-header {
    padding: 12px 16px;
  }

  .flow-steps {
    grid-template-columns: 1fr;
  }

  .flow-step:not(.active) {
    display: none;
  }

  .status-description {
    white-space: normal;
  }
}
</style>
