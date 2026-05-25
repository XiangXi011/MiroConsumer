<template>
  <section class="interview-workspace" aria-label="Representative Consumer Interview">
    <div class="interview-head">
      <span class="interview-kicker">Representative Interview</span>
      <strong>深度消费者访谈</strong>
    </div>

    <!-- role-filter -->
    <div class="interview-section role-filter">
      <span class="section-label">Role Filter</span>
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

    <!-- agent-selection -->
    <div class="interview-section agent-selection">
      <span class="section-label">Agent Selection</span>
      <div class="agent-list">
        <RepresentativeConsumerCard
          v-for="agent in filteredAgents"
          :key="agent.agent_id"
          v-bind="agent.view"
          @ask="selectAgentForInterview(agent.agent_id)"
        />
      </div>
    </div>

    <!-- topic-input -->
    <div class="interview-section">
      <span class="section-label">Topic</span>
      <input
        v-model="topic"
        class="interview-input"
        type="text"
        placeholder="Enter interview topic..."
      />
    </div>

    <!-- question-list -->
    <div class="interview-section">
      <span class="section-label">Questions</span>
      <textarea
        v-model="questionsText"
        class="interview-textarea"
        rows="3"
        placeholder="Enter questions, one per line..."
      ></textarea>
    </div>

    <!-- fixed-prompt -->
    <div class="interview-section">
      <span class="section-label">Quick Prompts</span>
      <div class="prompt-chips">
        <button
          v-for="prompt in quickPrompts"
          :key="prompt"
          class="prompt-chip"
          @click="applyPrompt(prompt)"
        >
          {{ prompt }}
        </button>
      </div>
    </div>

    <div class="interview-actions">
      <button
        class="interview-run-btn"
        :disabled="isRunning || !topic.trim()"
        @click="runInterview"
      >
        <span v-if="isRunning" class="loading-spinner"></span>
        <span v-else>Run Interview</span>
      </button>
      <button
        class="interview-load-btn"
        :disabled="isLoadingAgents"
        @click="loadAgents"
      >
        Load Agents
      </button>
    </div>

    <!-- interview-result -->
    <div v-if="result" class="interview-section interview-result">
      <span class="section-label">Result</span>
      <div class="result-card">
        <div class="result-topic">{{ result.topic }}</div>
        <div v-if="result.answers" class="result-responses">
          <div
            v-for="(response, idx) in result.answers"
            :key="idx"
            class="response-item"
          >
            <span class="response-agent">{{ response.agent_id }}</span>
            <p class="response-text">{{ response.answer }}</p>
          </div>
        </div>
        <div v-if="result.summary" class="result-summary">
          {{ result.summary }}
        </div>
        <div v-if="result.followup_questions && result.followup_questions.length" class="result-followups">
          <button
            v-for="question in result.followup_questions"
            :key="question"
            class="prompt-chip"
            @click="applyPrompt(question)"
          >
            {{ question }}
          </button>
        </div>
      </div>
    </div>

    <!-- follow-up-question -->
    <div v-if="result" class="interview-section follow-up-question">
      <span class="section-label">Follow-up</span>
      <input
        v-model="followUpQuestion"
        class="interview-input"
        type="text"
        placeholder="Ask a follow-up question..."
        @keydown.enter="runFollowUp"
      />
      <button
        class="interview-run-btn small"
        :disabled="!followUpQuestion.trim() || isRunning"
        @click="runFollowUp"
      >
        Ask Follow-up
      </button>
    </div>
  </section>
</template>

<script setup lang="ts">
// @ts-nocheck
import { ref, computed, watch } from 'vue'
import RepresentativeConsumerCard from './RepresentativeConsumerCard.vue'
import {
  INTERVIEW_ROLE_PRESETS,
  buildRepresentativeCardView,
  buildInterviewRequest,
  extractConsumerItems,
} from '../../utils/consumerInterview'
import {
  listRepresentativeAgents,
  runConsumerInterview,
} from '../../api/consumer'

const props = defineProps({
  simulationId: { type: String, default: '' },
  targetContext: { type: Object, default: null },
})

const emit = defineEmits(['add-log', 'result'])

const selectedRoles = ref(new Set())
const selectedAgentIds = ref(new Set())
const agents = ref([])
const topic = ref('')
const questionsText = ref('')
const followUpQuestion = ref('')
const result = ref(null)
const isRunning = ref(false)
const isLoadingAgents = ref(false)

const quickPrompts = [
  'What made you skeptical?',
  'What would change your mind?',
  'Who would you tell about this?',
]

const filteredAgents = computed(() => {
  if (selectedRoles.value.size === 0) return agents.value
  return agents.value.filter((a) => selectedRoles.value.has(a.role))
})

function toggleRole(role) {
  const next = new Set(selectedRoles.value)
  if (next.has(role)) {
    next.delete(role)
  } else {
    next.add(role)
  }
  selectedRoles.value = next
}

function applyPrompt(prompt) {
  questionsText.value = questionsText.value
    ? questionsText.value + '\n' + prompt
    : prompt
}

