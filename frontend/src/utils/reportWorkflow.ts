// @ts-nocheck
export function formatElapsedTime(startTime, agentLogs = []) {
  if (!startTime) return '0s'
  const lastLog = agentLogs[agentLogs.length - 1]
  const elapsed = lastLog?.elapsed_seconds || 0
  if (elapsed < 60) return `${Math.round(elapsed)}s`
  const mins = Math.floor(elapsed / 60)
  const secs = Math.round(elapsed % 60)
  return `${mins}m ${secs}s`
}

export function buildReportWorkflowSummary({
  isComplete = false,
  reportOutline = null,
  generatedSections = {},
  currentSectionIndex = null,
  agentLogs = [],
} = {}) {
  const statusClass = isComplete ? 'completed' : (agentLogs.length > 0 ? 'processing' : 'pending')
  const statusText = isComplete ? 'Completed' : (agentLogs.length > 0 ? 'Generating...' : 'Waiting')
  const totalSections = reportOutline?.sections?.length || 0
  const completedSections = Object.keys(generatedSections || {}).length
  const progressPercent = totalSections === 0 ? 0 : Math.round((completedSections / totalSections) * 100)
  const totalToolCalls = agentLogs.filter(l => l.action === 'tool_call').length
  const activeSectionIndex = isComplete
    ? null
    : (currentSectionIndex || (totalSections > 0 && completedSections < totalSections ? completedSections + 1 : null))
  const isPlanningDone = !!reportOutline?.sections?.length || agentLogs.some(l => l.action === 'planning_complete')
  const isPlanningStarted = agentLogs.some(l => l.action === 'planning_start' || l.action === 'report_start')
  const isFinalizing = !isComplete && isPlanningDone && totalSections > 0 && completedSections >= totalSections
  const workflowSteps = buildWorkflowSteps({
    isComplete,
    reportOutline,
    generatedSections,
    activeSectionIndex,
    isPlanningDone,
    isPlanningStarted,
    isFinalizing,
  })
  const activeStep = pickActiveStep(workflowSteps)

  return {
    statusClass,
    statusText,
    totalSections,
    completedSections,
    progressPercent,
    totalToolCalls,
    activeSectionIndex,
    isPlanningDone,
    isPlanningStarted,
    isFinalizing,
    workflowSteps,
    activeStep,
  }
}

export function applyAgentLogToReportState(log = {}) {
  if (log.action === 'planning_complete' && log.details?.outline) {
    return { reportOutline: log.details.outline }
  }

  if (log.action === 'section_start') {
    return { currentSectionIndex: log.section_index }
  }

  if (log.action === 'section_complete' && log.details?.content) {
    return {
      generatedSection: {
        index: log.section_index,
        content: log.details.content,
      },
      expandedContentIndex: log.section_index - 1,
      currentSectionIndex: null,
    }
  }

  if (log.action === 'report_complete') {
    return {
      isComplete: true,
      currentSectionIndex: null,
      statusUpdate: 'completed',
      shouldStopPolling: true,
    }
  }

  if (log.action === 'report_start') {
    return { startTime: new Date(log.timestamp) }
  }

  return {}
}

export function applyReportStatePatch(patch = {}, state = {}) {
  if (patch.reportOutline) {
    state.reportOutline.value = patch.reportOutline
  }
  if (patch.currentSectionIndex !== undefined) {
    state.currentSectionIndex.value = patch.currentSectionIndex
  }
  if (patch.generatedSection) {
    state.generatedSections.value[patch.generatedSection.index] = patch.generatedSection.content
  }
  if (patch.expandedContentIndex !== undefined) {
    state.expandedContent.value.add(patch.expandedContentIndex)
  }
  if (patch.isComplete !== undefined) {
    state.isComplete.value = patch.isComplete
  }
  if (patch.startTime) {
    state.startTime.value = patch.startTime
  }
  if (patch.statusUpdate) {
    state.emitUpdateStatus?.(patch.statusUpdate)
  }
  if (patch.shouldStopPolling) {
    state.stopPolling?.()
  }
}

