<template>
  <!-- Branch / Intervention Panel -->
  <div v-if="isConsumerMode && phase >= 1" class="consumer-branch-panel">
    <div class="consumer-branch-header">
      <span class="consumer-branch-title">{{ $t('consumer.branchPanel.title') }}</span>
      <span v-if="branchState.selectedBranch.value" class="consumer-branch-badge">
        {{ branchState.selectedBranch.value.name }}
      </span>
    </div>

    <div class="consumer-branch-toolbar">
      <select v-model="branchState.selectedBranchId.value" class="consumer-branch-select" @change="onBranchChange">
        <option value="">{{ $t('consumer.branchPanel.selectBranch') }}</option>
        <option v-for="b in branchState.branches.value" :key="b.branch_id" :value="b.branch_id">
          {{ b.name }} (R{{ b.fork_round }})
        </option>
      </select>
      <button class="consumer-branch-btn" @click="branchState.showCreateBranch.value = !branchState.showCreateBranch.value">
        {{ branchState.showCreateBranch.value ? $t('common.cancel') : $t('consumer.branchPanel.create') }}
      </button>
    </div>

    <div v-if="branchState.showCreateBranch.value" class="consumer-branch-form">
      <input v-model="branchState.newBranchName.value" class="consumer-input" :placeholder="$t('consumer.branchPanel.namePlaceholder')" />
      <input v-model.number="branchState.newBranchForkRound.value" type="number" min="0" class="consumer-input narrow" :placeholder="$t('consumer.branchPanel.forkRoundPlaceholder')" />
      <input v-model="branchState.newBranchDescription.value" class="consumer-input" :placeholder="$t('consumer.branchPanel.descPlaceholder')" />
      <button class="consumer-branch-btn primary" :disabled="!branchState.newBranchName.value.trim() || branchState.creatingBranch.value" @click="doCreateBranch">
        <span v-if="branchState.creatingBranch.value" class="loading-spinner-small"></span>
        {{ $t('consumer.branchPanel.confirmCreate') }}
      </button>
    </div>

    <div v-if="branchState.selectedBranch.value" class="consumer-intervention-section">
      <div class="consumer-intervention-header">
        <span class="consumer-intervention-title">{{ $t('consumer.branchPanel.interventions') }}</span>
        <button class="consumer-branch-btn small" @click="branchState.showAddIntervention.value = !branchState.showAddIntervention.value">
          {{ branchState.showAddIntervention.value ? $t('common.cancel') : $t('consumer.branchPanel.addIntervention') }}
        </button>
      </div>

      <div v-if="branchState.showAddIntervention.value" class="consumer-intervention-form">
        <select v-model="branchState.newInterventionType.value" class="consumer-input">
          <option value="">{{ $t('consumer.branchPanel.selectType') }}</option>
          <option value="clarification_injection">{{ $t('consumer.interventionTypes.clarification_injection') }}</option>
          <option value="revised_claim_injection">{{ $t('consumer.interventionTypes.revised_claim_injection') }}</option>
          <option value="evidence_reveal">{{ $t('consumer.interventionTypes.evidence_reveal') }}</option>
        </select>
        <input v-model="branchState.newInterventionPayload.value" class="consumer-input" :placeholder="interventionPayloadPlaceholder" />
        <input v-model.number="branchState.newInterventionTargetRound.value" type="number" min="0" class="consumer-input narrow" :placeholder="$t('consumer.branchPanel.targetRoundPlaceholder')" />
        <button class="consumer-branch-btn primary" :disabled="!branchState.newInterventionType.value || !branchState.newInterventionPayload.value.trim() || branchState.addingIntervention.value" @click="doAddIntervention">
          <span v-if="branchState.addingIntervention.value" class="loading-spinner-small"></span>
          {{ $t('consumer.branchPanel.confirmAdd') }}
        </button>
      </div>

      <div v-if="branchState.branchInterventions.value.length > 0" class="consumer-intervention-list">
        <div v-for="intv in branchState.branchInterventions.value" :key="intv.intervention_id" class="consumer-intervention-item">
          <span class="intervention-type">{{ intv.intervention_type }}</span>
          <span class="intervention-payload">{{ getInterventionDisplayText(intv.intervention_type, intv.payload) }}</span>
          <span v-if="intv.target_round != null" class="intervention-round">R{{ intv.target_round }}</span>
        </div>
      </div>
      <div v-else class="consumer-intervention-empty">
        {{ $t('consumer.branchPanel.noInterventions') }}
      </div>

      <div class="consumer-branch-run-section">
        <button
          class="consumer-branch-btn primary"
          :disabled="branchState.runningBranch.value || (branchState.branchRunStatus.value && branchState.branchRunStatus.value.status === 'running')"
          @click="doRunBranch"
        >
          <span v-if="branchState.runningBranch.value" class="loading-spinner-small"></span>
          {{ branchState.runningBranch.value ? $t('consumer.branchPanel.running') : $t('consumer.branchPanel.runBranch') }}
        </button>
        <span v-if="branchState.branchRunStatus.value && branchState.branchRunStatus.value.status" class="branch-run-status-badge" :class="'status-' + branchState.branchRunStatus.value.status">
          {{ branchState.branchRunStatus.value.status }}
        </span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
