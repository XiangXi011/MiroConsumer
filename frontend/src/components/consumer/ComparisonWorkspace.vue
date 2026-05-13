<template>
  <div class="workspace-section">
    <div class="workspace-section-title">{{ $t('consumer.researchAssets.comparisons') }}</div>

    <!-- Compare Branch vs Base -->
    <div v-if="branchComparisonFormatted" class="workspace-row">
      <button
        class="workspace-btn secondary"
        :disabled="compState.comparing.value"
        @click="handleCompareBranchVsBase"
      >
        <span v-if="compState.comparing.value" class="workspace-spinner"></span>
        <span v-else>{{ $t('consumer.researchAssets.compareBranchVsBase') }}</span>
      </button>
    </div>

    <!-- Compare Run vs Run -->
    <div class="workspace-row">
      <input
        v-model="compState.compareTargetSimId.value"
        class="workspace-input"
        :placeholder="$t('consumer.researchAssets.rightSimIdPlaceholder')"
        @keydown.enter.prevent="handleCompareRunVsRun"
      />
      <button
        class="workspace-btn secondary"
        :disabled="compState.comparing.value || !compState.compareTargetSimId.value.trim() || !simulationId"
        @click="handleCompareRunVsRun"
      >
        <span v-if="compState.comparing.value" class="workspace-spinner"></span>
        <span v-else>{{ $t('consumer.researchAssets.runComparison') }}</span>
      </button>
    </div>

    <!-- Compare Project vs Project -->
    <div class="workspace-row">
      <input
        v-model="compState.compareTargetProjectId.value"
        class="workspace-input"
        :placeholder="$t('consumer.researchAssets.rightProjectIdPlaceholder')"
        @keydown.enter.prevent="handleCompareProjectVsProject"
      />
      <button
        class="workspace-btn secondary"
        :disabled="compState.comparing.value || !compState.compareTargetProjectId.value.trim() || !projectId"
        @click="handleCompareProjectVsProject"
      >
        <span v-if="compState.comparing.value" class="workspace-spinner"></span>
        <span v-else>{{ $t('consumer.researchAssets.runComparison') }}</span>
      </button>
    </div>

    <!-- Saved Comparisons -->
    <div v-if="compState.comparisons.value.length > 0" class="workspace-list">
      <div
        v-for="c in compState.comparisons.value"
        :key="c.comparison_id"
        class="workspace-list-item clickable"
        @click="loadComparisonById(c.comparison_id)"
      >
        <span class="workspace-item-name">{{ c.mode }}</span>
        <span class="workspace-item-meta mono">{{ c.left?.label || '—' }} vs {{ c.right?.label || '—' }}</span>
      </div>
    </div>
  </div>

  <!-- Comparison Snapshot Result -->
  <div v-if="compState.comparisonSnapshot.value" class="workspace-section comparison-result">
    <div class="workspace-section-header">
      <span class="workspace-section-title">{{ $t('consumer.researchAssets.comparisonResult') }}</span>
      <button class="workspace-close-btn" @click="clearComparisonSnapshot">
        <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="18" y1="6" x2="6" y2="18"></line>
          <line x1="6" y1="6" x2="18" y2="18"></line>
        </svg>
      </button>
    </div>

    <!-- Mode label -->
    <div class="comparison-mode-badge">{{ compState.comparisonSnapshot.value.mode }}</div>

    <!-- Side-by-side summary -->
    <div class="comparison-sides">
      <div class="comparison-side">
        <span class="comparison-side-label">{{ $t('consumer.researchAssets.left') }}</span>
        <span class="comparison-side-value mono">{{ compState.comparisonSnapshot.value.left?.acceptance_positive != null ? Math.round(compState.comparisonSnapshot.value.left.acceptance_positive * 100) + '%' : '—' }}</span>
      </div>
      <div class="comparison-side">
        <span class="comparison-side-label">{{ $t('consumer.researchAssets.right') }}</span>
        <span class="comparison-side-value mono">{{ compState.comparisonSnapshot.value.right?.acceptance_positive != null ? Math.round(compState.comparisonSnapshot.value.right.acceptance_positive * 100) + '%' : '—' }}</span>
      </div>
    </div>

    <!-- Acceptance Delta -->
    <div class="comparison-metric">
      <span class="comparison-metric-label">{{ $t('consumer.researchAssets.acceptanceDelta') }}</span>
      <span class="comparison-metric-value mono" :class="{ 'delta-positive': (compState.comparisonSnapshot.value.acceptance_delta_pp || 0) >= 0, 'delta-negative': (compState.comparisonSnapshot.value.acceptance_delta_pp || 0) < 0 }">
        {{ (compState.comparisonSnapshot.value.acceptance_delta_pp || 0) >= 0 ? '+' : '' }}{{ Math.round(compState.comparisonSnapshot.value.acceptance_delta_pp || 0) }}pp
      </span>
    </div>

    <!-- Source Overlap -->
    <div class="comparison-metric">
      <span class="comparison-metric-label">{{ $t('consumer.researchAssets.sourceOverlap') }}</span>
      <span class="comparison-metric-value mono">{{ compState.comparisonSnapshot.value.source_overlap_count ?? '—' }}</span>
    </div>

    <!-- Comparison Confidence -->
    <div v-if="comparisonConfidenceFormatted" class="comparison-confidence-section">
      <span class="comparison-list-label">{{ $t('consumer.comparisonConfidence.title') }}</span>
      <div class="comparison-confidence-grid">
        <div class="comparison-confidence-side">
          <span class="comparison-confidence-label">{{ $t('consumer.researchAssets.left') }}</span>
          <span class="comparison-confidence-value mono" :class="getConfidenceBadgeClass(comparisonConfidenceFormatted.leftLabel)">{{ getConfidenceLabelText(comparisonConfidenceFormatted.leftLabel, t) }}</span>
        </div>
        <div class="comparison-confidence-side">
          <span class="comparison-confidence-label">{{ $t('consumer.researchAssets.right') }}</span>
          <span class="comparison-confidence-value mono" :class="getConfidenceBadgeClass(comparisonConfidenceFormatted.rightLabel)">{{ getConfidenceLabelText(comparisonConfidenceFormatted.rightLabel, t) }}</span>
        </div>
      </div>
    </div>

    <!-- Resonance Overlap -->
    <div class="comparison-list-section">
      <span class="comparison-list-label">{{ $t('consumer.researchAssets.resonanceOverlap') }}</span>
      <div v-if="(compState.comparisonSnapshot.value.resonance_overlap || []).length > 0" class="comparison-chip-list">
        <span v-for="(item, idx) in compState.comparisonSnapshot.value.resonance_overlap" :key="idx" class="comparison-chip">{{ item }}</span>
      </div>
      <span v-else class="comparison-empty">{{ $t('consumer.researchAssets.noResonanceOverlap') }}</span>
    </div>

    <!-- Recurring Risk Signals -->
    <div class="comparison-list-section">
      <span class="comparison-list-label">{{ $t('consumer.researchAssets.recurringRisks') }}</span>
      <div v-if="(compState.comparisonSnapshot.value.recurring_risk_signals || []).length > 0" class="comparison-chip-list">
        <span v-for="(item, idx) in compState.comparisonSnapshot.value.recurring_risk_signals" :key="idx" class="comparison-chip risk">{{ item }}</span>
      </div>
      <span v-else class="comparison-empty">{{ $t('consumer.researchAssets.noRecurringRisks') }}</span>
    </div>

    <!-- Evidence-Backed Divergences -->
    <div class="comparison-list-section">
      <span class="comparison-list-label">{{ $t('consumer.researchAssets.evidenceBackedDivergences') }}</span>
      <div v-if="(compState.comparisonSnapshot.value.evidence_backed_divergences || []).length > 0" class="comparison-divergence-list">
        <div v-for="(div, idx) in compState.comparisonSnapshot.value.evidence_backed_divergences" :key="idx" class="comparison-divergence-item">
          <span class="divergence-signal">{{ div.signal }}</span>
          <div class="divergence-presence">
            <span class="presence-badge" :class="{ present: div.left_presence, absent: !div.left_presence }">
              {{ $t('consumer.researchAssets.left') }}: {{ div.left_presence ? $t('consumer.researchAssets.presencePresent') : $t('consumer.researchAssets.presenceAbsent') }}
            </span>
            <span class="presence-badge" :class="{ present: div.right_presence, absent: !div.right_presence }">
              {{ $t('consumer.researchAssets.right') }}: {{ div.right_presence ? $t('consumer.researchAssets.presencePresent') : $t('consumer.researchAssets.presenceAbsent') }}
            </span>
          </div>
          <div v-if="(div.left_sources || []).length > 0" class="divergence-sources">
            <span class="sources-label">{{ $t('consumer.researchAssets.left') }}:</span>
            <span v-for="(src, sidx) in div.left_sources" :key="sidx" class="source-tag">{{ src }}</span>
          </div>
          <div v-if="(div.right_sources || []).length > 0" class="divergence-sources">
            <span class="sources-label">{{ $t('consumer.researchAssets.right') }}:</span>
            <span v-for="(src, sidx) in div.right_sources" :key="sidx" class="source-tag">{{ src }}</span>
          </div>
        </div>
      </div>
      <span v-else class="comparison-empty">{{ $t('consumer.researchAssets.noDivergences') }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
// @ts-nocheck
import { computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useComparisonState } from '../../composables/consumer/useComparisonState'
import { compareResearchSnapshots, listComparisons, getComparison } from '../../api/consumer'
import {
  loadSelectedBranch,
  saveSelectedComparison,
  clearSelectedComparison,
  formatComparisonConfidence,
  getConfidenceBadgeClass,
  getConfidenceLabelText,
} from '../../utils/consumerMode'

const { t } = useI18n()

const props = defineProps({
  projectId: String,
  simulationId: String,
  isConsumerMode: Boolean,
  branchComparisonFormatted: Object,
})

const compState = useComparisonState()

const comparisonConfidenceFormatted = computed(() => {
  if (!compState.comparisonSnapshot.value?.comparison_confidence) return null
  return formatComparisonConfidence(compState.comparisonSnapshot.value.comparison_confidence)
})

const loadComparisons = async () => {
  const pid = props.projectId
  if (!pid || !props.isConsumerMode) {
    compState.comparisons.value = []
    return
  }
  try {
    const res = await listComparisons(pid)
    if (res.success && res.data) {
      compState.comparisons.value = res.data.items || []
    }
  } catch (err) {
    console.warn('loadComparisons failed:', err)
  }
}

const handleCompareBranchVsBase = async () => {
  const sid = props.simulationId
  const branchId = sid ? loadSelectedBranch(sid) : null
  if (!sid || !branchId || compState.comparing.value) return
  compState.comparing.value = true
  try {
    const res = await compareResearchSnapshots({
      mode: 'branch_vs_base',
      simulation_id: sid,
      branch_id: branchId,
    })
    if (res.success && res.data) {
      compState.comparisonSnapshot.value = res.data
      if (res.data.comparison_id) {
        saveSelectedComparison(sid, res.data.comparison_id)
      }
    }
  } catch (err) {
    console.warn('compareBranchVsBase failed:', err)
  } finally {
    compState.comparing.value = false
  }
}

const handleCompareRunVsRun = async () => {
  const leftSid = props.simulationId
  const rightSid = compState.compareTargetSimId.value.trim()
  if (!leftSid || !rightSid || compState.comparing.value) return
  compState.comparing.value = true
  try {
    const res = await compareResearchSnapshots({
      mode: 'run_vs_run',
      left_simulation_id: leftSid,
      right_simulation_id: rightSid,
    })
    if (res.success && res.data) {
      compState.comparisonSnapshot.value = res.data
      if (res.data.comparison_id) {
        saveSelectedComparison(leftSid, res.data.comparison_id)
      }
    }
  } catch (err) {
    console.warn('compareRunVsRun failed:', err)
  } finally {
    compState.comparing.value = false
  }
}

const handleCompareProjectVsProject = async () => {
  const leftPid = props.projectId
  const rightPid = compState.compareTargetProjectId.value.trim()
  const sid = props.simulationId
  if (!leftPid || !rightPid || compState.comparing.value) return
  compState.comparing.value = true
  try {
    const res = await compareResearchSnapshots({
      mode: 'project_vs_project',
      left_project_id: leftPid,
      right_project_id: rightPid,
    })
    if (res.success && res.data) {
      compState.comparisonSnapshot.value = res.data
      if (res.data.comparison_id && sid) {
        saveSelectedComparison(sid, res.data.comparison_id)
      }
    }
  } catch (err) {
    console.warn('compareProjectVsProject failed:', err)
  } finally {
    compState.comparing.value = false
  }
}

const loadComparisonById = async (comparisonId) => {
  if (!comparisonId) return
  try {
    const res = await getComparison(comparisonId)
    if (res.success && res.data) {
      compState.comparisonSnapshot.value = res.data
      if (props.simulationId) {
        saveSelectedComparison(props.simulationId, comparisonId)
      }
    }
  } catch (err) {
    console.warn('loadComparisonById failed:', err)
  }
}

const clearComparisonSnapshot = () => {
  compState.comparisonSnapshot.value = null
  if (props.simulationId) {
    clearSelectedComparison(props.simulationId)
  }
}

watch(() => props.simulationId, () => {
  loadComparisons()
}, { immediate: true })

watch(() => props.projectId, () => {
  loadComparisons()
}, { immediate: true })

defineExpose({
  loadComparisons,
  comparisons: compState.comparisons,
})
</script>

<style scoped>
.mono {
  font-family: 'JetBrains Mono', monospace;
}

.workspace-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.workspace-section-title {
  font-size: 11px;
  font-weight: 600;
  color: #6B7280;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.workspace-section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.workspace-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.workspace-input {
  flex: 1;
  min-width: 120px;
  padding: 6px 10px;
  background: #FFFFFF;
  border: 1px solid #D1D5DB;
  border-radius: 6px;
  font-size: 12px;
  color: #374151;
  outline: none;
  transition: border-color 0.15s ease;
}

.workspace-input:focus {
  border-color: #22C55E;
  box-shadow: 0 0 0 2px rgba(34, 197, 94, 0.1);
}

.workspace-input::placeholder {
  color: #9CA3AF;
}

.workspace-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: #22C55E;
  color: #FFFFFF;
  border: none;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
  white-space: nowrap;
}