function buildWorkflowSteps({
  isComplete,
  reportOutline,
  generatedSections,
  activeSectionIndex,
  isPlanningDone,
  isPlanningStarted,
  isFinalizing,
}) {
  const steps = []
  const planningStatus = isPlanningDone ? 'done' : (isPlanningStarted ? 'active' : 'todo')

  steps.push({
    key: 'planning',
    noLabel: 'PL',
    title: 'Planning / Outline',
    status: planningStatus,
    meta: planningStatus === 'active' ? 'IN PROGRESS' : '',
  })

  const sections = reportOutline?.sections || []
  sections.forEach((section, i) => {
    const idx = i + 1
    const status = (isComplete || !!generatedSections?.[idx])
      ? 'done'
      : (activeSectionIndex === idx ? 'active' : 'todo')

    steps.push({
      key: `section-${idx}`,
      noLabel: String(idx).padStart(2, '0'),
      title: section.title,
      status,
      meta: status === 'active' ? 'IN PROGRESS' : '',
    })
  })

  const completeStatus = isComplete ? 'done' : (isFinalizing ? 'active' : 'todo')
  steps.push({
    key: 'complete',
    noLabel: 'OK',
    title: 'Complete',
    status: completeStatus,
    meta: completeStatus === 'active' ? 'FINALIZING' : '',
  })

  return steps
}

function pickActiveStep(workflowSteps) {
  const active = workflowSteps.find(s => s.status === 'active')
  if (active) return active

  const doneSteps = workflowSteps.filter(s => s.status === 'done')
  if (doneSteps.length > 0) return doneSteps[doneSteps.length - 1]

  return workflowSteps[0] || { noLabel: '--', title: '等待开始', status: 'todo', meta: '' }
}

export function formatTime(timestamp) {
  if (!timestamp) return ''
  try {
    const formatted = new Date(timestamp).toLocaleTimeString('en-US', {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    })
    return formatted === 'Invalid Date' ? '' : formatted
  } catch {
    return ''
  }
}

export function formatParams(params) {
  if (!params) return ''
  try {
    return JSON.stringify(params, null, 2)
  } catch {
    return String(params)
  }
}

export function formatResultSize(length) {
  if (!length) return ''
  if (length < 1000) return `${length} chars`
  return `${(length / 1000).toFixed(1)}k chars`
}

export function truncateText(text, maxLen) {
  if (!text) return ''
  if (text.length <= maxLen) return text
  return text.substring(0, maxLen) + '...'
}

export function getTimelineItemClass(log, idx, total, isComplete = false) {
  const isLatest = idx === total - 1 && !isComplete
  const isMilestone = log.action === 'section_complete' || log.action === 'report_complete'
  return {
    'node--active': isLatest,
    'node--done': !isLatest && isMilestone,
    'node--muted': !isLatest && !isMilestone,
    'node--tool': log.action === 'tool_call' || log.action === 'tool_result',
  }
}

export function getConnectorClass(log, idx, total, isComplete = false) {
  const isLatest = idx === total - 1 && !isComplete
  if (isLatest) return 'dot-active'
  if (log.action === 'section_complete' || log.action === 'report_complete') return 'dot-done'
  return 'dot-muted'
}

export function getActionLabel(action) {
  const labels = {
    report_start: 'Report Started',
    planning_start: 'Planning',
    planning_complete: 'Plan Complete',
    section_start: 'Section Start',
    section_content: 'Content Ready',
    section_complete: 'Section Done',
    tool_call: 'Tool Call',
    tool_result: 'Tool Result',
    llm_response: 'LLM Response',
    report_complete: 'Complete',
  }
  return labels[action] || action
}

export function getLogLevelClass(log) {
  if (log.includes('ERROR') || log.includes('错误')) return 'error'
  if (log.includes('WARNING') || log.includes('警告')) return 'warning'
  return ''
}