// @ts-nocheck
import { computed, onMounted, onUnmounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useBranchInterventionState } from '../../composables/consumer/useBranchInterventionState'
import {
  listBranches,
  createBranch,
  listInterventions,
  addIntervention,
  runBranch,
  getBranchStatus,
} from '../../api/consumer'
import {
  loadSelectedBranch,
  saveSelectedBranch,
  clearSelectedBranch,
  buildInterventionPayload,
  getInterventionDisplayText,
  restorePersistedBranchSelectionAfterLoad,
} from '../../utils/consumerMode'

const props = defineProps({
  simulationId: String,
  isConsumerMode: Boolean,
  phase: Number,
})

const emit = defineEmits(['add-log'])

const branchState = useBranchInterventionState()
const { t } = useI18n()

const interventionPayloadPlaceholder = computed(() => {
  const map = {
    clarification_injection: t('consumer.branchPanel.payloadClarification'),
    revised_claim_injection: t('consumer.branchPanel.payloadRevisedClaim'),
    evidence_reveal: t('consumer.branchPanel.payloadEvidence'),
  }
  return map[branchState.newInterventionType.value] || t('consumer.branchPanel.payloadDefault')
})

let branchStatusTimer = null

const addLog = (msg) => {
  emit('add-log', msg)
}

const loadBranches = async () => {
  if (!props.simulationId || !props.isConsumerMode) return
  try {
    const res = await listBranches(props.simulationId)
    if (res.success && res.data) {
      branchState.branches.value = res.data.branches || []
      await restorePersistedBranchSelectionAfterLoad({
        branches: branchState.branches.value,
        persistedBranchId: loadSelectedBranch(props.simulationId),
        setSelectedBranchId: (id) => { branchState.selectedBranchId.value = id },
        loadInterventions,
        fetchBranchStatus,
        startPolling: startBranchStatusPolling,
        clearPersisted: () => clearSelectedBranch(props.simulationId),
      })
    }
  } catch (err) {
    console.warn('loadBranches failed:', err)
  }
}

const onBranchChange = async () => {
  saveSelectedBranch(props.simulationId, branchState.selectedBranchId.value || null)
  branchState.branchInterventions.value = []
  branchState.branchRunStatus.value = null
  stopBranchStatusPolling()
  if (branchState.selectedBranchId.value) {
    await loadInterventions()
    await fetchBranchStatus()
    if (branchState.branchRunStatus.value && branchState.branchRunStatus.value.status === 'running') {
      startBranchStatusPolling()
    }
  }
}

