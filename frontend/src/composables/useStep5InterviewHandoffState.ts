// @ts-nocheck
import { ref } from 'vue'
import {
  loadConsumerInterviewHandoff,
  clearConsumerInterviewHandoff,
} from '../utils/consumerResearchActions'

export function useStep5InterviewHandoffState() {
  const interviewHandoffContext = ref(null)

  const loadInterviewHandoff = (simulationId) => {
    if (!simulationId) {
      interviewHandoffContext.value = null
      return
    }
    interviewHandoffContext.value = loadConsumerInterviewHandoff(simulationId)
  }

  const clearInterviewHandoff = (simulationId) => {
    if (!simulationId) return
    clearConsumerInterviewHandoff(simulationId)
    interviewHandoffContext.value = null
  }

  return {
    interviewHandoffContext,
    loadInterviewHandoff,
    clearInterviewHandoff,
  }
}
