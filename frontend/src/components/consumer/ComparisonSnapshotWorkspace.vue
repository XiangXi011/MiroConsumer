<template>
  <div v-if="isConsumerMode && hasData" class="comparison-snapshot-workspace">
    <!-- Branch Comparison Summary -->
    <div v-if="branchComparisonRaw" class="snapshot-section">
      <div class="snapshot-section-title">{{ $t('consumer.branchComparison.title') }}</div>
      <div class="snapshot-summary">
        <div class="snapshot-row">
          <span class="snapshot-label">{{ $t('consumer.branchComparison.forkRound') }}</span>
          <span class="snapshot-value mono">R{{ branchComparisonRaw.fork_round ?? 0 }}</span>
        </div>
        <div class="snapshot-row">
          <span class="snapshot-label">{{ $t('consumer.branchComparison.baseAcceptance') }}</span>
          <span class="snapshot-value mono">{{ branchAcceptancePct }}</span>
        </div>
        <div class="snapshot-row">
          <span class="snapshot-label">{{ $t('consumer.branchComparison.branchAcceptance') }}</span>
          <span class="snapshot-value mono" :class="{ 'delta-positive': branchDelta >= 0, 'delta-negative': branchDelta < 0 }">
            {{ branchBranchAcceptancePct }}
          </span>
        </div>
        <div class="snapshot-row">
          <span class="snapshot-label">{{ $t('consumer.branchComparison.delta') }}</span>
          <span class="snapshot-value mono" :class="{ 'delta-positive': branchDelta >= 0, 'delta-negative': branchDelta < 0 }">
            {{ branchDeltaText }}
          </span>
        </div>
      </div>
    </div>

    <!-- Comparison Snapshot Summary -->
    <div v-if="effectiveSnapshot" class="snapshot-section">
      <div class="snapshot-section-title">{{ $t('consumer.researchAssets.comparisonResult') }}</div>
      <div class="snapshot-badge">{{ effectiveSnapshot.mode }}</div>
      <div class="snapshot-sides">
        <div class="snapshot-side">
          <span class="snapshot-side-label">{{ $t('consumer.researchAssets.left') }}</span>
          <span class="snapshot-side-value mono">{{ leftAcceptance }}</span>
        </div>
        <div class="snapshot-side">
          <span class="snapshot-side-label">{{ $t('consumer.researchAssets.right') }}</span>
          <span class="snapshot-side-value mono">{{ rightAcceptance }}</span>
        </div>
      </div>
      <div class="snapshot-row">
        <span class="snapshot-label">{{ $t('consumer.researchAssets.acceptanceDelta') }}</span>
        <span class="snapshot-value mono" :class="{ 'delta-positive': (effectiveSnapshot.acceptance_delta_pp || 0) >= 0, 'delta-negative': (effectiveSnapshot.acceptance_delta_pp || 0) < 0 }">
          {{ (effectiveSnapshot.acceptance_delta_pp || 0) >= 0 ? '+' : '' }}{{ Math.round(effectiveSnapshot.acceptance_delta_pp || 0) }}pp
        </span>
      </div>
      <div v-if="comparisonConfidence" class="snapshot-row">
        <span class="snapshot-label">{{ $t('consumer.comparisonConfidence.title') }}</span>
        <span class="snapshot-value mono" :class="getConfidenceBadgeClass(comparisonConfidence.label)">
          {{ getConfidenceLabelText(comparisonConfidence.label, t) }}
        </span>
      </div>
      <div class="snapshot-row">
        <span class="snapshot-label">{{ $t('consumer.researchAssets.resonanceOverlap') }}</span>
        <span class="snapshot-value mono">{{ (effectiveSnapshot.resonance_overlap || []).length > 0 ? effectiveSnapshot.resonance_overlap.join(', ') : '—' }}</span>
      </div>
      <div class="snapshot-row">
        <span class="snapshot-label">{{ $t('consumer.researchAssets.recurringRisks') }}</span>
        <span class="snapshot-value mono">{{ (effectiveSnapshot.recurring_risk_signals || []).length > 0 ? effectiveSnapshot.recurring_risk_signals.join(', ') : '—' }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { getComparison, getBranchComparison } from '../../api/consumer'
import { useComparisonState } from '../../composables/consumer/useComparisonState'
import {
  loadSelectedBranch,
  clearSelectedBranch,
  loadSelectedComparison,
  formatComparisonConfidence,
  getConfidenceBadgeClass,
  getConfidenceLabelText,
} from '../../utils/consumerMode'

const { t } = useI18n()
const comparisonState = useComparisonState()

const props = defineProps({
  simulationId: String,
  isConsumerMode: Boolean,
  comparisonSnapshot: Object,
})

const emit = defineEmits(['update:branchComparison', 'update:comparisonSnapshot'])

const { branchComparisonRaw, comparisonSnapshot: comparisonSnapshotLocal } = comparisonState

const effectiveSnapshot = computed(() => props.comparisonSnapshot || comparisonSnapshotLocal.value)

const hasData = computed(() => !!branchComparisonRaw.value || !!effectiveSnapshot.value)

const branchBase = computed(() => branchComparisonRaw.value?.base_summary || {})
const branchBranch = computed(() => branchComparisonRaw.value?.branch_summary || {})

const branchAcceptancePct = computed(() => {
  const val = branchBase.value.post_propagation_acceptance?.positive ?? branchBase.value.initial_acceptance?.positive ?? 0
  return `${Math.round(val * 100)}%`
})

const branchBranchAcceptancePct = computed(() => {
  const val = branchBranch.value.post_propagation_acceptance?.positive ?? branchBranch.value.initial_acceptance?.positive ?? 0
  return `${Math.round(val * 100)}%`
})

const branchDelta = computed(() => {
  const base = branchBase.value.post_propagation_acceptance?.positive ?? branchBase.value.initial_acceptance?.positive ?? 0
  const branch = branchBranch.value.post_propagation_acceptance?.positive ?? branchBranch.value.initial_acceptance?.positive ?? 0
  return branch - base
})

const branchDeltaText = computed(() => {
  const delta = branchDelta.value
  return delta >= 0 ? `+${Math.round(delta * 100)}pp` : `${Math.round(delta * 100)}pp`
})

const leftAcceptance = computed(() => {
  const val = effectiveSnapshot.value?.left?.acceptance_positive
  return val != null ? `${Math.round(val * 100)}%` : '—'
})

const rightAcceptance = computed(() => {
  const val = effectiveSnapshot.value?.right?.acceptance_positive
  return val != null ? `${Math.round(val * 100)}%` : '—'
})

const comparisonConfidence = computed(() => {
  const cc = effectiveSnapshot.value?.comparison_confidence
  if (!cc) return null
  return formatComparisonConfidence(cc)
})

const loadComparison = async () => {
  if (!props.isConsumerMode || !props.simulationId) {
    comparisonSnapshotLocal.value = null
    emit('update:comparisonSnapshot', null)
    return
  }
  if (props.comparisonSnapshot) {
    comparisonSnapshotLocal.value = null
    emit('update:comparisonSnapshot', props.comparisonSnapshot)
    return
  }
  const comparisonId = loadSelectedComparison(props.simulationId)
  if (!comparisonId) {
    comparisonSnapshotLocal.value = null
    emit('update:comparisonSnapshot', null)
    return
  }
  try {
    const res = await getComparison(comparisonId)
    if (res.success && res.data) {
      comparisonSnapshotLocal.value = res.data
      emit('update:comparisonSnapshot', res.data)
    } else {
      comparisonSnapshotLocal.value = null
      emit('update:comparisonSnapshot', null)
    }
  } catch (err) {
    console.warn('loadComparison failed:', err)
    comparisonSnapshotLocal.value = null
    emit('update:comparisonSnapshot', null)
  }
}

const loadBranchComparison = async () => {
  if (!props.isConsumerMode || !props.simulationId) {
    branchComparisonRaw.value = null
    emit('update:branchComparison', null)
    return
  }
  const branchId = loadSelectedBranch(props.simulationId)
  if (!branchId) {
    branchComparisonRaw.value = null
    emit('update:branchComparison', null)
    return
  }
  try {
    const res = await getBranchComparison(props.simulationId, branchId)
    if (res.success && res.data) {
      branchComparisonRaw.value = res.data
      emit('update:branchComparison', res.data)
    } else {
      clearSelectedBranch(props.simulationId)
      branchComparisonRaw.value = null
      emit('update:branchComparison', null)
    }
  } catch (err) {
    console.warn('loadBranchComparison failed:', err)
    clearSelectedBranch(props.simulationId)
    branchComparisonRaw.value = null
    emit('update:branchComparison', null)
  }
}

watch([() => props.simulationId, () => props.isConsumerMode], () => {
  loadComparison()
  loadBranchComparison()
}, { immediate: true })

watch(() => props.comparisonSnapshot, () => {
  loadComparison()
})

defineExpose({
  branchComparisonRaw,
  comparisonSnapshotLocal,
  reload: () => {
    loadComparison()
    loadBranchComparison()
  },
})
</script>

<style scoped>
.comparison-snapshot-workspace {
  border-bottom: 1px solid #E5E7EB;
  background: #FFFDFB;
  padding: 12px 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.mono {
  font-family: 'JetBrains Mono', monospace;
}

.snapshot-section {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.snapshot-section-title {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #6B7280;
}

.snapshot-badge {
  display: inline-block;
  padding: 2px 8px;
  background: #F3F4F6;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  color: #6B7280;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.snapshot-summary {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.snapshot-row {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 12px;
}

.snapshot-label {
  color: #6B7280;
  min-width: 120px;
}

.snapshot-value {
  font-weight: 600;
  color: #111827;
}

.snapshot-sides {
  display: flex;
  gap: 10px;
}

.snapshot-side {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 6px 8px;
  background: #F9FAFB;
  border-radius: 4px;
  text-align: center;
}

.snapshot-side-label {
  font-size: 10px;
  font-weight: 600;
  color: #9CA3AF;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.snapshot-side-value {
  font-size: 14px;
  font-weight: 700;
  color: #111827;
}

.delta-positive {
  color: #059669;
}

.delta-negative {
  color: #DC2626;
}

.badge-high {
  background: #D1FAE5;
  color: #065F46;
  padding: 2px 6px;
  border-radius: 4px;
}

.badge-medium {
  background: #FEF3C7;
  color: #92400E;
  padding: 2px 6px;
  border-radius: 4px;
}

.badge-low {
  background: #FEE2E2;
  color: #991B1B;
  padding: 2px 6px;
  border-radius: 4px;
}

.badge-unknown {
  background: #F3F4F6;
  color: #6B7280;
  padding: 2px 6px;
  border-radius: 4px;
}
</style>
