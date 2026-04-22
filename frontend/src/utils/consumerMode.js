function formatPercent(value) {
  const numeric = Number(value)
  if (!Number.isFinite(numeric) || numeric <= 0) {
    return '0%'
  }
  return `${Math.round(numeric * 100)}%`
}

export function translate(t, key, fallback, params = {}) {
  if (typeof t !== 'function') {
    return fallback
  }
  return t(key, params)
}

const EVENT_LABEL_FALLBACKS = {
  positive_relay: 'Positive Relay',
  skeptical_challenge: 'Skeptical Challenge',
  misread_amplification: 'Misread Amplification',
  risk_discovery: 'Risk Discovery',
  clarification_recovery: 'Clarification Recovery',
}

export function getConsumerEventLabel(eventType, t = null) {
  const key = `consumer.eventTypes.${eventType}`
  const fallback = EVENT_LABEL_FALLBACKS[eventType] || eventType
  if (typeof t === 'function') {
    return t(key, fallback)
  }
  return fallback
}

export function isConsumerProject(projectLike) {
  if (!projectLike || typeof projectLike !== 'object') {
    return false
  }
  return projectLike.project_type === 'consumer_test' || projectLike.projectType === 'consumer_test'
}

export function buildConsumerMetricCards(reportContext = {}, t = null) {
  const summary = reportContext.summary || {}

  return [
    {
      key: 'initial',
      label: translate(t, 'consumer.metrics.initialAcceptance', 'Initial Acceptance'),
      value: formatPercent(summary.initial_acceptance?.positive),
    },
    {
      key: 'post',
      label: translate(t, 'consumer.metrics.postPropagationAcceptance', 'Post-Propagation Acceptance'),
      value: formatPercent(summary.post_propagation_acceptance?.positive),
    },
    {
      key: 'shift',
      label: translate(t, 'consumer.metrics.attitudeShift', 'Attitude Shift'),
      value: formatPercent(summary.attitude_shift_rate),
    },
    {
      key: 'events',
      label: translate(t, 'consumer.metrics.capturedEvents', 'Captured Events'),
      value: String(reportContext.events_count || 0),
    },
  ]
}

export function pickTopVocQuotes(reportContext = {}, t = null) {
  const groups = reportContext.representative_voc_quotes || {}
  const orderedBuckets = [
    ['resonance', translate(t, 'consumer.vocBuckets.resonance', 'Resonance')],
    ['risk', translate(t, 'consumer.vocBuckets.risk', 'Risk')],
    ['misread', translate(t, 'consumer.vocBuckets.misread', 'Misread')],
  ]

  return orderedBuckets
    .map(([bucket, label]) => {
      const item = groups[bucket]?.[0]
      if (!item?.quote) {
        return null
      }
      return {
        bucket,
        label,
        quote: item.quote,
        engagement: item.engagement || 0,
        agentId: item.agent_id || '',
      }
    })
    .filter(Boolean)
}

export function buildSourceAwarePrompts(reportContext = {}, t = null) {
  const prompts = []
  const enrichedFindings = reportContext.enriched_findings || []
  const sourceCatalog = reportContext.source_catalog || []

  const riskFindingsWithSource = enrichedFindings.filter(
    f => f.finding_type === 'risk_signal' && f.source_title,
  )
  if (riskFindingsWithSource.length > 0) {
    const first = riskFindingsWithSource[0]
    prompts.push(translate(
      t,
      'consumer.quickPrompts.sourceRisk',
      `Which source triggered the risk signal about "${first.summary}"?`,
      { summary: first.summary, source: first.source_title },
    ))
  }

  if (sourceCatalog.length > 0 && (reportContext.causal_chains || []).length > 0) {
    prompts.push(translate(
      t,
      'consumer.quickPrompts.sourceInfluence',
      'Which sources influenced the spread of these signals?',
    ))
  }

  const findingWithEvidence = enrichedFindings.find(
    f => f.evidence_preview && f.source_title,
  )
  if (findingWithEvidence) {
    prompts.push(translate(
      t,
      'consumer.quickPrompts.sourceEvidence',
      `What evidence from "${findingWithEvidence.source_title}" supports "${findingWithEvidence.summary}"?`,
      { summary: findingWithEvidence.summary, source: findingWithEvidence.source_title },
    ))
  }

  return prompts
}

// ============== Cascade / social-sandbox helpers ==============

