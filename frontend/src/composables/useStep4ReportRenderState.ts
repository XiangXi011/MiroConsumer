// @ts-nocheck
import { ref } from 'vue'
import { deriveReportRenderState } from '../utils/reportContent'
import { applyReportStatePatch } from '../utils/reportWorkflow'

export function useStep4ReportRenderState({
  emitUpdateStatus = () => {},
  stopPolling = () => {},
} = {}) {
  const reportOutline = ref(null)
  const currentSectionIndex = ref(null)
  const generatedSections = ref({})
  const expandedContent = ref(new Set())
  const collapsedSections = ref(new Set())
  const isComplete = ref(false)
  const startTime = ref(null)

  const applyReportRenderState = (reportData) => {
    const state = deriveReportRenderState(reportData)
    if (!state.isComplete) return
    isComplete.value = true
    reportOutline.value = state.outline
    generatedSections.value = state.generatedSections
  }

  const resetReportRenderState = () => {
    reportOutline.value = null
    currentSectionIndex.value = null
    generatedSections.value = {}
    expandedContent.value = new Set()
    collapsedSections.value = new Set()
    isComplete.value = false
    startTime.value = null
  }

  const toggleSectionContent = (idx) => {
    if (!generatedSections.value[idx + 1]) return
    const newSet = new Set(expandedContent.value)
    if (newSet.has(idx)) {
      newSet.delete(idx)
    } else {
      newSet.add(idx)
    }
    expandedContent.value = newSet
  }

  const toggleSectionCollapse = (idx) => {
    if (!generatedSections.value[idx + 1]) return
    const newSet = new Set(collapsedSections.value)
    if (newSet.has(idx)) {
      newSet.delete(idx)
    } else {
      newSet.add(idx)
    }
    collapsedSections.value = newSet
  }

  const applyAgentLogStatePatch = (patch) => applyReportStatePatch(patch, {
    reportOutline,
    currentSectionIndex,
    generatedSections,
    expandedContent,
    isComplete,
    startTime,
    emitUpdateStatus,
    stopPolling,
  })

  return {
    reportOutline,
    currentSectionIndex,
    generatedSections,
    expandedContent,
    collapsedSections,
    isComplete,
    startTime,
    applyReportRenderState,
    resetReportRenderState,
    toggleSectionContent,
    toggleSectionCollapse,
    applyAgentLogStatePatch,
  }
}