function selectAgentForInterview(agentId) {
  const agent = agents.value.find((a) => a.agent_id === agentId)
  const next = new Set(selectedAgentIds.value)
  if (next.has(agentId)) {
    next.delete(agentId)
  } else {
    next.add(agentId)
  }
  selectedAgentIds.value = next
  if (agent) {
    topic.value = `Interview with ${agent.display_name || agentId}`
  }
}

async function loadAgents() {
  if (!props.simulationId) return
  isLoadingAgents.value = true
  try {
    const res = await listRepresentativeAgents(props.simulationId)
    const list = extractConsumerItems(res)
    if (list.length > 0) {
      agents.value = list.map((a) => ({
        ...a,
        view: buildRepresentativeCardView(a),
      }))
    }
  } catch (err) {
    emit('add-log', `Failed to load agents: ${err.message}`)
  } finally {
    isLoadingAgents.value = false
  }
}

async function runInterview() {
  if (!props.simulationId || isRunning.value) return
  isRunning.value = true
  try {
    const payload = buildInterviewRequest({
      topic: topic.value,
      questionsText: questionsText.value,
      selectedAgentIds: selectedAgentIds.value.size > 0
        ? Array.from(selectedAgentIds.value)
        : agents.value
          .filter((a) => selectedRoles.value.size === 0 || selectedRoles.value.has(a.role))
          .map((a) => a.agent_id),
      selectedRoles: Array.from(selectedRoles.value),
      mode: 'snapshot',
      maxAgents: 3,
      targetContext: props.targetContext,
    })
    const res = await runConsumerInterview(props.simulationId, payload)
    if (res.success && res.data) {
      result.value = res.data
      emit('result', res.data)
    }
  } catch (err) {
    emit('add-log', `Interview failed: ${err.message}`)
  } finally {
    isRunning.value = false
  }
}

async function runFollowUp() {
  if (!followUpQuestion.value.trim() || isRunning.value) return
  questionsText.value = followUpQuestion.value
  followUpQuestion.value = ''
  await runInterview()
}

watch(() => props.simulationId, (id) => {
  if (id) loadAgents()
}, { immediate: true })
</script>

<style scoped>
.interview-workspace {
  border-bottom: 1px solid var(--mc-border);
  background: var(--mc-surface);
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.interview-head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
}

.interview-head span,
.section-label {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--mc-text-secondary);
}

.interview-head strong {
  font-size: 14px;
  font-weight: 600;
  color: var(--mc-text-primary);
}

.interview-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.role-chips,
.prompt-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.role-chip,
.prompt-chip {
  padding: 5px 10px;
  font-size: 12px;
  border: 1px solid var(--mc-border);
  background: var(--mc-surface);
  color: var(--mc-text-secondary);
  border-radius: 999px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.role-chip:hover,
.prompt-chip:hover {
  border-color: var(--mc-border-strong);
  color: var(--mc-text-primary);
}

.role-chip.active {
  background: var(--mc-accent);
  color: #fffdfa;
  border-color: var(--mc-accent);
}

.agent-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 10px;
}

.interview-input,
.interview-textarea {
  padding: 10px 12px;
  font-size: 13px;
  border: 1px solid var(--mc-border);
  border-radius: 6px;
  font-family: inherit;
  transition: border-color 0.2s ease;
}

.interview-input:focus,
.interview-textarea:focus {
  outline: none;
  border-color: var(--mc-accent);
  box-shadow: var(--mc-focus-ring);
}

.interview-actions {
  display: flex;
  gap: 10px;
}

.interview-run-btn,
.interview-load-btn {
  padding: 10px 18px;
  font-size: 13px;
  font-weight: 500;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.2s ease;
}

.interview-run-btn {
  background: var(--mc-accent);
  color: #fffdfa;
}

.interview-run-btn:hover:not(:disabled) {
  background: var(--mc-accent-strong);
}

.interview-run-btn:disabled {
  background: var(--mc-border);
  color: var(--mc-text-tertiary);
  cursor: not-allowed;
}

.interview-run-btn.small {
  padding: 8px 14px;
  font-size: 12px;
  align-self: flex-start;
}

.interview-load-btn {
  background: var(--mc-surface-muted);
  color: var(--mc-text-secondary);
}

.interview-load-btn:hover:not(:disabled) {
  background: var(--mc-accent-wash);
}

.result-card {
  border: 1px solid var(--mc-border);
  background: var(--mc-bg-subtle);
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.result-topic {
  font-size: 13px;
  font-weight: 600;
  color: var(--mc-text-primary);
}

.result-responses {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.response-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 8px;
  background: var(--mc-surface);
  border: 1px solid var(--mc-border);
}

.response-agent {
  font-size: 11px;
  font-weight: 600;
  color: var(--mc-text-secondary);
}

.response-text {
  font-size: 12px;
  color: #374151;
  margin: 0;
  line-height: 1.5;
}

.result-summary {
  font-size: 12px;
  color: #4B5563;
  font-style: italic;
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
