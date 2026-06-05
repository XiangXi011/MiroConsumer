// @ts-nocheck
import { computed, ref } from 'vue'
import {
  loadSelectedBranch,
  formatBranchComparison,
  clearSelectedBranch,
} from '../utils/consumerMode'

let defaultBranchComparisonApiPromise = null

async function loadDefaultBranchComparisonApi() {
  if (!defaultBranchComparisonApiPromise) {
    defaultBranchComparisonApiPromise = import('../api/consumer')
      .then(api => api.getBranchComparison)
  }
  return defaultBranchComparisonApiPromise
}

export function useStep4BranchComparisonState({
  simulationId,
  isConsumerMode,
  t,
  getBranchComparison = null,
  warn = console.warn,
} = {}) {
  const branchComparisonRaw = ref(null)
  const branchComparisonFormatted = computed(() => {
    if (!branchComparisonRaw.value) return null
    return formatBranchComparison(branchComparisonRaw.value, t)
  })

  const clearBranchComparison = () => {
    branchComparisonRaw.value = null
  }

  const loadBranchComparison = async () => {
    if (!simulationId.value || !isConsumerMode.value) {
      clearBranchComparison()
      return
    }

    const branchId = loadSelectedBranch(simulationId.value)
    if (!branchId) {
      clearBranchComparison()
      return
    }

    try {
      const loadComparison = getBranchComparison || await loadDefaultBranchComparisonApi()
      const res = await loadComparison(simulationId.value, branchId)
      if (res.success && res.data) {
        branchComparisonRaw.value = res.data
      } else {
        clearSelectedBranch(simulationId.value)
        clearBranchComparison()
      }
    } catch (err) {
      warn('loadBranchComparison failed:', err)
      clearSelectedBranch(simulationId.value)
      clearBranchComparison()
    }
  }

  return {
    branchComparisonRaw,
    branchComparisonFormatted,
    clearBranchComparison,
    loadBranchComparison,
  }
}