.workspace-btn:hover:not(:disabled) {
  background: #16A34A;
}

.workspace-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.workspace-btn.secondary {
  background: #F3F4F6;
  color: #374151;
  border: 1px solid #E5E7EB;
}

.workspace-btn.secondary:hover:not(:disabled) {
  background: #E5E7EB;
}

.workspace-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #FFFFFF;
  border-radius: 50%;
  animation: ws-spin 0.6s linear infinite;
}

.workspace-btn.secondary .workspace-spinner {
  border-color: rgba(55, 65, 81, 0.2);
  border-top-color: #374151;
}

@keyframes ws-spin {
  to { transform: rotate(360deg); }
}

.workspace-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.workspace-list-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 10px;
  background: #FFFFFF;
  border: 1px solid #E5E7EB;
  border-radius: 6px;
  font-size: 12px;
}

.workspace-list-item.clickable {
  cursor: pointer;
  transition: all 0.15s ease;
}

.workspace-list-item.clickable:hover {
  border-color: #22C55E;
  background: #F0FDF4;
}

.workspace-item-name {
  font-weight: 500;
  color: #374151;
}

.workspace-item-meta {
  font-size: 11px;
  color: #9CA3AF;
}

.workspace-close-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  padding: 0;
  background: transparent;
  border: none;
  border-radius: 4px;
  color: #9CA3AF;
  cursor: pointer;
  transition: all 0.15s ease;
}

