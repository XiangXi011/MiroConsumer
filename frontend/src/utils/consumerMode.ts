// @ts-nocheck
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

const STEP3_TOOLTIP_ACTIONS = {
  twitter: ['POST', 'LIKE', 'REPOST', 'QUOTE', 'FOLLOW', 'IDLE'],
  reddit: ['POST', 'COMMENT', 'LIKE', 'DISLIKE', 'SEARCH', 'TREND', 'FOLLOW', 'MUTE', 'REFRESH', 'IDLE'],
}

export function buildStep3StatusCards({ isConsumerMode, runStatus }) {
  const rs = runStatus || {}

  if (isConsumerMode) {
    return [
      {
        platform: 'reddit',
        label: 'Consumer Propagation Stream',
        active: !!rs.reddit_running,
        completed: !!rs.reddit_completed,
        currentRound: rs.reddit_current_round || 0,
        actionsCount: rs.reddit_actions_count || 0,
        tooltipActions: STEP3_TOOLTIP_ACTIONS.reddit,
      },
    ]
  }

  return [
    {
      platform: 'twitter',
      label: 'Info Plaza',
      active: !!rs.twitter_running,
      completed: !!rs.twitter_completed,
      currentRound: rs.twitter_current_round || 0,
      actionsCount: rs.twitter_actions_count || 0,
      tooltipActions: STEP3_TOOLTIP_ACTIONS.twitter,
    },
    {
      platform: 'reddit',
      label: 'Topic Community',
      active: !!rs.reddit_running,
      completed: !!rs.reddit_completed,
      currentRound: rs.reddit_current_round || 0,
      actionsCount: rs.reddit_actions_count || 0,
      tooltipActions: STEP3_TOOLTIP_ACTIONS.reddit,
    },
  ]
}

export function isConsumerProject(projectLike) {
  if (!projectLike || typeof projectLike !== 'object') {
    return false
  }
  return projectLike.project_type === 'consumer_test' || projectLike.projectType === 'consumer_test'
}

export function getConsumerTaskType(projectLike) {
  if (!projectLike || typeof projectLike !== 'object') {
    return 'concept_test'
  }
  if (projectLike.report_context?.task_type) {
    return projectLike.report_context.task_type
  }
  const brief = projectLike.consumer_brief || projectLike.consumerBrief || {}
  return brief.task_type || 'concept_test'
}

