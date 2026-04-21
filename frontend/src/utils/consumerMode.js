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

  return prompts
}