.workspace-close-btn:hover {
  background: #F3F4F6;
  color: #374151;
}

.comparison-result {
  background: #FFFFFF;
  border: 1px solid #E5E7EB;
  border-radius: 6px;
  padding: 12px;
}

.comparison-mode-badge {
  display: inline-block;
  padding: 2px 8px;
  background: #F3F4F6;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  color: #6B7280;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  margin-bottom: 10px;
}

.comparison-sides {
  display: flex;
  gap: 12px;
  margin-bottom: 10px;
}

.comparison-side {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px;
  background: #F9FAFB;
  border-radius: 6px;
  text-align: center;
}

.comparison-side-label {
  font-size: 11px;
  font-weight: 600;
  color: #9CA3AF;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.comparison-side-value {
  font-size: 18px;
  font-weight: 700;
  color: #111827;
}

.comparison-metric {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid #F3F4F6;
}

.comparison-metric-label {
  font-size: 12px;
  color: #6B7280;
}

.comparison-metric-value {
  font-size: 14px;
  font-weight: 600;
  color: #111827;
}

.delta-positive {
  color: #059669;
}

.delta-negative {
  color: #DC2626;
}

.comparison-list-section {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 8px 0;
  border-bottom: 1px solid #F3F4F6;
}

.comparison-list-section:last-child {
  border-bottom: none;
}

