// @ts-nocheck
export const CHANNEL_LABELS = {
  xiaohongshu: '小红书',
  douyin: '抖音',
  wechat_group: '微信群',
  ecommerce_review: '电商评论区',
  zhihu_qa: '知乎/问答社区',
  offline_word_of_mouth: '线下口碑',
  livestream: '直播间',
  sales_assistant: '导购场景',
}

function toNumber(value) {
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric : 0
}

function clamp01(value) {
  return Math.max(0, Math.min(1, toNumber(value)))
}

export function formatChannelPercent(value) {
  return `${Math.round(clamp01(value) * 100)}%`
}

export function formatChannelDelta(value) {
  const numeric = toNumber(value)
  const sign = numeric > 0 ? '+' : ''
  return `${sign}${Math.round(numeric * 100)}pp`
}

export function getChannelLabel(channelId) {
  return CHANNEL_LABELS[channelId] || channelId || '-'
}

function resolveChannelMetrics(context = {}) {
  if (context.channel_metrics?.channels) return context.channel_metrics
  if (context.channels) return context
  return { channels: {} }
}

export function buildChannelFitItems(context = {}) {
  const metrics = resolveChannelMetrics(context)
  const channelEntries = Object.entries(metrics.channels || {})
  const channels = channelEntries.map(([channelId, values]) => {
    const riskCandidates = [
      ['Misread', values.misread_risk || 0],
      ['Evidence', values.evidence_demand || 0],
      ['Price', values.price_resistance || 0],
    ].sort((a, b) => b[1] - a[1])
    return {
      channelId,
      label: getChannelLabel(channelId),
      fitScore: clamp01(values.fit_score),
      fitScoreText: formatChannelPercent(values.fit_score),
      primaryRisk: `${riskCandidates[0][0]} ${formatChannelPercent(riskCandidates[0][1])}`,
      misreadRiskText: formatChannelPercent(values.misread_risk),
      evidenceDemandText: formatChannelPercent(values.evidence_demand),
      priceResistanceText: formatChannelPercent(values.price_resistance),
    }
  }).sort((a, b) => b.fitScore - a.fitScore)

  return {
    summary: {
      bestLaunchChannel: getChannelLabel(metrics.best_launch_channel),
      highestMisreadChannel: getChannelLabel(metrics.highest_misread_channel),
      highestEvidenceDemandChannel: getChannelLabel(metrics.highest_evidence_demand_channel),
      highestPriceResistanceChannel: getChannelLabel(metrics.highest_price_resistance_channel),
    },
    channels,
  }
}

export function buildChannelHeatmapRows(channelMetrics = {}) {
  const metrics = resolveChannelMetrics(channelMetrics)
  const channels = Object.entries(metrics.channels || {})
  const dimensions = [
    ['claim', 'Channel x Claim', 'resonance'],
    ['segment', 'Channel x Persona Segment', 'fit_score'],
    ['risk', 'Channel x Risk Type', 'misread_risk'],
    ['purchaseIntent', 'Channel x Purchase Intent', 'purchase_intent_delta'],
  ]
  return dimensions.map(([key, label, metricKey]) => ({
    key,
    label,
    cells: channels.map(([channelId, values]) => ({
      channelId,
      channelLabel: getChannelLabel(channelId),
      metricKey,
      value: clamp01(values[metricKey]),
      valueText: formatChannelPercent(values[metricKey]),
    })),
  }))
}

export function buildPropagationTimelineItems(context = {}) {
  const completedRounds = Math.max(
    0,
    Math.floor(toNumber(context.society_rounds_completed ?? context.current_round ?? 10)),
  )
  const phases = [
    ['Initial reaction', 0, 0],
    ['Claim amplification', 1, 3],
    ['Objection emergence', 4, 6],
    ['Misread spread', 7, 9],
    ['Evidence repair', 10, 10],
  ]
  const items = []
  for (const [phase, start, end] of phases) {
    if (completedRounds < start) continue
    const actualEnd = Math.min(end, completedRounds)
    items.push({
      phase,
      roundRange: start === actualEnd ? `R${start}` : `R${start}-R${actualEnd}`,
      summary: timelineSummaryForPhase(phase, context),
    })
  }
  return items
}

function timelineSummaryForPhase(phase, context) {
  const metrics = resolveChannelMetrics(context)
  if (phase === 'Claim amplification') {
    return `Strongest channel: ${getChannelLabel(metrics.best_launch_channel)}`
  }
  if (phase === 'Objection emergence') {
    return `Evidence demand: ${getChannelLabel(metrics.highest_evidence_demand_channel)}`
  }
  if (phase === 'Misread spread') {
    return `Misread risk: ${getChannelLabel(metrics.highest_misread_channel)}`
  }
  if (phase === 'Evidence repair') {
    return 'Repair depends on proof and expert signals'
  }
  return 'First consumer impressions entered the channel runtime'
}

export function buildPropagationPathRows(context = {}) {
  const paths = context.cross_channel_paths || context.paths || []
  return paths.map((path, index) => ({
    key: path.path_id || `path-${index}`,
    firstActorId: path.first_actor_id || path.actor_id || '-',
    sourceChannelId: path.source_channel_id || '',
    targetChannelId: path.target_channel_id || '',
    sourceChannelLabel: getChannelLabel(path.source_channel_id),
    targetChannelLabel: getChannelLabel(path.target_channel_id),
    roundIndex: Number.isFinite(Number(path.round_index)) ? Number(path.round_index) : 0,
    triggerMetric: path.trigger_metric || '-',
    triggerValueText: formatChannelPercent(path.trigger_value),
    attitudeDeltaText: formatChannelDelta(path.attitude_delta),
    consumerProfileSummary: path.consumer_profile_summary || path.node_profile_summary || '-',
    hubScore: clamp01(path.hub_score),
    hubScoreText: formatChannelPercent(path.hub_score),
    criticalPath: Boolean(path.critical_path),
    crossSegmentDepth: path.cross_segment_depth || 0,
    crossChannelCount: path.cross_channel_count || 0,
    affectedSegmentsText: (path.affected_segments || []).join(', ') || '-',
    blockedNodesText: (path.blocked_nodes || []).join(', ') || '-',
    repairNodesText: (path.repair_nodes || []).join(', ') || '-',
  }))
}
