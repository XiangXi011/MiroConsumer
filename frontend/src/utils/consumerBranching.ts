// @ts-nocheck
import { translate } from './consumerFormatting'

export function buildInterventionPayload(interventionType, value) {
  const v = String(value || '').trim()
  if (interventionType === 'clarification_injection') {
    return { message: v }
  }
  if (interventionType === 'revised_claim_injection') {
    return { claim: v }
  }
  if (interventionType === 'evidence_reveal') {
    return { evidence: v }
  }
  return { text: v }
}

export function getInterventionDisplayText(interventionType, payload) {
  if (!payload || typeof payload !== 'object') return ''
  if (interventionType === 'clarification_injection') {
    return payload.message || ''
  }
  if (interventionType === 'revised_claim_injection') {
    return payload.claim || ''
  }
  if (interventionType === 'evidence_reveal') {
    return payload.evidence || ''
  }
  return payload.text || JSON.stringify(payload)
}

// ============== Comparison persistence (simulation-scoped, lightweight) ==============

function _comparisonKey(simulationId) {
  return `miroconsumer:consumer:comparison:${simulationId}`
}

export function loadSelectedComparison(simulationId) {
  if (!simulationId || typeof window === 'undefined') return null
  try {
    const raw = window.localStorage.getItem(_comparisonKey(simulationId))
    if (!raw) return null
    const parsed = JSON.parse(raw)
    return parsed && parsed.comparisonId ? parsed.comparisonId : null
  } catch {
    return null
  }
}

export function saveSelectedComparison(simulationId, comparisonId) {
  if (!simulationId || typeof window === 'undefined') return
  try {
    if (comparisonId) {
      window.localStorage.setItem(_comparisonKey(simulationId), JSON.stringify({ comparisonId, selectedAt: Date.now() }))
    } else {
      window.localStorage.removeItem(_comparisonKey(simulationId))
    }
  } catch {
    // ignore storage errors
  }
}

export function clearSelectedComparison(simulationId) {
  if (!simulationId || typeof window === 'undefined') return
  try {
    window.localStorage.removeItem(_comparisonKey(simulationId))
  } catch {
    // ignore
  }
}

// ============== Branch persistence (simulation-scoped, lightweight) ==============

export async function restorePersistedBranchSelectionAfterLoad(options) {
  const {
    branches,
    persistedBranchId,
    setSelectedBranchId,
    loadInterventions,
    fetchBranchStatus,
    startPolling,
    clearPersisted,
  } = options

  if (!persistedBranchId) return

  const exists = branches.some(b => b.branch_id === persistedBranchId)
  if (exists) {
    setSelectedBranchId(persistedBranchId)
    await loadInterventions()
    const status = await fetchBranchStatus()
    if (status && status.status === 'running') {
      startPolling()
    }
  } else {
    clearPersisted()
    setSelectedBranchId('')
  }
}

function _branchKey(simulationId) {
  return `miroconsumer:consumer:branch:${simulationId}`
}

export function loadSelectedBranch(simulationId) {
  if (!simulationId || typeof window === 'undefined') return null
  try {
    const raw = window.localStorage.getItem(_branchKey(simulationId))
    if (!raw) return null
    const parsed = JSON.parse(raw)
    return parsed && parsed.branchId ? parsed.branchId : null
  } catch {
    return null
  }
}

export function saveSelectedBranch(simulationId, branchId) {
  if (!simulationId || typeof window === 'undefined') return
  try {
    if (branchId) {
      window.localStorage.setItem(_branchKey(simulationId), JSON.stringify({ branchId, selectedAt: Date.now() }))
    } else {
      window.localStorage.removeItem(_branchKey(simulationId))
    }
  } catch {
    // ignore storage errors
  }
}

export function clearSelectedBranch(simulationId) {
  if (!simulationId || typeof window === 'undefined') return
  try {
    window.localStorage.removeItem(_branchKey(simulationId))
  } catch {
    // ignore
  }
}

// ============== Branch comparison formatting ==============

export function formatBranchComparison(context = {}, t = null) {
  const forkRound = context.fork_round ?? 0
  const branchName = context.branch_name || ''
  const interventions = context.interventions || []
  const base = context.base_summary || {}
  const branch = context.branch_summary || {}

  const baseAcceptance = base.post_propagation_acceptance?.positive ?? base.initial_acceptance?.positive ?? 0
  const branchAcceptance = branch.post_propagation_acceptance?.positive ?? branch.initial_acceptance?.positive ?? 0
  const baseEvents = base.events_count || 0
  const branchEvents = branch.events_count || 0

  const delta = branchAcceptance - baseAcceptance
  const deltaText = delta >= 0 ? `+${Math.round(delta * 100)}pp` : `${Math.round(delta * 100)}pp`

  return {
    branchId: context.branch_id || '',
    baseBranchId: context.base_branch_id || '',
    forkRound,
    branchName,
    interventionCount: interventions.length,
    baseAcceptancePct: `${Math.round(baseAcceptance * 100)}%`,
    branchAcceptancePct: `${Math.round(branchAcceptance * 100)}%`,
    deltaText,
    baseEvents,
    branchEvents,
    topResonanceDelta: _deltaQuotes(base.top_resonance_quotes, branch.top_resonance_quotes),
    topRiskDelta: _deltaQuotes(base.top_risk_quotes, branch.top_risk_quotes),
    hasData: base.has_data || branch.has_data,
  }
}

