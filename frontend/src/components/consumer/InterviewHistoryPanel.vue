<template>
  <section class="history-panel" aria-label="Interview History">
    <div class="history-head">
      <span class="history-kicker">Interview History</span>
      <strong>访谈历史</strong>
    </div>

    <div class="history-actions">
      <button
        class="history-load-btn"
        :disabled="isLoading"
        @click="loadHistory"
      >
        Refresh
      </button>
    </div>

    <!-- interview-history -->
    <div v-if="interviewItems.length > 0" class="history-group interview-history">
      <span class="section-label">Interviews</span>
      <div class="history-list">
        <div
          v-for="item in interviewItems"
          :key="item.id"
          class="history-card"
        >
          <div class="history-row">
            <span class="history-key">Topic</span>
            <span class="history-value">{{ item.topic }}</span>
          </div>
          <div class="history-row">
            <span class="history-key">Roles</span>
            <span class="history-value">{{ (item.roles || []).join(', ') }}</span>
          </div>
          <div class="history-row">
            <span class="history-key">Created</span>
            <span class="history-value mono">{{ item.createdAt }}</span>
          </div>
          <div class="history-row">
            <span class="history-key">Summary</span>
            <span class="history-value">{{ item.summary }}</span>
          </div>
          <button class="history-reopen-btn" @click="$emit('reopen', item)">Reopen</button>
        </div>
      </div>
    </div>

    <!-- focus-group-history -->
    <div v-if="focusGroupItems.length > 0" class="history-group focus-group-history">
      <span class="section-label">Focus Groups</span>
      <div class="history-list">
        <div
          v-for="item in focusGroupItems"
          :key="item.id"
          class="history-card"
        >
          <div class="history-row">
            <span class="history-key">Topic</span>
            <span class="history-value">{{ item.topic }}</span>
          </div>
          <div class="history-row">
            <span class="history-key">Roles</span>
            <span class="history-value">{{ (item.roles || []).join(', ') }}</span>
          </div>
          <div class="history-row">
            <span class="history-key">Created</span>
            <span class="history-value mono">{{ item.createdAt }}</span>
          </div>
          <div class="history-row">
            <span class="history-key">Summary</span>
            <span class="history-value">{{ item.summary }}</span>
          </div>
          <button class="history-reopen-btn" @click="$emit('reopen', item)">Reopen</button>
        </div>
      </div>
    </div>

    <div v-if="items.length === 0 && !isLoading" class="history-empty">
      No interview history yet.
    </div>
  </section>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import {
  normalizeInterviewHistoryItems,
  extractConsumerItems,
} from '../../utils/consumerInterview'
import {
  listInterviewHistory,
  listFocusGroupHistory,
} from '../../api/consumer'

const props = defineProps({
  simulationId: { type: String, default: '' },
})

const emit = defineEmits(['reopen', 'add-log'])

const items = ref([])
const isLoading = ref(false)

const interviewItems = computed(() =>
  items.value.filter((i) => i.type === 'interview')
)

const focusGroupItems = computed(() =>
  items.value.filter((i) => i.type === 'focus_group')
)

async function loadHistory() {
  if (!props.simulationId) return
  isLoading.value = true
  try {
    const [interviewRes, focusRes] = await Promise.all([
      listInterviewHistory(props.simulationId),
      listFocusGroupHistory(props.simulationId),
    ])
    items.value = normalizeInterviewHistoryItems({
      interviews: extractConsumerItems(interviewRes),
      focusGroups: extractConsumerItems(focusRes),
    })
  } catch (err) {
    emit('add-log', `Failed to load history: ${err.message}`)
  } finally {
    isLoading.value = false
  }
}

watch(() => props.simulationId, (id) => {
  if (id) loadHistory()
}, { immediate: true })
</script>

<style scoped>
.history-panel {
  border-bottom: 1px solid #E5E7EB;
  background: #FFFFFF;
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.history-head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
}

.history-head span,
.section-label {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: #6B7280;
}

.history-head strong {
  font-size: 14px;
  font-weight: 600;
  color: #111827;
}

.history-actions {
  display: flex;
  gap: 10px;
}

.history-load-btn {
  padding: 8px 14px;
  font-size: 12px;
  font-weight: 500;
  background: #F3F4F6;
  color: #374151;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.2s ease;
}

.history-load-btn:hover:not(:disabled) {
  background: #E5E7EB;
}

.history-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.history-card {
  border: 1px solid #E5E7EB;
  background: #FAFAFA;
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.history-row {
  display: flex;
  justify-content: space-between;
  gap: 8px;
}

.history-key {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: #6B7280;
  min-width: 60px;
}

.history-value {
  font-size: 12px;
  color: #374151;
  text-align: right;
}

.history-reopen-btn {
  align-self: flex-start;
  padding: 5px 10px;
  font-size: 11px;
  font-weight: 500;
  background: #1F2937;
  color: #FFFFFF;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: background 0.2s ease;
  margin-top: 4px;
}

.history-reopen-btn:hover {
  background: #374151;
}

.history-empty {
  font-size: 12px;
  color: #9CA3AF;
  padding: 10px 0;
}

.mono {
  font-family: 'JetBrains Mono', monospace;
}
</style>
