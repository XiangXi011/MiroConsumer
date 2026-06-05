// @ts-nocheck
import { formatPercent, translate } from './consumerFormatting'

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