const doCreateBranch = async () => {
  if (!props.simulationId || !branchState.newBranchName.value.trim()) return
  branchState.creatingBranch.value = true
  try {
    const forkRound = Number.isFinite(branchState.newBranchForkRound.value) ? Math.max(0, Math.floor(branchState.newBranchForkRound.value)) : 0
    const res = await createBranch(props.simulationId, {
      name: branchState.newBranchName.value.trim(),
      fork_round: forkRound,
      description: branchState.newBranchDescription.value.trim(),
    })
    if (res.success && res.data) {
      addLog(`Branch created: ${res.data.name} (R${res.data.fork_round})`)
      await loadBranches()
      branchState.selectedBranchId.value = res.data.branch_id
      saveSelectedBranch(props.simulationId, res.data.branch_id)
      branchState.showCreateBranch.value = false
      branchState.newBranchName.value = ''
      branchState.newBranchForkRound.value = 0
      branchState.newBranchDescription.value = ''
      await loadInterventions()
    } else {
      addLog(`Create branch failed: ${res.error || 'unknown'}`)
    }
  } catch (err) {
    addLog(`Create branch error: ${err.message}`)
  } finally {
    branchState.creatingBranch.value = false
  }
}

const loadInterventions = async () => {
  if (!props.simulationId || !branchState.selectedBranchId.value) return
  try {
    const res = await listInterventions(props.simulationId, branchState.selectedBranchId.value)
    if (res.success && res.data) {
      branchState.branchInterventions.value = res.data.interventions || []
    }
  } catch (err) {
    console.warn('loadInterventions failed:', err)
  }
}

const doAddIntervention = async () => {
  if (!props.simulationId || !branchState.selectedBranchId.value || !branchState.newInterventionType.value) return
  branchState.addingIntervention.value = true
  try {
    const res = await addIntervention(props.simulationId, branchState.selectedBranchId.value, {
      intervention_type: branchState.newInterventionType.value,
      payload: buildInterventionPayload(branchState.newInterventionType.value, branchState.newInterventionPayload.value),
      target_round: Number.isFinite(branchState.newInterventionTargetRound.value) ? Math.max(0, Math.floor(branchState.newInterventionTargetRound.value)) : undefined,
    })
    if (res.success && res.data) {
      addLog(`Intervention added: ${res.data.intervention_type}`)
      await loadInterventions()
      branchState.showAddIntervention.value = false
      branchState.newInterventionType.value = ''
      branchState.newInterventionPayload.value = ''
      branchState.newInterventionTargetRound.value = null
    } else {
      addLog(`Add intervention failed: ${res.error || 'unknown'}`)
    }
  } catch (err) {
    addLog(`Add intervention error: ${err.message}`)
  } finally {
    branchState.addingIntervention.value = false
  }
}

const startBranchStatusPolling = () => {
  if (branchStatusTimer) {
    clearInterval(branchStatusTimer)
  }
  branchStatusTimer = setInterval(fetchBranchStatus, 2000)
}

const stopBranchStatusPolling = () => {
  if (branchStatusTimer) {
    clearInterval(branchStatusTimer)
    branchStatusTimer = null
  }
}

const fetchBranchStatus = async () => {
  if (!props.simulationId || !branchState.selectedBranchId.value) return
  try {
    const res = await getBranchStatus(props.simulationId, branchState.selectedBranchId.value)
    if (res.success && res.data) {
      branchState.branchRunStatus.value = res.data
      if (res.data.status === 'completed' || res.data.status === 'failed') {
        stopBranchStatusPolling()
        branchState.runningBranch.value = false
        if (res.data.status === 'completed') {
          addLog(`Branch run completed: ${branchState.selectedBranch.value?.name}`)
        } else {
          addLog(`Branch run failed: ${branchState.selectedBranch.value?.name}`)
        }
      }
      return res.data
    }
  } catch (err) {
    console.warn('fetchBranchStatus failed:', err)
  }
}