.comparison-list-label {
  font-size: 11px;
  font-weight: 600;
  color: #6B7280;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.comparison-chip-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.comparison-chip {
  display: inline-flex;
  padding: 3px 8px;
  background: #ECFDF5;
  color: #065F46;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 500;
}

.comparison-chip.risk {
  background: #FEF2F2;
  color: #991B1B;
}

.comparison-empty {
  font-size: 12px;
  color: #9CA3AF;
  font-style: italic;
}

.comparison-divergence-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.comparison-divergence-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 10px;
  background: #FAFAFA;
  border: 1px solid #E5E7EB;
  border-radius: 6px;
}

.divergence-signal {
  font-size: 13px;
  font-weight: 600;
  color: #374151;
}

.divergence-presence {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.presence-badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 500;
}

.presence-badge.present {
  background: #ECFDF5;
  color: #065F46;
}

.presence-badge.absent {
  background: #F3F4F6;
  color: #9CA3AF;
}

.divergence-sources {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
}

.sources-label {
  font-size: 11px;
  font-weight: 600;
  color: #6B7280;
}

.source-tag {
  font-size: 10px;
  padding: 2px 6px;
  background: #F3F4F6;
  color: #4B5563;
  border-radius: 4px;
}

.comparison-confidence-section {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #E5E7EB;
}

.comparison-confidence-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin-top: 6px;
}

.comparison-confidence-side {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.comparison-confidence-label {
  font-size: 11px;
  color: #6B7280;
}

.comparison-confidence-value {
  font-size: 13px;
  font-weight: 600;
}

.badge-high {
  background: #D1FAE5;
  color: #065F46;
}

.badge-medium {
  background: #FEF3C7;
  color: #92400E;
}

.badge-low {
  background: #FEE2E2;
  color: #991B1B;
}

.badge-unknown {
  background: #F3F4F6;
  color: #6B7280;
}
</style>
