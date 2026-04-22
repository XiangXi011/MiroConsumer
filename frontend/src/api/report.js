import service, { requestWithRetry } from './index'

/**
 * 开始报告生成
 * @param {Object} data - { simulation_id, force_regenerate? }
 */
export const generateReport = (data) => {
  return requestWithRetry(() => service.post('/api/report/generate', data), 3, 1000)
}

/**
 * 获取报告生成状态
 * @param {string} reportId
 */
export const getReportStatus = (reportId) => {
  return service.get(`/api/report/generate/status`, { params: { report_id: reportId } })
}

/**
 * 获取 Agent 日志（增量）
 * @param {string} reportId
 * @param {number} fromLine - 从第几行开始获取
 */
export const getAgentLog = (reportId, fromLine = 0) => {
  return service.get(`/api/report/${reportId}/agent-log`, { params: { from_line: fromLine } })
}

/**
 * 获取控制台日志（增量）
 * @param {string} reportId
 * @param {number} fromLine - 从第几行开始获取
 */
export const getConsoleLog = (reportId, fromLine = 0) => {
  return service.get(`/api/report/${reportId}/console-log`, { params: { from_line: fromLine } })
}

/**
 * 获取报告详情
 * @param {string} reportId
 */
export const getReport = (reportId) => {
  return service.get(`/api/report/${reportId}`)
}

/**
 * 与 Report Agent 对话
 * @param {Object} data - { simulation_id, message, chat_history? }
 */
export const chatWithReport = (data) => {
  return requestWithRetry(() => service.post('/api/report/chat', data), 3, 1000)
}

// ============== Research Assets API ==============

/**
 * Export a research asset pack
 * @param {Object} data - { project_id, simulation_id?, branch_id?, name? }
 */
export const exportResearchAsset = (data) => {
  return service.post('/api/report/research-assets/export', data)
}

/**
 * List research assets for a project
 * @param {string} projectId
 */
export const listResearchAssets = (projectId) => {
  return service.get('/api/report/research-assets', { params: { project_id: projectId } })
}

/**
 * Get a single research asset
 * @param {string} assetId
 */
export const getResearchAsset = (assetId) => {
  return service.get(`/api/report/research-assets/${assetId}`)
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
  return service.post('/api/report/compare', data)
}

/**
 * List comparisons for a project
 * @param {string} projectId
 */
export const listComparisons = (projectId) => {
  return service.get('/api/report/comparisons', { params: { project_id: projectId } })
}

/**
 * Get a single comparison
 * @param {string} comparisonId
 */
export const getComparison = (comparisonId) => {
  return service.get(`/api/report/comparisons/${comparisonId}`)
}
