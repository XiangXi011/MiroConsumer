import service, { requestWithRetry } from './index'

/**
 * 创建模拟
 * @param {Object} data - { project_id, graph_id?, enable_twitter?, enable_reddit? }
 */
export const createSimulation = (data) => {
  return requestWithRetry(() => service.post('/api/simulation/create', data), 3, 1000)
}

/**
 * 准备模拟环境（异步任务）
 * @param {Object} data - { simulation_id, entity_types?, use_llm_for_profiles?, parallel_profile_count?, force_regenerate? }
 */
export const prepareSimulation = (data) => {
  return requestWithRetry(() => service.post('/api/simulation/prepare', data), 3, 1000)
}

/**
 * 查询准备任务进度
 * @param {Object} data - { task_id?, simulation_id? }
 */
export const getPrepareStatus = (data) => {
  return service.post('/api/simulation/prepare/status', data)
}

/**
 * 获取模拟状态
 * @param {string} simulationId
 */
export const getSimulation = (simulationId) => {
  return service.get(`/api/simulation/${simulationId}`)
}

/**
 * 获取模拟的 Agent Profiles
 * @param {string} simulationId
 * @param {string} platform - 'reddit' | 'twitter'
 */
export const getSimulationProfiles = (simulationId, platform = 'reddit') => {
  return service.get(`/api/simulation/${simulationId}/profiles`, { params: { platform } })
}

/**
 * 实时获取生成中的 Agent Profiles
 * @param {string} simulationId
 * @param {string} platform - 'reddit' | 'twitter'
 */
export const getSimulationProfilesRealtime = (simulationId, platform = 'reddit') => {
  return service.get(`/api/simulation/${simulationId}/profiles/realtime`, { params: { platform } })
}

/**
 * 获取模拟配置
 * @param {string} simulationId
 */
export const getSimulationConfig = (simulationId) => {
  return service.get(`/api/simulation/${simulationId}/config`)
}

/**
 * 实时获取生成中的模拟配置
 * @param {string} simulationId
 * @returns {Promise} 返回配置信息，包含元数据和配置内容
 */
export const getSimulationConfigRealtime = (simulationId) => {
  return service.get(`/api/simulation/${simulationId}/config/realtime`)
}

/**
 * 获取消费者传播摘要
 * @param {string} simulationId
 */
export const getConsumerSummary = (simulationId) => {
  return service.get(`/api/simulation/${simulationId}/consumer-summary`)
}

/**
 * 列出所有模拟
 * @param {string} projectId - 可选，按项目ID过滤
 */
export const listSimulations = (projectId) => {
  const params = projectId ? { project_id: projectId } : {}
  return service.get('/api/simulation/list', { params })
}

/**
 * 启动模拟
 * @param {Object} data - { simulation_id, platform?, max_rounds?, enable_graph_memory_update? }
 */
export const startSimulation = (data) => {
  return requestWithRetry(() => service.post('/api/simulation/start', data), 3, 1000)
}

/**
 * 停止模拟
 * @param {Object} data - { simulation_id }
 */
export const stopSimulation = (data) => {
  return service.post('/api/simulation/stop', data)
}

/**
 * 获取模拟运行实时状态
 * @param {string} simulationId
 */
export const getRunStatus = (simulationId) => {
  return service.get(`/api/simulation/${simulationId}/run-status`)
}

/**
 * 获取模拟运行详细状态（包含最近动作）
 * @param {string} simulationId
 */
export const getRunStatusDetail = (simulationId) => {
  return service.get(`/api/simulation/${simulationId}/run-status/detail`)
}

/**
 * 获取模拟中的帖子
 * @param {string} simulationId
 * @param {string} platform - 'reddit' | 'twitter'
 * @param {number} limit - 返回数量
 * @param {number} offset - 偏移量
 */
export const getSimulationPosts = (simulationId, platform = 'reddit', limit = 50, offset = 0) => {
  return service.get(`/api/simulation/${simulationId}/posts`, {
    params: { platform, limit, offset }
  })
}

/**
 * 获取模拟时间线（按轮次汇总）
 * @param {string} simulationId
 * @param {number} startRound - 起始轮次
 * @param {number} endRound - 结束轮次
 */
export const getSimulationTimeline = (simulationId, startRound = 0, endRound = null) => {
  const params = { start_round: startRound }
  if (endRound !== null) {
    params.end_round = endRound
  }
  return service.get(`/api/simulation/${simulationId}/timeline`, { params })
}

/**
 * 获取Agent统计信息
 * @param {string} simulationId
 */
export const getAgentStats = (simulationId) => {
  return service.get(`/api/simulation/${simulationId}/agent-stats`)
}

/**
 * 获取模拟动作历史
 * @param {string} simulationId
 * @param {Object} params - { limit, offset, platform, agent_id, round_num }
 */
export const getSimulationActions = (simulationId, params = {}) => {
  return service.get(`/api/simulation/${simulationId}/actions`, { params })
}

/**
 * 关闭模拟环境（优雅退出）
 * @param {Object} data - { simulation_id, timeout? }
 */
export const closeSimulationEnv = (data) => {
  return service.post('/api/simulation/close-env', data)
}

/**
 * 获取模拟环境状态
 * @param {Object} data - { simulation_id }
 */
export const getEnvStatus = (data) => {
  return service.post('/api/simulation/env-status', data)
}

/**
 * 批量采访 Agent
 * @param {Object} data - { simulation_id, interviews: [{ agent_id, prompt }] }
 */
export const interviewAgents = (data) => {
  return requestWithRetry(() => service.post('/api/simulation/interview/batch', data), 3, 1000)
}

/**
 * 获取历史模拟列表（带项目详情）
 * 用于首页历史项目展示
 * @param {number} limit - 返回数量限制
 */
export const getSimulationHistory = (limit = 20) => {
  return service.get('/api/simulation/history', { params: { limit } })
}

// ============== Branch / Intervention APIs (consumer_test only) ==============

/**
 * 列出某模拟的所有分支
 * @param {string} simulationId
 */
export const listBranches = (simulationId) => {
  return service.get(`/api/simulation/${simulationId}/branches`)
}

/**
 * 创建分支
 * @param {string} simulationId
 * @param {Object} data - { name, fork_round, description?, parent_branch_id? }
 */
export const createBranch = (simulationId, data) => {
  return service.post(`/api/simulation/${simulationId}/branches`, data)
}

/**
 * 列出某模拟或某分支的干预
 * @param {string} simulationId
 * @param {string} branchId - 可选
 */
export const listInterventions = (simulationId, branchId = null) => {
  const params = branchId ? { branch_id: branchId } : {}
  return service.get(`/api/simulation/${simulationId}/interventions`, { params })
}

/**
 * 为某分支添加干预
 * @param {string} simulationId
 * @param {string} branchId
 * @param {Object} data - { intervention_type, payload, target_round? }
 */
export const addIntervention = (simulationId, branchId, data) => {
  return service.post(`/api/simulation/${simulationId}/branches/${branchId}/interventions`, data)
}

/**
 * 获取分支对比上下文
 * @param {string} simulationId
 * @param {string} branchId
 */
export const getBranchComparison = (simulationId, branchId) => {
  return service.get(`/api/simulation/${simulationId}/branches/${branchId}/comparison`)
}

