import service, { requestWithRetry } from './index'

// Re-export consumer-specific wrappers from canonical consumer module
export {
  exportResearchAsset,
  listResearchAssets,
  getResearchAsset,
  compareResearchSnapshots,
  listComparisons,
  getComparison,
} from './consumer'

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

// Research assets & comparisons live in consumer.js and are re-exported above.

// ============== Benchmark API ==============

/**
 * Register a benchmark case
 * @param {Object} data - { name, source_pack_lineage, expected_signals, simulation_context? }
 */
export const registerBenchmark = (data) => {
  return service.post('/api/report/benchmarks/register', data)
}

/**
 * List all registered benchmarks
 */
export const listBenchmarks = () => {
  return service.get('/api/report/benchmarks')
}

/**
 * Get a single benchmark
 * @param {string} benchmarkId
 */
export const getBenchmark = (benchmarkId) => {
  return service.get(`/api/report/benchmarks/${benchmarkId}`)
}

/**
 * Replay a benchmark against current report context
 * @param {string} benchmarkId
 * @param {Object} data - { report_context, project_id?, simulation_id? }
 */
export const replayBenchmark = (benchmarkId, data) => {
  return service.post(`/api/report/benchmarks/${benchmarkId}/replay`, data)
}

/**
 * Get a single replay result
 * @param {string} replayId
 */
export const getReplayResult = (replayId) => {
  return service.get(`/api/report/benchmark-replays/${replayId}`)
}
