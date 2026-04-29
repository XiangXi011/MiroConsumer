<template>
  <section class="focus-group-panel" aria-label="Virtual Focus Group">
    <div class="focus-head">
      <span class="focus-kicker">Virtual Focus Group</span>
      <strong>虚拟焦点小组</strong>
    </div>

    <!-- participant-role-selection -->
    <div class="focus-section participant-role-selection">
      <span class="section-label">Participant Roles</span>
      <div class="role-chips">
        <button
          v-for="preset in INTERVIEW_ROLE_PRESETS"
          :key="preset.role"
          class="role-chip"
          :class="{ active: selectedRoles.has(preset.role) }"
          @click="toggleRole(preset.role)"
        >
          {{ preset.label }}
        </button>
      </div>
    </div>

    <!-- moderator-goal-input -->
    <div class="focus-section">
      <span class="section-label">Moderator Goal</span>
      <input
        v-model="moderatorGoal"
        class="focus-input"
        type="text"
        placeholder="e.g. Find disagreement on price"
      />
    </div>

    <div class="focus-actions">
      <button
        class="focus-run-btn"
        :disabled="isRunning || !moderatorGoal.trim()"
        @click="runFocusGroup"
      >
        <span v-if="isRunning" class="loading-spinner"></span>
        <span v-else>Run Focus Group</span>
      </button>
    </div>

    <!-- turn-by-turn -->
    <div v-if="result && result.turns" class="focus-section turn-by-turn">
      <span class="section-label">Turn-by-turn</span>
      <div class="turn-list">
        <div
          v-for="(turn, idx) in result.turns"
          :key="idx"
          class="turn-card"
        >
          <div class="turn-meta">
            <span class="turn-num">Turn {{ idx + 1 }}</span>
            <span class="turn-speaker">{{ turn.agent_id || 'Moderator' }}</span>
          </div>
          <div v-if="turn.responses" class="turn-responses">
            <p
              v-for="response in turn.responses"
              :key="`${idx}-${response.agent_id}-${response.role}`"
              class="turn-text"
            >
              <strong>{{ response.role }}</strong>: {{ response.response }}
            </p>
          </div>
          <p v-else class="turn-text">{{ turn.text }}</p>
        </div>
      </div>
    </div>

    <!-- consensus-view -->
    <div v-if="result && result.consensus" class="focus-section consensus-view">
      <span class="section-label">Consensus</span>
      <div class="consensus-card">
        <ul>
          <li v-for="(item, idx) in result.consensus" :key="idx">{{ item }}</li>
        </ul>
      </div>
    </div>

    <!-- disagreement-view -->
    <div v-if="result && result.disagreements" class="focus-section disagreement-view">
      <span class="section-label">Disagreement</span>
      <div class="disagreement-card">
        <ul>
          <li v-for="(item, idx) in result.disagreements" :key="idx">{{ item }}</li>
        </ul>
      </div>
    </div>

    <!-- evidence-map-view -->
    <div v-if="result && result.evidence_map" class="focus-section evidence-map-view">
      <span class="section-label">Evidence Map</span>
      <div class="evidence-card">
        <div
          v-for="(evidence, idx) in result.evidence_map"
          :key="idx"
          class="evidence-item"
        >
          <span class="evidence-agent">{{ evidence.agent_id }}</span>
          <span class="evidence-text">{{ evidence.support_level || evidence.text }}</span>
        </div>
      </div>
    </div>

    <!-- what-if-output -->
    <div v-if="result && result.next_what_if_experiments" class="focus-section what-if-output">
      <span class="section-label">What-if</span>
      <div class="what-if-card">
        <p v-for="item in result.next_what_if_experiments" :key="item">{{ item }}</p>
      </div>
    </div>
  </section>
</template>

<script setup>
import { ref } from 'vue'
import {
  INTERVIEW_ROLE_PRESETS,
  buildFocusGroupRequest,
} from '../../utils/consumerInterview'
import { runFocusGroup as apiRunFocusGroup } from '../../api/consumer'

