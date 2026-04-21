function formatPercent(value) {
  const numeric = Number(value)
  if (!Number.isFinite(numeric) || numeric <= 0) {
    return '0%'
  }
  return `${Math.round(numeric * 100)}%`
}

function translate(t, key, fallback, params = {}) {
  if (typeof t !== 'function') {
    return fallback
  }
  return t(key, params)
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

  return prompts
}
