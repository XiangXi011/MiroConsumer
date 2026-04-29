// Pure API factory — no runtime dependencies on axios, Vue, i18n, or ./index.
// Inject any service object that provides get(url, config?) and post(url, data?).

export function createConsumerApi(service) {
  return {
    getConsumerSummary(simulationId) {
      return service.get(`/api/consumer/simulation/${simulationId}/consumer-summary`)
    },

    getChannelSummary(simulationId) {
      return service.get(`/api/consumer/simulations/${simulationId}/channel-summary`)
    },

    getChannelEvents(simulationId) {
      return service.get(`/api/consumer/simulations/${simulationId}/channel-events`)
    },

    getPropagationPaths(simulationId) {
      return service.get(`/api/consumer/simulations/${simulationId}/propagation-paths`)
    },

    listBranches(simulationId) {
      return service.get(`/api/consumer/simulations/${simulationId}/branches`)
    },

    createBranch(simulationId, data) {
      return service.post(`/api/consumer/simulations/${simulationId}/branches`, data)
    },

    getBranchComparison(simulationId, branchId) {
      return service.get(`/api/consumer/simulations/${simulationId}/branches/${branchId}/comparison`)
    },

    runBranch(simulationId, branchId, data = {}) {
      return service.post(`/api/consumer/simulations/${simulationId}/branches/${branchId}/resume`, data)
    },

    getBranchStatus(simulationId, branchId) {
      return service.get(`/api/consumer/simulations/${simulationId}/branches/${branchId}/status`)
    },

    listInterventions(simulationId, branchId = null) {
      const params = branchId ? { branch_id: branchId } : {}
      return service.get(`/api/consumer/simulations/${simulationId}/interventions`, { params })
    },

    addIntervention(simulationId, branchId, data) {
      return service.post(`/api/consumer/simulations/${simulationId}/branches/${branchId}/interventions`, data)
    },

    exportResearchAsset(data) {
      return service.post('/api/consumer/research-assets/export', data)
    },

    listResearchAssets(projectId) {
      return service.get('/api/consumer/research-assets', { params: { project_id: projectId } })
    },

    getResearchAsset(assetId) {
      return service.get(`/api/consumer/research-assets/${assetId}`)
    },

    compareResearchSnapshots(data) {
      return service.post('/api/consumer/comparisons', data)
    },

    listComparisons(projectId) {
      return service.get('/api/consumer/comparisons', { params: { project_id: projectId } })
    },

    getComparison(comparisonId) {
      return service.get(`/api/consumer/comparisons/${comparisonId}`)
    },

    runConsumerResearchAction(simulationId, data) {
      return service.post(`/api/consumer/simulations/${simulationId}/research-actions`, data)
    },
  }
}
