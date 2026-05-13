// @ts-nocheck
import { ref } from 'vue'

export function useComparisonState() {
  const branchComparisonRaw = ref(null)
  const comparisons = ref([])
  const comparisonSnapshot = ref(null)
  const comparing = ref(false)
  const compareTargetSimId = ref('')
  const compareTargetProjectId = ref('')

  function setComparisons(list) {
    comparisons.value = list
  }

  function addComparison(item) {
    comparisons.value = [...comparisons.value, item]
  }

  function removeComparison(id) {
    comparisons.value = comparisons.value.filter(c => c.id !== id)
  }

  function setComparisonSnapshot(snapshot) {
    comparisonSnapshot.value = snapshot
  }

  function setComparing(flag) {
    comparing.value = flag
  }

  function reset() {
    branchComparisonRaw.value = null
    comparisons.value = []
    comparisonSnapshot.value = null
    comparing.value = false
    compareTargetSimId.value = ''
    compareTargetProjectId.value = ''
  }

  return {
    branchComparisonRaw,
    comparisons,
    comparisonSnapshot,
    comparing,
    compareTargetSimId,
    compareTargetProjectId,
    setComparisons,
    addComparison,
    removeComparison,
    setComparisonSnapshot,
    setComparing,
    reset
  }
}