export function getConsumerTaskTypeLabel(taskType, t = null) {
  const key = `consumer.taskTypes.${taskType}`
  const fallbacks = {
    concept_test: 'Concept Test',
    packaging_test: 'Packaging Test',
    ab_test: 'A/B Test',
    price_test: 'Price Test',
  }
  return translate(t, key, fallbacks[taskType] || taskType)
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

// ============== Phase 4A: Source quality / confidence helpers ==============

export function resolveSourceQualitySummary(context) {
  if (!context || typeof context !== 'object') return null
  return context.source_quality_summary || null
}

export function formatSourceQualitySummary(summary = {}, t = null) {
  if (!summary || typeof summary !== 'object') return []
  const items = []
  const push = (key, labelKey, fallback, formatter) => {
    const raw = summary[key]
    if (raw === undefined || raw === null || raw === '') return
    const value = formatter ? formatter(raw) : String(raw)
    items.push({
      key,
      label: translate(t, labelKey, fallback),
      value,
    })
  }
  push('source_count', 'consumer.sourceQuality.sources', 'Sources', v => String(v))
  push('lane_a_count', 'consumer.sourceQuality.laneA', 'Lane A', v => String(v))
  push('lane_b_count', 'consumer.sourceQuality.laneB', 'Lane B', v => String(v))
  push('average_source_confidence', 'consumer.sourceQuality.avgConfidence', 'Avg Confidence', v => formatPercent(v))
  push('average_freshness_score', 'consumer.sourceQuality.avgFreshness', 'Avg Freshness', v => String(Math.round(v)))
  return items
}

export function getConfidenceBadgeClass(label) {
  const map = {
    high: 'badge-high',
    medium: 'badge-medium',
    low: 'badge-low',
    unknown: 'badge-unknown',
  }
  return map[label] || 'badge-unknown'
}

export function getConfidenceLabelText(label, t = null) {
  const map = {
    high: translate(t, 'consumer.confidence.high', 'High Confidence'),
    medium: translate(t, 'consumer.confidence.medium', 'Medium Confidence'),
    low: translate(t, 'consumer.confidence.low', 'Low Confidence'),
    unknown: translate(t, 'consumer.confidence.unknown', 'Unknown'),
  }
  return map[label] || map.unknown
}

export function mergeFindingConfidence(findings = [], findingConfidences = []) {
  const byId = {}
  for (const fc of findingConfidences) {
    const fid = fc.finding_id || ''
    if (fid) byId[fid] = fc
  }
  return findings.map(f => {
    const fid = f.findingId || f.finding_id || ''
    const fc = byId[fid]
    return {
      ...f,
      confidenceLabel: fc ? (fc.confidence_label || 'unknown') : 'unknown',
      confidenceScore: fc ? (fc.confidence_score || 0) : 0,
      confidenceReasons: fc ? (fc.confidence_reasons || []) : [],
      supportSummary: fc ? (fc.support_summary || '') : '',
    }
  })
}

export function buildConfidenceAwarePrompts(reportContext = {}, t = null) {
  const prompts = []
  if (!reportContext || typeof reportContext !== 'object') return prompts
  const reportConfidence = reportContext.report_confidence
  if (!reportConfidence || typeof reportConfidence !== 'object') return prompts

  const findingConfidences = reportConfidence.finding_confidences || []
  const lowConfidenceFindings = findingConfidences.filter(
    fc => (fc.confidence_label || '') === 'low' || (fc.confidence_label || '') === 'unknown',
  )

  if (lowConfidenceFindings.length > 0) {
    prompts.push(translate(
      t,
      'consumer.quickPrompts.lowConfidenceFindings',
      `${lowConfidenceFindings.length} finding(s) have low confidence. Which evidence should be strengthened?`,
      { count: lowConfidenceFindings.length },
    ))
  }

  const weakSupportCount = findingConfidences.filter(
    fc => (fc.confidence_reasons || []).some(r => r.includes('weak') || r.includes('insufficient')),
  ).length

  if (weakSupportCount > 0) {
    prompts.push(translate(
      t,
      'consumer.quickPrompts.weakEvidence',
      `${weakSupportCount} finding(s) rely on weak or insufficient evidence. What additional sources could improve support?`,
      { count: weakSupportCount },
    ))
  }

  if (reportConfidence.replay_alignment === 'not_replayed') {
    prompts.push(translate(
      t,
      'consumer.quickPrompts.replayCalibration',
      'This report has not been benchmarked. Run a replay to calibrate confidence.',
    ))
  }

  return prompts
}

export function buildReplayAwarePrompts(reportContext = {}, t = null) {
  const prompts = []
  if (!reportContext || typeof reportContext !== 'object') return prompts
  const replay = reportContext.replay_alignment
  if (!replay || typeof replay !== 'object') return prompts

  if (replay.status === 'drift' && replay.drift_signals && replay.drift_signals.length > 0) {
    prompts.push(translate(
      t,
      'consumer.quickPrompts.replayDrift',
      'Replay shows drift. What changed compared to the benchmark?',
      { count: replay.drift_signals.length },
    ))
  }

  if (replay.status === 'aligned') {
    prompts.push(translate(
      t,
      'consumer.quickPrompts.replayAligned',
      'Replay aligns with benchmark. What stable signals hold up best?',
    ))
  }

  if (replay.status === 'partial') {
    prompts.push(translate(
      t,
      'consumer.quickPrompts.replayPartial',
      'Replay is partially aligned. Which signals are inconsistent?',
    ))
  }

  return prompts
}

export function formatComparisonConfidence(comparisonConfidence = {}) {
  if (!comparisonConfidence || typeof comparisonConfidence !== 'object') {
    return {
      label: 'unknown',
      delta: 0,
      leftLabel: 'unknown',
      rightLabel: 'unknown',
      leftScore: 0,
      rightScore: 0,
      summary: '',
    }
  }
  return {
    label: comparisonConfidence.comparison_label || 'unknown',
    delta: comparisonConfidence.confidence_delta || 0,
    leftLabel: comparisonConfidence.left_confidence_label || 'unknown',
    rightLabel: comparisonConfidence.right_confidence_label || 'unknown',
    leftScore: comparisonConfidence.left_confidence_score || 0,
    rightScore: comparisonConfidence.right_confidence_score || 0,
    summary: comparisonConfidence.support_summary || '',
  }
}

export function buildTaskAwareConsumerQuickPrompts(reportContext = {}, t = null) {
  const prompts = []
  const taskType = reportContext.task_type || 'concept_test'

  if (taskType === 'packaging_test') {
    const hooks = reportContext.top_packaging_hooks?.[0]
    const trust = reportContext.top_trust_objections?.[0]
    const confusion = reportContext.top_confusion_triggers?.[0]
    if (hooks) {
      prompts.push(translate(t, 'consumer.quickPrompts.packagingHook', `Why did "${hooks}" become a top packaging hook?`, { point: hooks }))
    }
    if (trust) {
      prompts.push(translate(t, 'consumer.quickPrompts.packagingTrust', `Why did "${trust}" trigger a trust/credibility objection?`, { point: trust }))
    }
    if (confusion) {
      prompts.push(translate(t, 'consumer.quickPrompts.packagingConfusion', `How did "${confusion}" cause confusion about the packaging?`, { point: confusion }))
    }
  } else if (taskType === 'ab_test') {
    const variantDelta = reportContext.top_variant_deltas?.[0]
    const personaDivergence = reportContext.top_persona_divergences?.[0]
    const winningVariant = reportContext.winning_variant
    if (winningVariant) {
      prompts.push(translate(t, 'consumer.quickPrompts.abWinningVariant', `Why did variant "${winningVariant}" outperform the others?`, { variant: winningVariant }))
    }
    if (variantDelta) {
      prompts.push(translate(t, 'consumer.quickPrompts.abVariantDelta', `What explains the resonance/risk delta between "${variantDelta.left}" and "${variantDelta.right}"?`, { left: variantDelta.left, right: variantDelta.right }))
    }
    if (personaDivergence) {
      prompts.push(translate(t, 'consumer.quickPrompts.abPersonaDivergence', `Why did personas diverge between "${personaDivergence.variant_a}" and "${personaDivergence.variant_b}"?`, { variantA: personaDivergence.variant_a, variantB: personaDivergence.variant_b }))
    }
  } else if (taskType === 'price_test') {
    const acceptablePrice = reportContext.acceptable_price_points?.[0]
    const resistedPrice = reportContext.resisted_price_points?.[0]
    const objection = reportContext.top_price_objections?.[0]
    if (acceptablePrice) {
      prompts.push(translate(t, 'consumer.quickPrompts.priceAcceptable', `Why is "${acceptablePrice}" perceived as an acceptable price point?`, { point: acceptablePrice }))
    }
    if (resistedPrice) {
      prompts.push(translate(t, 'consumer.quickPrompts.priceResisted', `What objections does "${resistedPrice}" trigger?`, { point: resistedPrice }))
    }
    if (objection) {
      prompts.push(translate(t, 'consumer.quickPrompts.priceObjection', `How does "${objection}" affect perceived value for money?`, { point: objection }))
    }
  }

  return prompts
}

export function buildConsumerQuickPrompts(reportContext = {}, t = null) {
  const prompts = []
  const taskType = reportContext.task_type || 'concept_test'
  const resonance = reportContext.top_resonance_points?.[0]
  const risk = reportContext.top_risk_points?.[0]
  const misread = reportContext.top_misreads?.[0]

  // Task-aware prompts first
  const taskPrompts = buildTaskAwareConsumerQuickPrompts(reportContext, t)
  prompts.push(...taskPrompts)

  // Shared prompts for all task types (except when task-specific covers the same ground)
  if (taskType !== 'packaging_test') {
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

  const confidencePrompts = buildConfidenceAwarePrompts(reportContext, t)
  prompts.push(...confidencePrompts)

  return prompts
}
