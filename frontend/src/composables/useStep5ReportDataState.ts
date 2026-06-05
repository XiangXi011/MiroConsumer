// @ts-nocheck
import { ref } from 'vue'

export function useStep5ReportDataState() {
  const reportOutline = ref(null)
  const generatedSections = ref({})
  const collapsedSections = ref(new Set())
  const currentSectionIndex = ref(null)
  const profiles = ref([])

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

  const applyReportLogs = (logs = []) => {
    logs.forEach(log => {
      if (log.action === 'planning_complete' && log.details?.outline) {
        reportOutline.value = log.details.outline
      }

      if (log.action === 'section_complete' && log.section_index < 100 && log.details?.content) {
        generatedSections.value[log.section_index] = log.details.content
      }
    })
  }

  const setProfiles = (nextProfiles) => {
    profiles.value = Array.isArray(nextProfiles) ? nextProfiles : []
  }

  return {
    reportOutline,
    generatedSections,
    collapsedSections,
    currentSectionIndex,
    profiles,
    toggleSectionCollapse,
    applyReportLogs,
    setProfiles,
  }
}
