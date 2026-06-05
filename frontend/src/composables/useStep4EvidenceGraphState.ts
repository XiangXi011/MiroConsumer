// @ts-nocheck
import { ref } from 'vue'

let defaultEvidenceGraphApiPromise = null

async function loadDefaultEvidenceGraphApi() {
  if (!defaultEvidenceGraphApiPromise) {
    defaultEvidenceGraphApiPromise = import('../api/consumer')
      .then(api => api.getReportEvidenceGraph)
  }
  return defaultEvidenceGraphApiPromise
}

export function useStep4EvidenceGraphState({
  reportId,
  isConsumerMode,
  getReportEvidenceGraph = null,
} = {}) {
  const evidenceGraph = ref(null)
  const evidenceGraphLoading = ref(false)
  const evidenceGraphError = ref('')

  const resetEvidenceGraph = () => {
    evidenceGraph.value = null
    evidenceGraphError.value = ''
    evidenceGraphLoading.value = false
  }

  const loadEvidenceGraph = async () => {
    if (!reportId.value || !isConsumerMode.value) {
      resetEvidenceGraph()
      return
    }

    evidenceGraphLoading.value = true
    evidenceGraphError.value = ''
    try {
      const loadGraph = getReportEvidenceGraph || await loadDefaultEvidenceGraphApi()
      const res = await loadGraph(reportId.value)
      if (res.success && res.data) {
        evidenceGraph.value = res.data
      } else {
        evidenceGraph.value = null
        evidenceGraphError.value = res.error || 'Evidence graph unavailable'
      }
    } catch (err) {
      evidenceGraph.value = null
      evidenceGraphError.value = err?.message || 'Evidence graph unavailable'
    } finally {
      evidenceGraphLoading.value = false
    }
  }

  return {
    evidenceGraph,
    evidenceGraphLoading,
    evidenceGraphError,
    resetEvidenceGraph,
    loadEvidenceGraph,
  }
}