const props = defineProps({
  simulationId: { type: String, default: '' },
  targetContext: { type: Object, default: null },
})

const emit = defineEmits(['add-log', 'result'])

const selectedRoles = ref(new Set())
const moderatorGoal = ref('')
const result = ref(null)
const isRunning = ref(false)

function toggleRole(role) {
  const next = new Set(selectedRoles.value)
  if (next.has(role)) {
    next.delete(role)
  } else {
    next.add(role)
  }
  selectedRoles.value = next
}

async function runFocusGroup() {
  if (!props.simulationId || isRunning.value) return
  isRunning.value = true
  try {
    const payload = buildFocusGroupRequest({
      topic: moderatorGoal.value,
      moderatorGoal: moderatorGoal.value,
      selectedRoles: Array.from(selectedRoles.value),
      maxAgents: 8,
      targetContext: props.targetContext,
    })
    const res = await apiRunFocusGroup(props.simulationId, payload)
    if (res.success && res.data) {
      result.value = res.data
      emit('result', res.data)
    }
  } catch (err) {
    emit('add-log', `Focus group failed: ${err.message}`)
  } finally {
    isRunning.value = false
  }
}
</script>

<style scoped>
.focus-group-panel {
  border-bottom: 1px solid #E5E7EB;
  background: #FFFFFF;
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.focus-head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
}

.focus-head span,
.section-label {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: #6B7280;
}

.focus-head strong {
  font-size: 14px;
  font-weight: 600;
  color: #111827;
}

.focus-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.role-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.role-chip {
  padding: 5px 10px;
  font-size: 12px;
  border: 1px solid #E5E7EB;
  background: #FFFFFF;
  color: #374151;
  border-radius: 999px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.role-chip:hover {
  border-color: #D1D5DB;
}

.role-chip.active {
  background: #1F2937;
  color: #FFFFFF;
  border-color: #1F2937;
}

.focus-input {
  padding: 10px 12px;
  font-size: 13px;
  border: 1px solid #E5E7EB;
  border-radius: 6px;
  font-family: inherit;
  transition: border-color 0.2s ease;
}

.focus-input:focus {
  outline: none;
  border-color: #1F2937;
}

.focus-actions {
  display: flex;
  gap: 10px;
}

.focus-run-btn {
  padding: 10px 18px;
  font-size: 13px;
  font-weight: 500;
  background: #1F2937;
  color: #FFFFFF;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.2s ease;
}

.focus-run-btn:hover:not(:disabled) {
  background: #374151;
}

.focus-run-btn:disabled {
  background: #E5E7EB;
  color: #9CA3AF;
  cursor: not-allowed;
}

.turn-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.turn-card {
  border: 1px solid #E5E7EB;
  background: #FAFAFA;
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.turn-meta {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
}

.turn-num {
  font-size: 11px;
  font-weight: 600;
  color: #6B7280;
}

.turn-speaker {
  font-size: 11px;
  color: #9CA3AF;
}

.turn-text {
  font-size: 12px;
  color: #374151;
  margin: 0;
  line-height: 1.5;
}

.consensus-card,
.disagreement-card,
.evidence-card,
.what-if-card {
  border: 1px solid #E5E7EB;
  background: #FAFAFA;
  padding: 10px 12px;
}

.consensus-card ul,
.disagreement-card ul {
  margin: 0;
  padding-left: 18px;
  font-size: 12px;
  color: #374151;
  line-height: 1.6;
}

.evidence-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 6px 0;
  border-bottom: 1px solid #F3F4F6;
}

.evidence-item:last-child {
  border-bottom: none;
}

.evidence-agent {
  font-size: 11px;
  font-weight: 600;
  color: #6B7280;
}

.evidence-text {
  font-size: 12px;
  color: #374151;
}

.what-if-card p {
  font-size: 12px;
  color: #4B5563;
  margin: 0;
  font-style: italic;
  line-height: 1.5;
}

.loading-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #FFFFFF;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