const doRunBranch = async () => {
  if (!props.simulationId || !branchState.selectedBranchId.value) return
  branchState.runningBranch.value = true
  try {
    const res = await runBranch(props.simulationId, branchState.selectedBranchId.value)
    if (res.success && res.data) {
      addLog(`Branch run started: ${branchState.selectedBranch.value?.name} (R${res.data.fork_round})`)
      branchState.branchRunStatus.value = { status: 'running' }
      startBranchStatusPolling()
    } else {
      addLog(`Branch run failed: ${res.error || 'unknown'}`)
      branchState.runningBranch.value = false
    }
  } catch (err) {
    addLog(`Branch run error: ${err.message}`)
    branchState.runningBranch.value = false
  }
}

onMounted(() => {
  if (props.isConsumerMode && props.simulationId) {
    loadBranches()
  }
})

watch(() => props.simulationId, () => {
  if (props.isConsumerMode && props.simulationId) {
    loadBranches()
  }
})

onUnmounted(() => {
  stopBranchStatusPolling()
})

defineExpose({
  loadBranches,
  branchState,
})
</script>

<style scoped>
/* --- Branch Panel --- */
.consumer-branch-panel {
  border-top: 1px solid #E5E7EB;
  padding-top: 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.consumer-branch-header {
  display: flex;
  align-items: center;
  gap: 10px;
}

.consumer-branch-title {
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: #374151;
}

.consumer-branch-badge {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  background: #EEF2FF;
  color: #4338CA;
  border-radius: 4px;
}

.consumer-branch-toolbar {
  display: flex;
  gap: 8px;
  align-items: center;
}

.consumer-branch-select {
  padding: 6px 10px;
  font-size: 13px;
  border: 1px solid var(--mc-border);
  border-radius: 4px;
  background: var(--mc-surface);
  min-width: 200px;
  color: var(--mc-text-primary);
}

.consumer-branch-btn {
  padding: 6px 12px;
  font-size: 12px;
  font-weight: 600;
  border: 1px solid var(--mc-border);
  border-radius: 4px;
  background: var(--mc-surface);
  color: var(--mc-text-secondary);
  cursor: pointer;
  transition: all 0.2s;
}

.consumer-branch-btn:hover:not(:disabled) {
  background: var(--mc-accent-wash);
  border-color: var(--mc-accent);
  color: var(--mc-accent);
}

.consumer-branch-btn.primary {
  background: var(--mc-accent);
  color: #fffdfa;
  border-color: var(--mc-accent);
}

.consumer-branch-btn.primary:hover:not(:disabled) {
  background: var(--mc-accent-strong);
}

.consumer-branch-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.consumer-branch-btn.small {
  padding: 4px 10px;
  font-size: 11px;
}

.consumer-branch-form,
.consumer-intervention-form {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.consumer-input {
  padding: 6px 10px;
  font-size: 13px;
  border: 1px solid var(--mc-border);
  border-radius: 4px;
  background: var(--mc-surface);
  color: var(--mc-text-primary);
  min-width: 180px;
}

.consumer-input.narrow {
  min-width: 80px;
  width: 100px;
}

.consumer-intervention-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 10px;
  background: var(--mc-bg-subtle);
  border-radius: 4px;
}

.consumer-intervention-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.consumer-intervention-title {
  font-size: 12px;
  font-weight: 700;
  color: var(--mc-text-primary);
}

.consumer-intervention-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.consumer-intervention-item {
  display: flex;
  gap: 10px;
  align-items: center;
  font-size: 12px;
  padding: 6px 8px;
  background: var(--mc-surface);
  border: 1px solid var(--mc-border);
  border-radius: 4px;
}

.consumer-intervention-item .intervention-type {
  font-weight: 600;
  color: var(--mc-accent);
  text-transform: uppercase;
  font-size: 10px;
  letter-spacing: 0.05em;
}

.consumer-intervention-item .intervention-payload {
  color: var(--mc-text-primary);
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.consumer-intervention-item .intervention-round {
  font-size: 10px;
  color: #6B7280;
  background: #F3F4F6;
  padding: 2px 6px;
  border-radius: 4px;
}

.consumer-intervention-empty {
  font-size: 12px;
  color: #9CA3AF;
}

/* Loading spinner for button */
.loading-spinner-small {
  display: inline-block;
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #FFF;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin-right: 6px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
