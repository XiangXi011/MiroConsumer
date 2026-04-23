import service, { requestWithRetry } from './index'

// ============== Consumer Summary ==============

/**
 * 获取消费者传播摘要
 * @param {string} simulationId
 */
export const getConsumerSummary = (simulationId) => {
  return service.get(`/api/consumer/simulation/${simulationId}/consumer-summary`)
}

// ============== Branch APIs ==============

/**
 * 列出某模拟的所有分支
 * @param {string} simulationId
 */
export const listBranches = (simulationId) => {
  return service.get(`/api/consumer/simulations/${simulationId}/branches`)
}

/**
 * 创建分支
 * @param {string} simulationId
 * @param {Object} data - { name, fork_round, description?, parent_branch_id? }
 */
export const createBranch = (simulationId, data) => {
  return service.post(`/api/consumer/simulations/${simulationId}/branches`, data)
}

/**
 * 获取分支对比上下文
 * @param {string} simulationId
 * @param {string} branchId
 */
export const getBranchComparison = (simulationId, branchId) => {
  return service.get(`/api/consumer/simulations/${simulationId}/branches/${branchId}/comparison`)
}

/**
 * 运行分支模拟
 * @param {string} simulationId
 * @param {string} branchId
 * @param {Object} data - { max_rounds? }
 */
export const runBranch = (simulationId, branchId, data = {}) => {
  return service.post(`/api/consumer/simulations/${simulationId}/branches/${branchId}/resume`, data)
}

/**
 * 获取分支运行状态
 * @param {string} simulationId
 * @param {string} branchId
 */
export const getBranchStatus = (simulationId, branchId) => {
  return service.get(`/api/consumer/simulations/${simulationId}/branches/${branchId}/status`)
}

// ============== Intervention APIs ==============

/**
 * 列出某模拟或某分支的干预
 * @param {string} simulationId
 * @param {string} branchId - 可选
 */
export const listInterventions = (simulationId, branchId = null) => {
  const params = branchId ? { branch_id: branchId } : {}
  return service.get(`/api/consumer/simulations/${simulationId}/interventions`, { params })
}

/**
 * 为某分支添加干预
 * @param {string} simulationId
 * @param {string} branchId
 * @param {Object} data - { intervention_type, payload, target_round? }
 */
export const addIntervention = (simulationId, branchId, data) => {
  return service.post(`/api/consumer/simulations/${simulationId}/branches/${branchId}/interventions`, data)
}

// ============== Research Assets API ==============

/**
 * Export a research asset pack
 * @param {Object} data - { project_id, simulation_id?, branch_id?, name? }
 */
export const exportResearchAsset = (data) => {
  return service.post('/api/consumer/research-assets/export', data)
}

/**
 * List research assets for a project
 * @param {string} projectId
 */
export const listResearchAssets = (projectId) => {
  return service.get('/api/consumer/research-assets', { params: { project_id: projectId } })
}

/**
 * Get a single research asset
 * @param {string} assetId
 */
export const getResearchAsset = (assetId) => {
  return service.get(`/api/consumer/research-assets/${assetId}`)
}

// ============== Comparison API ==============

/**
 * Compare research snapshots
 * Supports:
 *   a) { mode: "run_vs_run", left_simulation_id, right_simulation_id }
 *   b) { mode: "branch_vs_base", simulation_id, branch_id }
 *   c) { mode: "project_vs_project", left_project_id, right_project_id }
 * @param {Object} data
 */
export const compareResearchSnapshots = (data) => {
  return service.post('/api/consumer/comparisons', data)
}

/**
 * List comparisons for a project
 * @param {string} projectId
 */
export const listComparisons = (projectId) => {
  return service.get('/api/consumer/comparisons', { params: { project_id: projectId } })
}

/**
 * Get a single comparison
 * @param {string} comparisonId
 */
export const getComparison = (comparisonId) => {
  return service.get(`/api/consumer/comparisons/${comparisonId}`)
}
