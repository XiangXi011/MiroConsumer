<template>
  <div v-if="isConsumerMode && isComplete" class="consumer-research-workspace">
    <div class="workspace-header" @click="showWorkspace = !showWorkspace">
      <span class="workspace-title">{{ $t('consumer.researchAssets.title') }}</span>
      <svg
        class="workspace-toggle-icon"
        :class="{ 'is-collapsed': !showWorkspace }"
        viewBox="0 0 24 24"
        width="16"
        height="16"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
      >
        <polyline points="6 9 12 15 18 9"></polyline>
      </svg>
    </div>

    <div v-show="showWorkspace" class="workspace-body">
      <!-- Export Pack -->
      <div class="workspace-section">
        <div class="workspace-section-title">{{ $t('consumer.researchAssets.exportPack') }}</div>
        <div class="workspace-row">
          <input
            v-model="assetState.assetExportName.value"
            class="workspace-input"
            :placeholder="$t('consumer.researchAssets.exportNamePlaceholder')"
            @keydown.enter.prevent="handleExportAsset"
          />
          <button
            class="workspace-btn"
            :disabled="assetState.exportingAsset.value || !projectId || !simulationId"
            @click="handleExportAsset"
          >
            <span v-if="assetState.exportingAsset.value" class="workspace-spinner"></span>
            <span v-else>{{ $t('consumer.researchAssets.exportPack') }}</span>
          </button>
        </div>
      </div>

      <!-- Existing Packs -->
      <div v-if="assetState.researchAssets.value.length > 0" class="workspace-section">
        <div class="workspace-section-title">{{ $t('consumer.researchAssets.existingPacks') }}</div>
        <div class="workspace-list">
          <div
            v-for="asset in assetState.researchAssets.value"
            :key="asset.asset_id"
            class="workspace-list-item"
          >
            <span class="workspace-item-name">{{ asset.name || asset.asset_id }}</span>
            <span class="workspace-item-meta mono">{{ asset.summary?.source_count || 0 }} src / {{ asset.summary?.finding_count || 0 }} findings</span>
          </div>
        </div>
      </div>

      <!-- Slot for comparison workspace -->
      <slot></slot>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useResearchAssetState } from '../../composables/consumer/useResearchAssetState'
import { exportResearchAsset, listResearchAssets } from '../../api/consumer'
import { loadSelectedBranch } from '../../utils/consumerMode'

const { t } = useI18n()

const props = defineProps({
  projectId: String,
  simulationId: String,
  isConsumerMode: Boolean,
  isComplete: Boolean,
})

const assetState = useResearchAssetState()
const showWorkspace = ref(true)

const loadResearchAssets = async () => {
  const pid = props.projectId
  if (!pid || !props.isConsumerMode) {
    assetState.researchAssets.value = []
    return
  }
  try {
    const res = await listResearchAssets(pid)
    if (res.success && res.data) {
      assetState.researchAssets.value = res.data.items || []
    }
  } catch (err) {
    console.warn('loadResearchAssets failed:', err)
  }
}

const handleExportAsset = async () => {
  const pid = props.projectId
  const sid = props.simulationId
  if (!pid || !sid || assetState.exportingAsset.value) return
  assetState.exportingAsset.value = true
  try {
    const branchId = loadSelectedBranch(sid)
    const res = await exportResearchAsset({
      project_id: pid,
      simulation_id: sid,
      branch_id: branchId || undefined,
      name: assetState.assetExportName.value.trim() || undefined,
    })
    if (res.success) {
      assetState.assetExportName.value = ''
      await loadResearchAssets()
    }
  } catch (err) {
    console.warn('exportResearchAsset failed:', err)
  } finally {
    assetState.exportingAsset.value = false
  }
}

watch(() => props.simulationId, () => {
  loadResearchAssets()
}, { immediate: true })

watch(() => props.projectId, () => {
  loadResearchAssets()
}, { immediate: true })

defineExpose({
  loadResearchAssets,
  researchAssets: assetState.researchAssets,
})
</script>

<style scoped>
.mono {
  font-family: 'JetBrains Mono', monospace;
}

.consumer-research-workspace {
  margin: 16px 0;
  background: #FAFAFA;
  border: 1px solid #E5E7EB;
  border-radius: 8px;
  overflow: hidden;
}

.workspace-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  background: linear-gradient(135deg, #F0FDF4 0%, #DCFCE7 100%);
  border-bottom: 1px solid #BBF7D0;
  cursor: pointer;
  user-select: none;
}

.workspace-title {
  font-size: 13px;
  font-weight: 600;
  color: #166534;
}

.workspace-toggle-icon {
  color: #166534;
  transition: transform 0.2s ease;
}

.workspace-toggle-icon.is-collapsed {
  transform: rotate(-90deg);
}

.workspace-body {
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 14px;
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

.workspace-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #FFFFFF;
  border-radius: 50%;
  animation: ws-spin 0.6s linear infinite;
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

.workspace-item-name {
  font-weight: 500;
  color: #374151;
}

.workspace-item-meta {
  font-size: 11px;
  color: #9CA3AF;
}
</style>