export function formatCascadeMetrics(cascadeMetrics = {}, t = null) {
  if (!cascadeMetrics || typeof cascadeMetrics !== 'object') return []
  const items = []
  const push = (key, labelKey, fallback, formatter) => {
    const raw = cascadeMetrics[key]
    if (raw === undefined || raw === null || raw === '') return
    const value = formatter ? formatter(raw) : String(raw)
    items.push({
      key,
      label: translate(t, labelKey, fallback),
      value,
    })
  }
  push('community_coverage', 'consumer.cascade.communityCoverage', 'Community Coverage', v => formatPercent(v))
  push('cross_community_event_count', 'consumer.cascade.crossCommunityEvents', 'Cross-Community Events', v => String(v))
  push('bridge_event_count', 'consumer.cascade.bridgeEvents', 'Bridge Events', v => String(v))
  push('reversal_event_count', 'consumer.cascade.reversalEvents', 'Reversal Events', v => String(v))
  push('narrative_takeover_score', 'consumer.cascade.narrativeTakeover', 'Narrative Takeover', v => formatPercent(v))
  push('blocked_event_count', 'consumer.cascade.blockedEvents', 'Blocked Events', v => String(v))
  push('amplifier_event_count', 'consumer.cascade.amplifierEvents', 'Amplifier Events', v => String(v))
  return items
}

export function buildCascadeAwarePrompts(reportContext = {}, t = null) {
  const prompts = []
  const cascade = reportContext.cascade_metrics || {}

  if (cascade.cross_community_event_count > 0) {
    prompts.push(translate(
      t,
      'consumer.quickPrompts.crossCommunitySpread',
      `Why did the signal spread across ${cascade.cross_community_event_count} cross-community events?`,
      { count: cascade.cross_community_event_count },
    ))
  }
  if (cascade.blocked_event_count > 0) {
    prompts.push(translate(
      t,
      'consumer.quickPrompts.blockageReason',
      `What caused ${cascade.blocked_event_count} blockage events during propagation?`,
      { count: cascade.blocked_event_count },
    ))
  }
  if (cascade.reversal_event_count > 0) {
    prompts.push(translate(
      t,
      'consumer.quickPrompts.reversalPattern',
      `What patterns explain the ${cascade.reversal_event_count} reversal events?`,
      { count: cascade.reversal_event_count },
    ))
  }
  if (cascade.bridge_event_count > 0) {
    prompts.push(translate(
      t,
      'consumer.quickPrompts.bridgeActivity',
      `How did bridge personas influence spread in ${cascade.bridge_event_count} events?`,
      { count: cascade.bridge_event_count },
    ))
  }
  if (cascade.amplifier_event_count > 0) {
    prompts.push(translate(
      t,
      'consumer.quickPrompts.amplifierActivity',
      `Which messages were amplified most by high-reach personas?`,
    ))
  }
  if (cascade.narrative_takeover_score > 0) {
    prompts.push(translate(
      t,
      'consumer.quickPrompts.narrativeTakeover',
      `How close did a single narrative come to dominating the conversation?`,
    ))
  }

  return prompts
}

// ============== Intervention payload helpers ==============

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

// ============== Branch persistence (simulation-scoped, lightweight) ==============

function _branchKey(simulationId) {
  return `mirofish:consumer:branch:${simulationId}`
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

export function buildConsumerQuickPrompts(reportContext = {}, t = null) {
  const prompts = []
  const resonance = reportContext.top_resonance_points?.[0]
  const risk = reportContext.top_risk_points?.[0]
  const misread = reportContext.top_misreads?.[0]

  if (resonance) {
    prompts.push(translate(
      t,
      'consumer.quickPrompts.resonance',
      `Why did "${resonance}" become a top resonance point?`,
      { point: resonance },
    ))
  }
  if (risk) {
    prompts.push(translate(
      t,
      'consumer.quickPrompts.risk',
      `Why did "${risk}" get amplified during propagation?`,
      { point: risk },
    ))
  }
  if (misread) {
    prompts.push(translate(
      t,
      'consumer.quickPrompts.misread',
      `How did "${misread}" turn into a misread?`,
      { point: misread },
    ))
  }

  const riskFindings = reportContext.top_risk_findings || []
  const causalChains = reportContext.causal_chains || []
  const clarifications = reportContext.top_clarification_opportunities || []
  const reversals = reportContext.event_led_reversals || []
  const personaSignals = reportContext.persona_group_signals || {}

  if (riskFindings.length > 0 || causalChains.length > 0) {
    prompts.push(translate(
      t,
      'consumer.step5.causalPromptTrigger',
      'Which finding triggered the negative turn?',
    ))
  }
  if (Object.keys(personaSignals).length > 0) {
    prompts.push(translate(
      t,
      'consumer.step5.causalPromptSpread',
      'Why did this signal spread among these personas?',
    ))
  }
  if (clarifications.length > 0 || reversals.length > 0) {
    prompts.push(translate(
      t,
      'consumer.step5.causalPromptRecovery',
      'What helped the clarification recover acceptance?',
    ))
  }

  const sourcePrompts = buildSourceAwarePrompts(reportContext, t)
  prompts.push(...sourcePrompts)

  const cascadePrompts = buildCascadeAwarePrompts(reportContext, t)
  prompts.push(...cascadePrompts)

  return prompts
}
