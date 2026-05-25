<template>
  <aside class="brief-validation" :class="{ complete: items.length === 0 }">
    <div class="validation-header">
      <span class="validation-title">{{ items.length === 0 ? 'Brief 已就绪' : '开始前还差这些信息' }}</span>
      <span class="validation-count">{{ items.length === 0 ? '可以开始测试' : `${items.length} 项待补充` }}</span>
    </div>

    <p class="validation-copy">
      {{ items.length === 0
        ? '系统将基于你的素材、目标人群和研究目标生成消费者传播测试。'
        : '补齐后即可进入测试准备，不需要先理解技术流程。' }}
    </p>

    <div v-if="items.length > 0" class="missing-list">
      <button
        v-for="item in items"
        :key="item.field"
        class="missing-item"
        type="button"
        @click="$emit('focus-field', item.field)"
      >
        <span class="missing-group">{{ item.group }}</span>
        <span class="missing-label">{{ item.label }}</span>
        <span class="missing-hint">{{ item.hint }}</span>
      </button>
    </div>
  </aside>
</template>

<script setup lang="ts">
// @ts-nocheck
defineProps({
  items: { type: Array, default: () => [] },
})

defineEmits(['focus-field'])
</script>

<style scoped>
.brief-validation {
  border: 1px solid #FED7AA;
  background: #FFF7ED;
  border-radius: 8px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.brief-validation.complete {
  border-color: #A7F3D0;
  background: #ECFDF5;
}

.validation-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.validation-title {
  font-size: 15px;
  font-weight: 700;
  color: #111827;
}

.validation-count {
  font-size: 12px;
  font-weight: 700;
  color: #C2410C;
  white-space: nowrap;
}

.complete .validation-count {
  color: #047857;
}

.validation-copy {
  margin: 0;
  color: #6B7280;
  font-size: 13px;
  line-height: 1.6;
}

.missing-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.missing-item {
  width: 100%;
  text-align: left;
  border: 1px solid #FDBA74;
  background: #FFFFFF;
  border-radius: 6px;
  padding: 10px 12px;
  display: grid;
  grid-template-columns: 70px 1fr;
  gap: 3px 10px;
  cursor: pointer;
}

.missing-item:hover {
  border-color: #EA580C;
}

.missing-group {
  grid-row: span 2;
  color: #C2410C;
  font-size: 11px;
  font-weight: 700;
}

.missing-label {
  color: #111827;
  font-size: 13px;
  font-weight: 700;
}

.missing-hint {
  color: #6B7280;
  font-size: 12px;
  line-height: 1.4;
}
</style>
