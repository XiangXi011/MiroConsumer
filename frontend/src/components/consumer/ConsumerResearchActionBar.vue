<template>
  <div class="consumer-research-action-bar">
    <button
      class="action-btn"
      :disabled="disabled"
      @click="emitAction(CONSUMER_RESEARCH_ACTIONS.DEEP_DIVE_CONCLUSION)"
    >
      深挖结论
    </button>
    <button
      class="action-btn"
      :disabled="disabled"
      @click="emitAction(CONSUMER_RESEARCH_ACTIONS.EXPLAIN_PROPAGATION_PATH)"
    >
      查看传播路径
    </button>
    <button
      class="action-btn"
      :disabled="disabled"
      @click="emitAction(CONSUMER_RESEARCH_ACTIONS.VERIFY_EVIDENCE)"
    >
      查看证据
    </button>
    <button
      class="action-btn"
      :disabled="disabled"
      @click="emitAction(CONSUMER_RESEARCH_ACTIONS.INTERVIEW_CONSUMERS)"
    >
      追问消费者
    </button>
    <button
      class="action-btn"
      :disabled="disabled || !branchId"
      @click="emitAction(CONSUMER_RESEARCH_ACTIONS.COMPARE_BRANCH_DELTA)"
    >
      比较分支差异
    </button>
  </div>
</template>

<script setup>
import {
  CONSUMER_RESEARCH_ACTIONS,
  buildConsumerResearchActionPayload,
} from '../../utils/consumerResearchActions'

const props = defineProps({
  reportId: String,
  simulationId: String,
  sectionIndex: Number,
  sectionTitle: String,
  sectionContent: String,
  branchId: String,
  disabled: Boolean,
})

const emit = defineEmits(['run-action'])

function emitAction(actionType) {
  const payload = buildConsumerResearchActionPayload(actionType, {
    reportId: props.reportId,
    sectionIndex: props.sectionIndex,
    sectionTitle: props.sectionTitle,
    sectionContent: props.sectionContent,
    branchId: props.branchId,
  })
  emit('run-action', payload)
}
</script>

<style scoped>
.consumer-research-action-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid #E5E7EB;
}

.action-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  font-size: 12px;
  font-weight: 500;
  color: #374151;
  background: #F9FAFB;
  border: 1px solid #E5E7EB;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.action-btn:hover:not(:disabled) {
  background: #F3F4F6;
  border-color: #D1D5DB;
}

.action-btn:disabled {
  background: #F3F4F6;
  color: #9CA3AF;
  border-color: #E5E7EB;
  cursor: not-allowed;
}
</style>
