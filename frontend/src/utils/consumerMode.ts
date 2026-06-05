// @ts-nocheck
import { formatPercent, translate } from './consumerFormatting'
import { buildConfidenceAwarePrompts } from './consumerConfidence'

export { formatPercent, translate } from './consumerFormatting'
export {
  buildConfidenceAwarePrompts,
  buildReplayAwarePrompts,
  formatComparisonConfidence,
  formatSourceQualitySummary,
  getConfidenceBadgeClass,
  getConfidenceLabelText,
  mergeFindingConfidence,
  resolveSourceQualitySummary,
} from './consumerConfidence'
export {
  buildBranchAwarePrompts,
  buildComparisonAwarePrompts,
  buildInterventionPayload,
  clearSelectedBranch,
  clearSelectedComparison,
  formatBranchComparison,
  getInterventionDisplayText,
  loadSelectedBranch,
  loadSelectedComparison,
  restorePersistedBranchSelectionAfterLoad,
  saveSelectedBranch,
  saveSelectedComparison,
} from './consumerBranching'

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
