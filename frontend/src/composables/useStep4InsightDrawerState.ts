// @ts-nocheck
import { ref } from 'vue'
import {
  normalizeConsumerResearchActionResponse,
  saveConsumerInterviewHandoff,
} from '../utils/consumerResearchActions'

let defaultRunActionPromise = null

async function loadDefaultRunAction() {
  if (!defaultRunActionPromise) {
    defaultRunActionPromise = import('../api/consumer')
      .then(api => api.runConsumerResearchAction)
  }
  return defaultRunActionPromise
}

export function useStep4InsightDrawerState({
  simulationId,
  goToInteraction = () => {},
  runConsumerResearchAction = null,
} = {}) {
  const showInsightDrawer = ref(false)
  const drawerResult = ref(null)
  const drawerLoading = ref(false)
  const drawerError = ref('')

  const closeInsightDrawer = () => {
    showInsightDrawer.value = false
    drawerResult.value = null
    drawerError.value = ''
  }

  const handleRunAction = async (payload) => {
    if (!simulationId.value) return
    drawerLoading.value = true
    drawerError.value = ''
    drawerResult.value = null
    showInsightDrawer.value = true

    try {
      const runAction = runConsumerResearchAction || await loadDefaultRunAction()
      const response = await runAction(simulationId.value, payload)
      drawerResult.value = normalizeConsumerResearchActionResponse(response)
    } catch (err) {
      drawerError.value = err?.message || 'Request failed'
    } finally {
      drawerLoading.value = false
    }
  }

  const handleOpenHandoff = (targetContext) => {
    saveConsumerInterviewHandoff(simulationId.value, targetContext)
    goToInteraction()
  }

  return {
    showInsightDrawer,
    drawerResult,
    drawerLoading,
    drawerError,
    closeInsightDrawer,
    handleRunAction,
    handleOpenHandoff,
  }
}
