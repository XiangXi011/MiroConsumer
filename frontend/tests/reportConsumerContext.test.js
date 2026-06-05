import { test } from 'vitest'
import assert from 'node:assert/strict'

import { deriveReportConsumerContext } from '../src/utils/reportConsumerContext.ts'

test('deriveReportConsumerContext returns empty display state outside consumer mode', () => {
  const state = deriveReportConsumerContext({
    reportData: { report_context: { events_count: 8, source_catalog: [{ source_id: 's1' }] } },
    projectData: { project_type: 'default' },
  })

  assert.equal(state.isConsumerMode, false)
  assert.deepEqual(state.consumerMetricCards, [])
  assert.deepEqual(state.consumerSourceCatalog, [])
  assert.deepEqual(state.consumerRiskFindings, [])
  assert.equal(state.consumerTaskType, '')
})

test('deriveReportConsumerContext maps backend report context into Step4 header fields', () => {
  const state = deriveReportConsumerContext({
    reportData: {
      project_type: 'consumer_test',
      report_context: {
        task_type: 'packaging_test',
        report_confidence: { label: 'high' },
        replay_alignment: { status: 'aligned' },
        evidence_validation_summary: { valid_count: 3 },
        event_counts: { risk_discovery: 2, positive_relay: 0, clarification_recovery: 1 },
        top_risk_findings: [
          {
            finding_type: 'risk_signal',
            summary: 'Sugar claim is fragile',
            source_id: 'src_a',
            source_label: 'Brief',
            evidence: { support_level: 'medium' },
          },
        ],
        low_confidence_risk_findings: [
          { finding_type: 'risk_signal', summary: 'Weak sample size', support_level: 'low' },
        ],
        findings_requiring_more_evidence: [
          { finding_type: 'price_signal', summary: 'Needs price ladder evidence' },
        ],
        causal_voc_quotes: [
          { quote: 'This sounds too sweet.', bucket: 'risk', source_label: 'Interview' },
        ],
        top_clarification_opportunities: [
          { summary: 'Explain protein source' },
        ],
        causal_chains: [
          { finding_summary: 'Risk spread after label confusion' },
        ],
        persona_group_signals: {
          skeptical_parent: {
            amplified: ['risk_discovery'],
            blocked: ['clarification_recovery'],
          },
        },
        source_catalog: [{ source_id: 'src_a', label: 'Brief' }],
        enriched_findings: [
          {
            finding_type: 'risk_signal',
            confidence_label: 'medium',
            summary: 'Sugar concern',
            source_title: 'Brief Background',
            trust_tier: 2,
          },
        ],
        enriched_traces: [
          {
            query: 'sugar claims',
            source_title: 'Brief Background',
            trust_tier: 2,
            chunk_previews: [{ text_preview: 'sugar...' }],
          },
        ],
        top_packaging_hooks: ['resealable pouch'],
        top_trust_objections: ['unclear nutrition panel'],
        top_confusion_triggers: ['meal replacement wording'],
        winning_variant: 'B',
        top_variant_deltas: [{ variant: 'B', delta: 0.12 }],
        top_persona_divergences: [{ persona: 'Busy Parent' }],
        acceptable_price_points: ['$4.99'],
        resisted_price_points: ['$8.99'],
        top_price_objections: ['too premium'],
        price_context: 'snack aisle',
      },
    },
  })

  assert.equal(state.isConsumerMode, true)
  assert.equal(state.consumerReportTag, 'Packaging Test')
  assert.equal(state.consumerTaskType, 'packaging_test')
  assert.deepEqual(state.consumerReportConfidence, { label: 'high' })
  assert.deepEqual(state.consumerReplayAlignment, { status: 'aligned' })
  assert.deepEqual(state.consumerEvidenceValidationSummary, { valid_count: 3 })
  assert.deepEqual(state.consumerEventCounts.map(item => item.type), ['risk_discovery', 'clarification_recovery'])
  assert.equal(state.consumerRiskFindings[0].text, 'Sugar claim is fragile')
  assert.equal(state.consumerRiskFindings[0].supportLevel, 'medium')
  assert.equal(state.consumerLowConfidenceRiskFindings[0].text, 'Weak sample size')
  assert.equal(state.consumerFindingsRequiringMoreEvidence[0].text, 'Needs price ladder evidence')
  assert.equal(state.consumerCausalVocQuotes[0].quote, 'This sounds too sweet.')
  assert.equal(state.consumerClarificationOpportunities[0].text, 'Explain protein source')
  assert.equal(state.consumerCausalChains[0].description, 'Risk spread after label confusion')
  assert.deepEqual(state.consumerPersonaGroupSignals[0], {
    persona: 'skeptical_parent',
    amplifiedCount: 1,
    blockedCount: 1,
  })
  assert.equal(state.consumerSourceCatalog[0].source_id, 'src_a')
  assert.equal(state.consumerEnrichedFindings[0].sourceTitle, 'Brief Background')
  assert.equal(state.consumerEnrichedTraces[0].query, 'sugar claims')
  assert.equal(state.consumerPackagingHooks[0].text, 'resealable pouch')
  assert.equal(state.consumerPackagingTrustObjections[0].text, 'unclear nutrition panel')
  assert.equal(state.consumerPackagingConfusionTriggers[0].text, 'meal replacement wording')
  assert.equal(state.consumerABWinningVariant, 'B')
  assert.deepEqual(state.consumerABVariantDeltas, [{ variant: 'B', delta: 0.12 }])
  assert.deepEqual(state.consumerABPersonaDivergences, [{ persona: 'Busy Parent' }])
  assert.equal(state.consumerPriceAcceptablePoints[0].text, '$4.99')
  assert.equal(state.consumerPriceResistedPoints[0].text, '$8.99')
  assert.equal(state.consumerPriceObjections[0].text, 'too premium')
  assert.equal(state.consumerPriceContext, 'snack aisle')
})

test('deriveReportConsumerContext falls back to project task type for consumer tag', () => {
  const state = deriveReportConsumerContext({
    reportData: {
      project_type: 'consumer_test',
      report_context: {},
    },
    projectData: {
      consumer_brief: { task_type: 'price_test' },
    },
  })

  assert.equal(state.consumerReportTag, 'Price Test')
})
