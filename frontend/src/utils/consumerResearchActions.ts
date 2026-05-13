// @ts-nocheck
export const CONSUMER_RESEARCH_ACTIONS = {
  DEEP_DIVE_CONCLUSION: 'deep_dive_conclusion',
  EXPLAIN_PROPAGATION_PATH: 'explain_propagation_path',
  VERIFY_EVIDENCE: 'verify_evidence',
  INTERVIEW_CONSUMERS: 'interview_consumers',
  COMPARE_BRANCH_DELTA: 'compare_branch_delta',
}

export function buildConsumerResearchActionPayload(
  actionType,
  { reportId, sectionIndex, sectionTitle, sectionContent, branchId, claim, findingId }
) {
  const isInterview = actionType === CONSUMER_RESEARCH_ACTIONS.INTERVIEW_CONSUMERS
  const hasFindingId = isInterview && findingId
  const targetText = sectionTitle || claim || String(sectionContent || '').slice(0, 280)
  const contextClaim = claim || sectionTitle || ''

  const target = {
    kind: hasFindingId ? 'finding' : 'section',
    id: hasFindingId ? findingId : `section_${sectionIndex}`,
  }

  if (!hasFindingId) {
    target.text = targetText
  }

  return {
    action_type: actionType,
    target,
    context: {
      report_id: reportId || '',
      section_index: sectionIndex ?? null,
      branch_id: branchId || '',
      claim: contextClaim,
    },
  }
}

export function normalizeConsumerResearchActionResponse(apiResponse) {
  if (apiResponse && typeof apiResponse === 'object' && 'data' in apiResponse) {
    if ('success' in apiResponse) {
      return apiResponse.data
    }
  }
  return apiResponse
}

export function isPhase6IInterviewHandoff(result) {
  if (!result || typeof result !== 'object') return false
  if (!result.handoff || typeof result.handoff !== 'object') return false
  return result.handoff.handoff_type === 'phase6i_interview'
}

export function getConsumerInterviewHandoffStorageKey(simulationId) {
  return `miroconsumer:consumer:interview-handoff:${simulationId}`
}

export function saveConsumerInterviewHandoff(simulationId, targetContext) {
  if (typeof window === 'undefined') return
  try {
    window.localStorage.setItem(
      getConsumerInterviewHandoffStorageKey(simulationId),
      JSON.stringify({ targetContext, savedAt: Date.now() })
    )
  } catch {
    // ignore storage errors
  }
}

export function loadConsumerInterviewHandoff(simulationId) {
  if (typeof window === 'undefined') return null
  try {
    const raw = window.localStorage.getItem(getConsumerInterviewHandoffStorageKey(simulationId))
    if (!raw) return null
    const parsed = JSON.parse(raw)
    return parsed && parsed.targetContext ? parsed.targetContext : null
  } catch {
    return null
  }
}

export function clearConsumerInterviewHandoff(simulationId) {
  if (typeof window === 'undefined') return
  try {
    window.localStorage.removeItem(getConsumerInterviewHandoffStorageKey(simulationId))
  } catch {
    // ignore storage errors
  }
}
