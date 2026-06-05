// @ts-nocheck
import { ref, nextTick as vueNextTick } from 'vue'
import { applyAgentLogToReportState } from '../utils/reportWorkflow'

let defaultReportApiPromise = null

async function loadDefaultReportApi() {
  if (!defaultReportApiPromise) {
    defaultReportApiPromise = import('../api/report')
      .then(api => ({
        getAgentLog: api.getAgentLog,
        getConsoleLog: api.getConsoleLog,
      }))
  }
  return defaultReportApiPromise
}

export function useStep4ReportPollingState({
  reportId,
  isComplete,
  rightPanel,
  logContent,
  applyAgentLogStatePatch,
  api = null,
  nextTick = vueNextTick,
  setIntervalFn = setInterval,
  clearIntervalFn = clearInterval,
  warn = console.warn,
} = {}) {
  const agentLogs = ref([])
  const consoleLogs = ref([])
  const agentLogLine = ref(0)
  const consoleLogLine = ref(0)

  let agentLogTimer = null
  let consoleLogTimer = null

  const resolveApi = async () => api || loadDefaultReportApi()

  const resetPollingState = () => {
    agentLogs.value = []
    consoleLogs.value = []
    agentLogLine.value = 0
    consoleLogLine.value = 0
  }

  const fetchAgentLog = async () => {
    if (!reportId.value) return

    try {
      const resolvedApi = await resolveApi()
      const res = await resolvedApi.getAgentLog(reportId.value, agentLogLine.value)

      if (res.success && res.data) {
        const newLogs = res.data.logs || []

        if (newLogs.length > 0) {
          newLogs.forEach(log => {
            agentLogs.value.push(log)
            applyAgentLogStatePatch(applyAgentLogToReportState(log))
          })

          agentLogLine.value = res.data.from_line + newLogs.length

          nextTick(() => {
            if (rightPanel.value) {
              if (isComplete.value) {
                rightPanel.value.scrollTop = 0
              } else {
                rightPanel.value.scrollTop = rightPanel.value.scrollHeight
              }
            }
          })
        }
      }
    } catch (err) {
      warn('Failed to fetch agent log:', err)
    }
  }

  const fetchConsoleLog = async () => {
    if (!reportId.value) return

    try {
      const resolvedApi = await resolveApi()
      const res = await resolvedApi.getConsoleLog(reportId.value, consoleLogLine.value)

      if (res.success && res.data) {
        const newLogs = res.data.logs || []

        if (newLogs.length > 0) {
          consoleLogs.value.push(...newLogs)
          consoleLogLine.value = res.data.from_line + newLogs.length

          nextTick(() => {
            if (logContent.value) {
              logContent.value.scrollTop = logContent.value.scrollHeight
            }
          })
        }
      }
    } catch (err) {
      warn('Failed to fetch console log:', err)
    }
  }

  const startPolling = async () => {
    if (agentLogTimer || consoleLogTimer) return

    await fetchAgentLog()
    await fetchConsoleLog()

    agentLogTimer = setIntervalFn(fetchAgentLog, 2000)
    consoleLogTimer = setIntervalFn(fetchConsoleLog, 1500)
  }

  const stopPolling = () => {
    if (agentLogTimer) {
      clearIntervalFn(agentLogTimer)
      agentLogTimer = null
    }
    if (consoleLogTimer) {
      clearIntervalFn(consoleLogTimer)
      consoleLogTimer = null
    }
  }

  return {
    agentLogs,
    consoleLogs,
    agentLogLine,
    consoleLogLine,
    resetPollingState,
    fetchAgentLog,
    fetchConsoleLog,
    startPolling,
    stopPolling,
  }
}
