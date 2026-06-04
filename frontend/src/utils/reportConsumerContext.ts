// @ts-nocheck
import {
  buildConsumerMetricCards,
  formatCascadeMetrics,
  formatSourceQualitySummary,
  getConsumerEventLabel,
  getConsumerTaskType,
  getConsumerTaskTypeLabel,
  isConsumerProject,
  pickTopVocQuotes,
  resolveSourceQualitySummary,
} from './consumerMode'

function mapFinding(finding = {}) {
  return {
    typeLabel: finding.finding_type || '',
    text: finding.summary || '',
    source: finding.source || null,
    sourceId: finding.source_id || '',
    sourceLabel: finding.source_label || '',
    evidence: finding.evidence || null,
    support: finding.support || null,
    supportLevel: finding.support_level || finding.evidence?.support_level || '',
    explainability: finding.explainability || null,
    audit: finding.audit || null,
    reasoningMetadata: finding.reasoning_metadata || null,
  }
}

function mapTextItem(text) {
  return { text }
}

export function deriveReportConsumerContext({ reportData = {}, projectData = {}, t = null } = {}) {
  const isConsumerMode = isConsumerProject(reportData) || isConsumerProject(projectData)
  const reportContext = reportData?.report_context || {}

  if (!isConsumerMode) {
    return {
      isConsumerMode: false,
      reportContext,
      consumerReportTag: '',
      consumerMetricCards: [],
      consumerReportConfidence: null,
      consumerReplayAlignment: null,
      consumerEvidenceValidationSummary: null,
      consumerSourceQualitySummary: [],
      consumerVocHighlights: [],
      consumerEventCounts: [],
      consumerRiskFindings: [],
      consumerLowConfidenceRiskFindings: [],
      consumerFindingsRequiringMoreEvidence: [],
      consumerCausalVocQuotes: [],
      consumerClarificationOpportunities: [],
      consumerCausalChains: [],
      consumerCascadeMetrics: [],
      consumerPersonaGroupSignals: [],
      consumerResearchSnapshot: null,
      consumerSourceCatalog: [],
      consumerEnrichedFindings: [],
      consumerEnrichedTraces: [],
      consumerTaskType: '',
      consumerPackagingHooks: [],
      consumerPackagingTrustObjections: [],
      consumerPackagingConfusionTriggers: [],
      consumerABWinningVariant: '',
      consumerABVariantDeltas: [],
      consumerABPersonaDivergences: [],
      consumerPriceAcceptablePoints: [],
      consumerPriceResistedPoints: [],
      consumerPriceObjections: [],
      consumerPriceContext: '',
    }
  }

  const taskType = reportContext.task_type || getConsumerTaskType(projectData) || 'concept_test'
  const sourceQualitySummary = resolveSourceQualitySummary(reportContext)
  const eventCounts = reportContext.event_counts || {}
  const personaGroupSignals = reportContext.persona_group_signals || {}

  return {
    isConsumerMode: true,
    reportContext,
    consumerReportTag: getConsumerTaskTypeLabel(taskType, t),
    consumerMetricCards: buildConsumerMetricCards(reportContext, t),
    consumerReportConfidence: reportContext.report_confidence || null,
    consumerReplayAlignment: reportContext.replay_alignment || null,
    consumerEvidenceValidationSummary: reportContext.evidence_validation_summary || null,
    consumerSourceQualitySummary: formatSourceQualitySummary(sourceQualitySummary, t),
    consumerVocHighlights: pickTopVocQuotes(reportContext, t),
    consumerEventCounts: Object.entries(eventCounts)
      .filter(([, count]) => count > 0)
      .map(([type, count]) => ({
        type,
        count,
        label: getConsumerEventLabel(type, t),
      })),
    consumerRiskFindings: (reportContext.top_risk_findings || []).map(mapFinding),
    consumerLowConfidenceRiskFindings: (reportContext.low_confidence_risk_findings || []).map(mapFinding),
    consumerFindingsRequiringMoreEvidence: (reportContext.findings_requiring_more_evidence || []).map(mapFinding),
    consumerCausalVocQuotes: (reportContext.causal_voc_quotes || []).map(quote => ({
      quote: quote.quote || '',
      bucket: quote.bucket || '',
      source: quote.source || null,
      sourceId: quote.source_id || '',
      sourceLabel: quote.source_label || '',
      explainability: quote.explainability || null,
      audit: quote.audit || null,
      reasoningMetadata: quote.reasoning_metadata || null,
    })),
    consumerClarificationOpportunities: (reportContext.top_clarification_opportunities || [])
      .map(item => ({ text: item.summary || '' })),
    consumerCausalChains: (reportContext.causal_chains || [])
      .map(chain => ({ description: chain.finding_summary || '' })),
    consumerCascadeMetrics: formatCascadeMetrics(reportContext.cascade_metrics, t),
    consumerPersonaGroupSignals: Object.entries(personaGroupSignals).map(([persona, data]) => ({
      persona,
      amplifiedCount: (data.amplified || []).length,
      blockedCount: (data.blocked || []).length,
    })),
    consumerResearchSnapshot: reportContext.research_snapshot || null,
    consumerSourceCatalog: reportContext.source_catalog || [],
    consumerEnrichedFindings: (reportContext.enriched_findings || []).map(finding => ({
      findingType: finding.finding_type || '',
      confidenceLabel: finding.confidence_label || '',
      summary: finding.summary || '',
      sourceTitle: finding.source_title || '',
      sourceUri: finding.source_uri || '',
      sourceLane: finding.source_lane || '',
      trustTier: finding.trust_tier || '',
      evidencePreview: finding.evidence_preview || '',
      sourceLabel: finding.source_label || '',
      sourceId: finding.source_id || '',
      snippetId: finding.snippet_id || '',
      retrievalTraceId: finding.retrieval_trace_id || '',
    })),
    consumerEnrichedTraces: (reportContext.enriched_traces || []).map(trace => ({
      query: trace.query || '',
      sourceTitle: trace.source_title || '',
      sourceType: trace.source_type || '',
      trustTier: trace.trust_tier || '',
      chunkPreviews: trace.chunk_previews || [],
      lane: trace.lane || '',
      chunkCount: trace.chunk_count || 0,
    })),
    consumerTaskType: reportContext.task_type || '',
    consumerPackagingHooks: (reportContext.top_packaging_hooks || []).map(mapTextItem),
    consumerPackagingTrustObjections: (reportContext.top_trust_objections || []).map(mapTextItem),
    consumerPackagingConfusionTriggers: (reportContext.top_confusion_triggers || []).map(mapTextItem),
    consumerABWinningVariant: reportContext.winning_variant || '',
    consumerABVariantDeltas: reportContext.top_variant_deltas || [],
    consumerABPersonaDivergences: reportContext.top_persona_divergences || [],
    consumerPriceAcceptablePoints: (reportContext.acceptable_price_points || []).map(mapTextItem),
    consumerPriceResistedPoints: (reportContext.resisted_price_points || []).map(mapTextItem),
    consumerPriceObjections: (reportContext.top_price_objections || []).map(mapTextItem),
    consumerPriceContext: reportContext.price_context || '',
  }
}
