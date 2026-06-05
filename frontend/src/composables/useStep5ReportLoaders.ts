// @ts-nocheck
let defaultApiPromise = null

async function loadDefaultApi() {
  if (!defaultApiPromise) {
    defaultApiPromise = Promise.all([
      import('../api/report'),
      import('../api/simulation'),
    ]).then(([reportApi, simulationApi]) => ({
      getReport: reportApi.getReport,
      getAgentLog: reportApi.getAgentLog,
      getSimulationProfilesRealtime: simulationApi.getSimulationProfilesRealtime,
    }))
  }
  return defaultApiPromise
}

export function useStep5ReportLoaders({
  reportId,
  simulationId,
  profiles,
  addLog,
  t,
  applyReportLogs,
  setProfiles,
  api = null,
}) {
  const resolveApi = async () => api || loadDefaultApi()

  const loadAgentLogs = async () => {
    if (!reportId.value) return

    try {
      const resolvedApi = await resolveApi()
      const res = await resolvedApi.getAgentLog(reportId.value, 0)
      if (res.success && res.data) {
        const logs = res.data.logs || []

        applyReportLogs(logs)

        addLog(t('log.reportDataLoaded'))
      }
    } catch (err) {
      addLog(t('log.loadReportLogFailed', { error: err.message }))
    }
  }

  const loadReportData = async () => {
    if (!reportId.value) return

    try {
      addLog(t('log.loadReportData', { id: reportId.value }))

      const resolvedApi = await resolveApi()
      const reportRes = await resolvedApi.getReport(reportId.value)
      if (reportRes.success && reportRes.data) {
        await loadAgentLogs()
      }
    } catch (err) {
      addLog(t('log.loadReportFailed', { error: err.message }))
    }
  }

  const loadProfiles = async () => {
    if (!simulationId.value) return

    try {
      const resolvedApi = await resolveApi()
      const res = await resolvedApi.getSimulationProfilesRealtime(simulationId.value, 'reddit')
      if (res.success && res.data) {
        setProfiles(res.data.profiles || [])
        addLog(t('log.loadedProfiles', { count: profiles.value.length }))
      }
    } catch (err) {
      addLog(t('log.loadProfilesFailed', { error: err.message }))
    }
  }

  return {
    loadReportData,
    loadAgentLogs,
    loadProfiles,
  }
}
