import service, { requestWithRetry } from './index'

/**
 * Build the multipart payload used by /api/graph/ontology/generate.
 * Accepts the shared pending-upload payload shape from the Home page.
 */
export function buildOntologyFormData(payload = {}) {
  const formData = new FormData()

  for (const file of payload.files || []) {
    formData.append('files', file)
  }

  formData.append('simulation_requirement', payload.simulationRequirement || '')
  formData.append('project_type', payload.projectType || 'default')

  if (payload.projectName) {
    formData.append('project_name', payload.projectName)
  }

  if (payload.additionalContext) {
    formData.append('additional_context', payload.additionalContext)
  }

  if (payload.consumerBrief) {
    formData.append('consumer_brief', JSON.stringify(payload.consumerBrief))
  }

  return formData
}

/**
 * 生成本体（上传文档和模拟需求）
 * @param {FormData} formData
 * @returns {Promise}
 */
export function generateOntology(formData) {
  return requestWithRetry(() =>
    service({
      url: '/api/graph/ontology/generate',
      method: 'post',
      data: formData,
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
  )
}

/**
 * 构建图谱
 * @param {Object} data
 * @returns {Promise}
 */
export function buildGraph(data) {
  return requestWithRetry(() =>
    service({
      url: '/api/graph/build',
      method: 'post',
      data
    })
  )
}

/**
 * 查询任务状态
 * @param {String} taskId
 * @returns {Promise}
 */
export function getTaskStatus(taskId) {
  return service({
    url: `/api/graph/task/${taskId}`,
    method: 'get'
  })
}

/**
 * 获取图谱数据
 * @param {String} graphId
 * @returns {Promise}
 */
export function getGraphData(graphId) {
  return service({
    url: `/api/graph/data/${graphId}`,
    method: 'get'
  })
}

/**
 * 获取项目信息
 * @param {String} projectId
 * @returns {Promise}
 */
export function getProject(projectId) {
  return service({
    url: `/api/graph/project/${projectId}`,
    method: 'get'
  })
}
