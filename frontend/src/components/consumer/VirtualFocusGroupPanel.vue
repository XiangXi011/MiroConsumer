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
            <div
              v-for="response in turn.responses"
              :key="`${idx}-${response.agent_id}-${response.role}`"
              class="turn-response-block"
            >
              <p class="turn-text">
                <strong>{{ response.role }}</strong>: {{ response.response }}
              </p>
              <ConsumerExplainabilityPanel
                v-if="buildExplainabilityData(response)"
                :data="buildExplainabilityData(response)"
              />
            </div>
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
      <div
        v-for="(item, idx) in result.next_what_if_experiments"
        :key="idx"
        class="what-if-card"
      >
        <p>{{ item }}</p>
        <ConsumerExplainabilityPanel
          v-if="buildWhatIfExplainabilityData(item, idx)"
          :data="buildWhatIfExplainabilityData(item, idx)"
        />
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
// @ts-nocheck
import { ref } from 'vue'
import {
  INTERVIEW_ROLE_PRESETS,
  buildFocusGroupRequest,
} from '../../utils/consumerInterview'
import { runFocusGroup as apiRunFocusGroup } from '../../api/consumer'
import ConsumerExplainabilityPanel from './ConsumerExplainabilityPanel.vue'

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

function buildExplainabilityData(response) {
  if (!response) return null
  const out = {}

  if (response.reasoning_metadata) {
    if (response.reasoning_metadata.llm_invoked !== undefined) {
      out.llm_invoked = response.reasoning_metadata.llm_invoked
    }
    if (response.reasoning_metadata.reasoning_backend) {
      out.reasoning_backend = response.reasoning_metadata.reasoning_backend
    }
    if (response.reasoning_metadata.reasoning_error) {
      out.reasoning_error = response.reasoning_metadata.reasoning_error
    }
  }

  if (response.source) {
    if (!out.source_type) {
      out.source_type = response.source
    }
  }

  if (response.context) {
    if (!out.source_visibility && response.context.support_level) {
      out.source_visibility = response.context.support_level
    }
  }

  if (response.evidence_map) {
    const em = normalizeEvidenceMap(response.evidence_map)
    if (em.length > 0) {
      if (!out.source_visibility) {
        out.source_visibility = em[0].support_level || 'unknown'
      }
      if (!out.source_type) {
        const hasMaterial = em.some(e => e.source_type === 'material')
        const hasSimulation = em.some(e => e.source_type === 'simulation')
        if (hasMaterial && hasSimulation) {
          out.source_type = 'mixed'
        } else if (hasSimulation) {
          out.source_type = 'simulation'
        } else if (hasMaterial) {
          out.source_type = 'material'
        }
      }
    }
  }

  return Object.keys(out).length > 0 ? out : null
}

function buildWhatIfExplainabilityData(item, idx) {
  if (!result.value) return null
  const out = {}

  if (result.value.evidence_map) {
    const em = normalizeEvidenceMap(result.value.evidence_map)
    if (em[idx]) {
      if (em[idx].support_level) {
        out.source_visibility = em[idx].support_level
      }
      if (em[idx].agent_id) {
        out.reasoning_backend = em[idx].agent_id
      }
    }
  }

  if (props.targetContext) {
    if (!out.source_type && props.targetContext.branch_id) {
      out.source_type = 'material'
    }
    if (props.targetContext.simulation_id) {
      if (!out.source_type) {
        out.source_type = 'simulation'
      }
    }
  }

  return Object.keys(out).length > 0 ? out : null
}

function normalizeEvidenceMap(evidenceMap) {
  if (!evidenceMap) return []
  if (Array.isArray(evidenceMap)) return evidenceMap
  if (typeof evidenceMap === 'object') return Object.values(evidenceMap)
  return []
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
  border-bottom: 1px solid var(--mc-border);
  background: var(--mc-surface);
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
  color: var(--mc-text-secondary);
}

.focus-head strong {
  font-size: 14px;
  font-weight: 600;
  color: var(--mc-text-primary);
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
  border: 1px solid var(--mc-border);
  background: var(--mc-surface);
  color: var(--mc-text-secondary);
  border-radius: 999px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.role-chip:hover {
  border-color: var(--mc-border-strong);
  color: var(--mc-text-primary);
}

.role-chip.active {
  background: var(--mc-accent);
  color: #fffdfa;
  border-color: var(--mc-accent);
}

.focus-input {
  padding: 10px 12px;
  font-size: 13px;
  border: 1px solid var(--mc-border);
  border-radius: 6px;
  font-family: inherit;
  transition: border-color 0.2s ease;
}

.focus-input:focus {
  outline: none;
  border-color: var(--mc-accent);
  box-shadow: var(--mc-focus-ring);
}

.focus-actions {
  display: flex;
  gap: 10px;
}

.focus-run-btn {
  padding: 10px 18px;
  font-size: 13px;
  font-weight: 500;
  background: var(--mc-accent);
  color: #fffdfa;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.2s ease;
}

.focus-run-btn:hover:not(:disabled) {
  background: var(--mc-accent-strong);
}

.focus-run-btn:disabled {
  background: var(--mc-border);
  color: var(--mc-text-tertiary);
  cursor: not-allowed;
}

.turn-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.turn-card {
  border: 1px solid var(--mc-border);
  background: var(--mc-bg-subtle);
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

.turn-response-block {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 6px 0;
  border-bottom: 1px solid #F3F4F6;
}

.turn-response-block:last-child {
  border-bottom: none;
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
