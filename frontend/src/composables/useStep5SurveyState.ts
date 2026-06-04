// @ts-nocheck
import { ref } from 'vue'

export function useStep5SurveyState({ profiles = ref([]) } = {}) {
  const selectedAgents = ref(new Set())
  const surveyQuestion = ref('')
  const surveyResults = ref([])
  const isSurveying = ref(false)

  const toggleAgentSelection = (idx) => {
    const newSet = new Set(selectedAgents.value)
    if (newSet.has(idx)) {
      newSet.delete(idx)
    } else {
      newSet.add(idx)
    }
    selectedAgents.value = newSet
  }

  const selectAllAgents = () => {
    const newSet = new Set()
    profiles.value.forEach((_, idx) => newSet.add(idx))
    selectedAgents.value = newSet
  }

  const clearAgentSelection = () => {
    selectedAgents.value = new Set()
  }

  return {
    selectedAgents,
    surveyQuestion,
    surveyResults,
    isSurveying,
    toggleAgentSelection,
    selectAllAgents,
    clearAgentSelection,
  }
}