function _deltaQuotes(baseQuotes = [], branchQuotes = []) {
  const baseTexts = new Set((baseQuotes || []).map(q => q.quote || q.text || '').filter(Boolean))
  return (branchQuotes || [])
    .map(q => q.quote || q.text || '')
    .filter(Boolean)
    .filter(text => !baseTexts.has(text))
}

export function buildBranchAwarePrompts(comparison = {}, t = null) {
  const prompts = []
  const branchName = comparison.branch_name || ''
  const forkRound = comparison.fork_round ?? 0
  const interventions = comparison.interventions || []

  if (branchName && forkRound > 0) {
    prompts.push(translate(t, 'consumer.quickPrompts.branchFork', `How does the branch "${branchName}" (forked at round ${forkRound}) differ from the base run?`, { branchName, forkRound }))
  }

  if (interventions.length > 0) {
    const types = [...new Set(interventions.map(i => i.intervention_type))]
    prompts.push(translate(t, 'consumer.quickPrompts.branchIntervention', `What impact did the ${types.length} intervention type(s) have on acceptance?`, { count: types.length }))
  }

  const base = comparison.base_summary || {}
  const branch = comparison.branch_summary || {}
  const baseAcceptance = base.post_propagation_acceptance?.positive ?? 0
  const branchAcceptance = branch.post_propagation_acceptance?.positive ?? 0
  if (baseAcceptance > 0 && branchAcceptance > 0) {
    const delta = branchAcceptance - baseAcceptance
    const direction = delta >= 0 ? 'improved' : 'worsened'
    prompts.push(translate(t, 'consumer.quickPrompts.branchDelta', `Acceptance ${direction} by ${Math.round(Math.abs(delta) * 100)} percentage points. Why?`, { direction, delta: Math.round(Math.abs(delta) * 100) }))
  }

  return prompts
}

export function buildComparisonAwarePrompts(comparisonSnapshot = {}, t = null) {
  const prompts = []
  if (!comparisonSnapshot || typeof comparisonSnapshot !== 'object') return prompts

  const mode = comparisonSnapshot.mode || ''
  const left = comparisonSnapshot.left || {}
  const right = comparisonSnapshot.right || {}
  const acceptanceDelta = comparisonSnapshot.acceptance_delta_pp ?? 0

  if (mode === 'branch_vs_base' && left.label && right.label) {
    prompts.push(translate(
      t,
      'consumer.quickPrompts.comparisonBranchVsBase',
      `How does the branch "${right.label}" differ from the base run "${left.label}"?`,
      { left: left.label, right: right.label },
    ))
  }

  if (mode === 'run_vs_run' && left.label && right.label) {
    prompts.push(translate(
      t,
      'consumer.quickPrompts.comparisonRunVsRun',
      `What explains the difference between run "${left.label}" and run "${right.label}"?`,
      { left: left.label, right: right.label },
    ))
  }

  if (mode === 'project_vs_project' && left.label && right.label) {
    prompts.push(translate(
      t,
      'consumer.quickPrompts.comparisonProjectVsProject',
      `How do the research findings differ between project "${left.label}" and project "${right.label}"?`,
      { left: left.label, right: right.label },
    ))
  }

  if ((comparisonSnapshot.resonance_overlap || []).length > 0) {
    prompts.push(translate(
      t,
      'consumer.quickPrompts.comparisonResonanceOverlap',
      'What do the overlapping resonance signals tell us about the core message?',
    ))
  }

  if ((comparisonSnapshot.recurring_risk_signals || []).length > 0) {
    prompts.push(translate(
      t,
      'consumer.quickPrompts.comparisonRecurringRisks',
      'Why do these risk signals keep appearing across both runs?',
    ))
  }

  if ((comparisonSnapshot.evidence_backed_divergences || []).length > 0) {
    const firstDiv = comparisonSnapshot.evidence_backed_divergences[0]
    prompts.push(translate(
      t,
      'consumer.quickPrompts.comparisonDivergence',
      `The signal "${firstDiv?.signal || ''}" diverges between runs. What explains this?`,
      { signal: firstDiv?.signal || '' },
    ))
  }

  if (acceptanceDelta !== 0) {
    const direction = acceptanceDelta > 0 ? 'increased' : 'decreased'
    prompts.push(translate(
      t,
      'consumer.quickPrompts.comparisonAcceptanceDelta',
      `Acceptance ${direction} by ${Math.abs(Math.round(acceptanceDelta))} percentage points. What drove this?`,
      { direction, delta: Math.abs(Math.round(acceptanceDelta)) },
    ))
  }

  return prompts
}
