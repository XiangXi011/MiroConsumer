<template>
  <div class="report-header-block">
    <div class="report-meta">
      <span class="report-tag">{{ consumerReportTag }}</span>
      <span class="report-id">ID: {{ reportId || 'REF-2024-X92' }}</span>
    </div>
    <h1 class="main-title">{{ title }}</h1>
    <p class="sub-title">{{ summary }}</p>
    <div class="header-divider"></div>

    <div v-if="isConsumerMode && consumerMetricCards.length > 0" class="consumer-header-grid">
      <div v-for="card in consumerMetricCards" :key="card.key" class="consumer-header-card">
        <span class="consumer-header-label">{{ card.label }}</span>
        <span class="consumer-header-value mono">{{ card.value }}</span>
      </div>
    </div>

    <!-- Report Confidence Summary -->
    <div v-if="isConsumerMode && consumerReportConfidence" class="consumer-confidence-strip">
      <div class="consumer-confidence-header">{{ $t('consumer.reportConfidence.title') }}</div>
      <div class="consumer-confidence-grid">
        <div class="consumer-confidence-card">
          <span class="consumer-confidence-label">{{ $t('consumer.reportConfidence.overallLabel') }}</span>
          <span class="consumer-confidence-value mono" :class="getConfidenceBadgeClass(consumerReportConfidence.confidence_label)">{{ getConfidenceLabelText(consumerReportConfidence.confidence_label, t) }}</span>
        </div>
        <div class="consumer-confidence-card">
          <span class="consumer-confidence-label">{{ $t('consumer.reportConfidence.scoreLabel') }}</span>
          <span class="consumer-confidence-value mono">{{ Math.round((consumerReportConfidence.confidence_score || 0) * 100) }}%</span>
        </div>
      </div>
    </div>

    <!-- Replay Alignment Status -->
    <div v-if="isConsumerMode && consumerReplayAlignment" class="consumer-confidence-strip">
      <div class="consumer-confidence-header">{{ $t('consumer.replayAlignment.title') }}</div>
      <div class="consumer-confidence-grid">
        <div class="consumer-confidence-card">
          <span class="consumer-confidence-label">{{ $t('consumer.replayAlignment.statusLabel') }}</span>
          <span class="consumer-confidence-value mono" :class="'replay-' + consumerReplayAlignment.status">{{ consumerReplayAlignment.status || 'not_replayed' }}</span>
        </div>
        <div v-if="consumerReplayAlignment.overall_score !== undefined && consumerReplayAlignment.overall_score !== null" class="consumer-confidence-card">
          <span class="consumer-confidence-label">{{ $t('consumer.replayAlignment.scoreLabel') }}</span>
          <span class="consumer-confidence-value mono">{{ Math.round((consumerReplayAlignment.overall_score || 0) * 100) }}%</span>
        </div>
        <div v-if="consumerReplayAlignment.drift_signals && consumerReplayAlignment.drift_signals.length > 0" class="consumer-confidence-card">
          <span class="consumer-confidence-label">{{ $t('consumer.replayAlignment.driftLabel') }}</span>
          <span class="consumer-confidence-value mono">{{ consumerReplayAlignment.drift_signals.length }}</span>
        </div>
      </div>
      <div v-if="consumerReplayAlignment.replay_summary" class="consumer-replay-summary">
        {{ consumerReplayAlignment.replay_summary }}
      </div>
    </div>

    <!-- Evidence Validation Summary -->
    <div v-if="isConsumerMode && consumerEvidenceValidationSummary" class="consumer-confidence-strip">
      <div class="consumer-confidence-header">{{ $t('consumer.evidenceValidation.title') }}</div>
      <div class="consumer-confidence-grid">
        <div class="consumer-confidence-card">
          <span class="consumer-confidence-label">{{ $t('consumer.evidenceValidation.supported') }}</span>
          <span class="consumer-confidence-value mono">{{ consumerEvidenceValidationSummary.supported_count || 0 }}</span>
        </div>
        <div class="consumer-confidence-card">
          <span class="consumer-confidence-label">{{ $t('consumer.evidenceValidation.weak') }}</span>
          <span class="consumer-confidence-value mono">{{ consumerEvidenceValidationSummary.weak_support_count || 0 }}</span>
        </div>
        <div class="consumer-confidence-card">
          <span class="consumer-confidence-label">{{ $t('consumer.evidenceValidation.insufficient') }}</span>
          <span class="consumer-confidence-value mono">{{ consumerEvidenceValidationSummary.insufficient_support_count || 0 }}</span>
        </div>
      </div>
    </div>

    <!-- Source Quality Summary -->
    <div v-if="isConsumerMode && consumerSourceQualitySummary.length > 0" class="consumer-confidence-strip">
      <div class="consumer-confidence-header">{{ $t('consumer.sourceQuality.title') }}</div>
      <div class="consumer-confidence-grid">
        <div v-for="item in consumerSourceQualitySummary" :key="item.key" class="consumer-confidence-card">
          <span class="consumer-confidence-label">{{ item.label }}</span>
          <span class="consumer-confidence-value mono">{{ item.value }}</span>
        </div>
      </div>
    </div>

    <div v-if="isConsumerMode && consumerVocHighlights.length > 0" class="consumer-voc-strip">
      <div class="consumer-voc-header">{{ $t('consumer.representativeVoc') }}</div>
      <div class="consumer-voc-list">
        <div v-for="quote in consumerVocHighlights" :key="quote.bucket" class="consumer-voc-item">
          <span class="consumer-voc-bucket">{{ quote.label }}</span>
          <span class="consumer-voc-text">"{{ quote.quote }}"</span>
        </div>
      </div>
    </div>

    <div v-if="isConsumerMode && consumerEventCounts.length > 0" class="consumer-events-strip">
      <div class="consumer-events-header">{{ $t('consumer.eventCounts') }}</div>
      <div class="consumer-events-grid report">
        <div
          v-for="evt in consumerEventCounts"
          :key="evt.type"
          class="consumer-event-chip report"
          :class="'event-' + evt.type"
        >
          <span class="event-type-label">{{ evt.label }}</span>
          <span class="event-type-count">{{ evt.count }}</span>
        </div>
      </div>
    </div>

    <div v-if="isConsumerMode && consumerRiskFindings.length > 0" class="consumer-findings-strip">
      <div class="consumer-findings-header">{{ $t('consumer.step4.riskFindingsTitle') }}</div>
      <div class="consumer-findings-list">
        <div v-for="(f, idx) in consumerRiskFindings" :key="idx" class="consumer-finding-item risk">
          <span class="finding-type">{{ f.typeLabel }}</span>
          <span class="finding-text">{{ f.text }}</span>
          <ConsumerExplainabilityPanel
            v-if="buildExplainabilityData(f)"
            :data="buildExplainabilityData(f)"
          />
        </div>
      </div>
    </div>

    <div v-if="isConsumerMode && consumerLowConfidenceRiskFindings.length > 0" class="consumer-findings-strip">
      <div class="consumer-findings-header">{{ $t('consumer.step4.lowConfidenceRiskFindingsTitle') }}</div>
      <div class="consumer-findings-list">
        <div v-for="(f, idx) in consumerLowConfidenceRiskFindings" :key="idx" class="consumer-finding-item risk">
          <span class="finding-type">{{ f.typeLabel }}</span>
          <span class="finding-text">{{ f.text }}</span>
          <ConsumerExplainabilityPanel
            v-if="buildExplainabilityData(f)"
            :data="buildExplainabilityData(f)"
          />
        </div>
      </div>
    </div>

    <div v-if="isConsumerMode && consumerFindingsRequiringMoreEvidence.length > 0" class="consumer-findings-strip">
      <div class="consumer-findings-header">{{ $t('consumer.step4.findingsRequiringMoreEvidenceTitle') }}</div>
      <div class="consumer-findings-list">
        <div v-for="(f, idx) in consumerFindingsRequiringMoreEvidence" :key="idx" class="consumer-finding-item">
          <span class="finding-type">{{ f.typeLabel }}</span>
          <span class="finding-text">{{ f.text }}</span>
          <ConsumerExplainabilityPanel
            v-if="buildExplainabilityData(f)"
            :data="buildExplainabilityData(f)"
          />
        </div>
      </div>
    </div>

    <div v-if="isConsumerMode && consumerCausalVocQuotes.length > 0" class="consumer-voc-strip">
      <div class="consumer-voc-header">{{ $t('consumer.step4.causalVocQuotesTitle') }}</div>
      <div class="consumer-voc-list">
        <div v-for="(q, idx) in consumerCausalVocQuotes" :key="idx" class="consumer-voc-item">
          <span class="consumer-voc-bucket">{{ q.bucket }}</span>
          <span class="consumer-voc-text">"{{ q.quote }}"</span>
          <ConsumerExplainabilityPanel
            v-if="buildExplainabilityData(q)"
            :data="buildExplainabilityData(q)"
          />
        </div>
      </div>
    </div>

    <div v-if="isConsumerMode && consumerClarificationOpportunities.length > 0" class="consumer-findings-strip">
      <div class="consumer-findings-header">{{ $t('consumer.step4.clarificationTitle') }}</div>
      <div class="consumer-findings-list">
        <div
          v-for="(c, idx) in consumerClarificationOpportunities"
          :key="idx"
          class="consumer-finding-item recovery"
        >
          <span class="finding-text">{{ c.text }}</span>
        </div>
      </div>
    </div>

    <div v-if="isConsumerMode && consumerCausalChains.length > 0" class="consumer-causal-strip">
      <div class="consumer-causal-header">{{ $t('consumer.step4.causalReportTitle') }}</div>
      <div class="consumer-causal-list">
        <div v-for="(chain, idx) in consumerCausalChains" :key="idx" class="consumer-causal-item">
          <span class="causal-chain-text">{{ chain.description }}</span>
        </div>
      </div>
    </div>

    <div v-if="isConsumerMode && consumerCascadeMetrics.length > 0" class="consumer-cascade-strip">
      <div class="consumer-cascade-header">{{ $t('consumer.cascade.title') }}</div>
      <div class="consumer-cascade-grid report">
        <div v-for="item in consumerCascadeMetrics" :key="item.key" class="consumer-cascade-card">
          <span class="consumer-cascade-label">{{ item.label }}</span>
          <span class="consumer-cascade-value mono">{{ item.value }}</span>
        </div>
      </div>
    </div>

    <div v-if="isConsumerMode && consumerPersonaGroupSignals.length > 0" class="consumer-persona-strip">
      <div class="consumer-findings-header">{{ $t('consumer.personaGroupSignals') }}</div>
      <div class="consumer-persona-list">
        <div v-for="(p, idx) in consumerPersonaGroupSignals" :key="idx" class="consumer-persona-item">
          <span class="persona-name">{{ p.persona }}</span>
          <span v-if="p.amplifiedCount > 0" class="persona-signal amplified">+{{ p.amplifiedCount }}</span>
          <span v-if="p.blockedCount > 0" class="persona-signal blocked">-{{ p.blockedCount }}</span>
        </div>
      </div>
    </div>

    <div v-if="isConsumerMode && consumerResearchSnapshot" class="consumer-findings-strip">
      <div class="consumer-findings-header">{{ $t('consumer.researchSnapshot') }}</div>
      <div class="snapshot-grid report">
        <div class="snapshot-item">
          <span class="snapshot-value">{{ consumerResearchSnapshot.source_count || 0 }}</span>
          <span class="snapshot-label">{{ $t('consumer.snapshotSources') }}</span>
        </div>
        <div class="snapshot-item">
          <span class="snapshot-value">{{ consumerResearchSnapshot.document_count || 0 }}</span>
          <span class="snapshot-label">{{ $t('consumer.snapshotDocuments') }}</span>
        </div>
        <div class="snapshot-item">
          <span class="snapshot-value">{{ consumerResearchSnapshot.chunk_count || 0 }}</span>
          <span class="snapshot-label">{{ $t('consumer.snapshotChunks') }}</span>
        </div>
        <div class="snapshot-item">
          <span class="snapshot-value">{{ consumerResearchSnapshot.finding_count || 0 }}</span>
          <span class="snapshot-label">{{ $t('consumer.snapshotFindings') }}</span>
        </div>
        <div class="snapshot-item">
          <span class="snapshot-value">{{ consumerResearchSnapshot.retrieval_trace_count || 0 }}</span>
          <span class="snapshot-label">{{ $t('consumer.snapshotTraces') }}</span>
        </div>
      </div>
    </div>

    <div v-if="isConsumerMode && consumerSourceCatalog.length > 0" class="consumer-findings-strip">
      <div class="consumer-findings-header">{{ $t('consumer.sourcesUsed') }}</div>
      <div class="consumer-source-list">
        <div
          v-for="source in consumerSourceCatalog"
          :key="source.source_id"
          class="consumer-source-chip"
        >
          <span class="source-label">{{ source.label }}</span>
          <span v-if="source.lane" class="source-lane">{{ source.lane }}</span>
          <span v-if="source.trust_tier" class="source-trust">T{{ source.trust_tier }}</span>
        </div>
      </div>
    </div>

    <div v-if="isConsumerMode && consumerEnrichedFindings.length > 0" class="consumer-findings-strip">
      <div class="consumer-findings-header">{{ $t('consumer.citationReadyFindings') }}</div>
      <div class="consumer-findings-list">
        <div
          v-for="(f, idx) in consumerEnrichedFindings"
          :key="idx"
          class="consumer-finding-item"
          :class="'type-' + f.findingType"
        >
          <span class="finding-type">{{ f.findingType }}</span>
          <span v-if="f.confidenceLabel" class="confidence-badge" :class="getConfidenceBadgeClass(f.confidenceLabel)">{{ getConfidenceLabelText(f.confidenceLabel, t) }}</span>
          <span class="finding-text">{{ f.summary }}</span>
          <div v-if="f.sourceTitle || f.sourceUri || f.evidencePreview" class="finding-evidence">
            <div v-if="f.sourceTitle" class="evidence-source">
              <span class="evidence-source-title">{{ f.sourceTitle }}</span>
              <a v-if="f.sourceUri" :href="f.sourceUri" target="_blank" class="evidence-source-uri">{{ f.sourceUri }}</a>
              <span v-if="f.sourceLane" class="evidence-lane-badge">{{ f.sourceLane }}</span>
              <span v-if="f.trustTier" class="evidence-trust-tier">T{{ f.trustTier }}</span>
            </div>
            <div v-if="f.evidencePreview" class="evidence-preview">"{{ f.evidencePreview }}"</div>
          </div>
          <div v-else-if="f.sourceLabel || f.sourceId || f.retrievalTraceId" class="finding-provenance">
            <span v-if="f.sourceLabel" class="prov-badge">{{ f.sourceLabel }}</span>
            <span v-if="f.sourceId" class="prov-id">src:{{ f.sourceId }}</span>
            <span v-if="f.snippetId" class="prov-id">snip:{{ f.snippetId }}</span>
            <span v-if="f.retrievalTraceId" class="prov-id">trace:{{ f.retrievalTraceId }}</span>
          </div>
        </div>
      </div>
    </div>

    <div v-if="isConsumerMode && consumerEnrichedTraces.length > 0" class="consumer-findings-strip">
      <div class="consumer-findings-header">{{ $t('consumer.retrievalTraces') }}</div>
      <div class="consumer-findings-list">
        <div
          v-for="(trace, idx) in consumerEnrichedTraces"
          :key="idx"
          class="consumer-finding-item"
        >
          <span class="finding-text">{{ trace.query }}</span>
          <div class="finding-evidence">
            <div v-if="trace.sourceTitle" class="evidence-source">
              <span class="evidence-source-title">{{ trace.sourceTitle }}</span>
              <span v-if="trace.sourceType" class="evidence-type-badge">{{ trace.sourceType }}</span>
              <span v-if="trace.trustTier" class="evidence-trust-tier">T{{ trace.trustTier }}</span>
            </div>
            <div v-if="trace.chunkPreviews.length > 0" class="evidence-previews">
              <div
                v-for="(preview, pidx) in trace.chunkPreviews.slice(0, 2)"
                :key="pidx"
                class="evidence-preview"
              >
                "{{ preview.text_preview }}"
              </div>
            </div>
            <div v-else class="finding-provenance">
              <span class="prov-badge">{{ trace.lane }}</span>
              <span class="prov-id">{{ trace.chunkCount }} chunks</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Phase 4B: Task-aware report sections -->
    <!-- Packaging Test -->
    <div v-if="isConsumerMode && consumerTaskType === 'packaging_test' && consumerPackagingHooks.length > 0" class="consumer-findings-strip">
      <div class="consumer-findings-header">{{ $t('consumer.step4.packagingHooksTitle') }}</div>
      <div class="consumer-findings-list">
        <div v-for="(item, idx) in consumerPackagingHooks" :key="idx" class="consumer-finding-item">
          <span class="finding-text">{{ item.text }}</span>
        </div>
      </div>
    </div>

    <div v-if="isConsumerMode && consumerTaskType === 'packaging_test' && consumerPackagingTrustObjections.length > 0" class="consumer-findings-strip">
      <div class="consumer-findings-header">{{ $t('consumer.step4.packagingTrustObjectionsTitle') }}</div>
      <div class="consumer-findings-list">
        <div v-for="(item, idx) in consumerPackagingTrustObjections" :key="idx" class="consumer-finding-item risk">
          <span class="finding-text">{{ item.text }}</span>
        </div>
      </div>
    </div>

    <div v-if="isConsumerMode && consumerTaskType === 'packaging_test' && consumerPackagingConfusionTriggers.length > 0" class="consumer-findings-strip">
      <div class="consumer-findings-header">{{ $t('consumer.step4.packagingConfusionTriggersTitle') }}</div>
      <div class="consumer-findings-list">
        <div v-for="(item, idx) in consumerPackagingConfusionTriggers" :key="idx" class="consumer-finding-item">
          <span class="finding-text">{{ item.text }}</span>
        </div>
      </div>
    </div>

    <!-- A/B Test -->
    <div v-if="isConsumerMode && consumerTaskType === 'ab_test' && consumerABWinningVariant" class="consumer-findings-strip">
      <div class="consumer-findings-header">{{ $t('consumer.step4.abWinningVariantTitle') }}</div>
      <div class="consumer-findings-list">
        <div class="consumer-finding-item">
          <span class="finding-text">{{ consumerABWinningVariant }}</span>
        </div>
      </div>
    </div>

    <div v-if="isConsumerMode && consumerTaskType === 'ab_test' && consumerABVariantDeltas.length > 0" class="consumer-findings-strip">
      <div class="consumer-findings-header">{{ $t('consumer.step4.abVariantDeltasTitle') }}</div>
      <div class="consumer-findings-list">
        <div v-for="(item, idx) in consumerABVariantDeltas" :key="idx" class="consumer-finding-item">
          <span class="finding-text">{{ item.description }}</span>
        </div>
      </div>
    </div>

    <div v-if="isConsumerMode && consumerTaskType === 'ab_test' && consumerABPersonaDivergences.length > 0" class="consumer-findings-strip">
      <div class="consumer-findings-header">{{ $t('consumer.step4.abPersonaDivergencesTitle') }}</div>
      <div class="consumer-findings-list">
        <div v-for="(item, idx) in consumerABPersonaDivergences" :key="idx" class="consumer-finding-item">
          <span class="finding-text">{{ item.description }}</span>
        </div>
      </div>
    </div>

    <!-- Price Test -->
    <div v-if="isConsumerMode && consumerTaskType === 'price_test' && consumerPriceAcceptablePoints.length > 0" class="consumer-findings-strip">
      <div class="consumer-findings-header">{{ $t('consumer.step4.priceAcceptablePointsTitle') }}</div>
      <div class="consumer-findings-list">
        <div v-for="(item, idx) in consumerPriceAcceptablePoints" :key="idx" class="consumer-finding-item">
          <span class="finding-text">{{ item.text }}</span>
        </div>
      </div>
    </div>

    <div v-if="isConsumerMode && consumerTaskType === 'price_test' && consumerPriceResistedPoints.length > 0" class="consumer-findings-strip">
      <div class="consumer-findings-header">{{ $t('consumer.step4.priceResistedPointsTitle') }}</div>
      <div class="consumer-findings-list">
        <div v-for="(item, idx) in consumerPriceResistedPoints" :key="idx" class="consumer-finding-item risk">
          <span class="finding-text">{{ item.text }}</span>
        </div>
      </div>
    </div>

    <div v-if="isConsumerMode && consumerTaskType === 'price_test' && consumerPriceObjections.length > 0" class="consumer-findings-strip">
      <div class="consumer-findings-header">{{ $t('consumer.step4.priceObjectionsTitle') }}</div>
      <div class="consumer-findings-list">
        <div v-for="(item, idx) in consumerPriceObjections" :key="idx" class="consumer-finding-item risk">
          <span class="finding-text">{{ item.text }}</span>
        </div>
      </div>
    </div>

    <div v-if="isConsumerMode && consumerTaskType === 'price_test' && consumerPriceContext" class="consumer-findings-strip">
      <div class="consumer-findings-header">{{ $t('consumer.step4.priceContextTitle') }}</div>
      <div class="consumer-findings-list">
        <div class="consumer-finding-item">
          <span class="finding-text">{{ consumerPriceContext }}</span>
        </div>
      </div>
    </div>

    <!-- Branch Comparison -->
    <div v-if="isConsumerMode && branchComparisonFormatted" class="consumer-findings-strip">
      <div class="consumer-findings-header">{{ $t('consumer.branchComparison.title') }}</div>
      <div class="consumer-comparison-summary">
        <div class="comparison-row">
          <span class="comparison-label">{{ $t('consumer.branchComparison.forkRound') }}</span>
          <span class="comparison-value mono">R{{ branchComparisonFormatted.forkRound }}</span>
        </div>
        <div class="comparison-row">
          <span class="comparison-label">{{ $t('consumer.branchComparison.interventions') }}</span>
          <span class="comparison-value mono">{{ branchComparisonFormatted.interventionCount }}</span>
        </div>
        <div class="comparison-row">
          <span class="comparison-label">{{ $t('consumer.branchComparison.baseAcceptance') }}</span>
          <span class="comparison-value mono">{{ branchComparisonFormatted.baseAcceptancePct }}</span>
        </div>
        <div class="comparison-row">
          <span class="comparison-label">{{ $t('consumer.branchComparison.branchAcceptance') }}</span>
          <span class="comparison-value mono" :class="{ 'delta-positive': branchComparisonFormatted.deltaText.startsWith('+'), 'delta-negative': branchComparisonFormatted.deltaText.startsWith('-') }">
            {{ branchComparisonFormatted.branchAcceptancePct }}
          </span>
        </div>
        <div class="comparison-row">
          <span class="comparison-label">{{ $t('consumer.branchComparison.delta') }}</span>
          <span class="comparison-value mono delta-text" :class="{ 'delta-positive': branchComparisonFormatted.deltaText.startsWith('+'), 'delta-negative': branchComparisonFormatted.deltaText.startsWith('-') }">
            {{ branchComparisonFormatted.deltaText }}
          </span>
        </div>
        <div v-if="branchComparisonFormatted.topResonanceDelta.length > 0" class="comparison-delta-quotes">
          <span class="comparison-label">{{ $t('consumer.branchComparison.newResonance') }}</span>
          <div class="comparison-quote-list">
            <span v-for="(q, idx) in branchComparisonFormatted.topResonanceDelta" :key="idx" class="comparison-quote">"{{ q }}"</span>
          </div>
        </div>
        <div v-if="branchComparisonFormatted.topRiskDelta.length > 0" class="comparison-delta-quotes">
          <span class="comparison-label">{{ $t('consumer.branchComparison.newRisk') }}</span>
          <div class="comparison-quote-list">
            <span v-for="(q, idx) in branchComparisonFormatted.topRiskDelta" :key="idx" class="comparison-quote">"{{ q }}"</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
// @ts-nocheck
import { useI18n } from 'vue-i18n'
import { getConfidenceBadgeClass, getConfidenceLabelText } from '../../utils/consumerMode'
import ConsumerExplainabilityPanel from './ConsumerExplainabilityPanel.vue'

const { t } = useI18n()

function buildExplainabilityData(item) {
  if (!item) return null
  const out = {}

  if (item.explainability) {
    Object.assign(out, item.explainability)
  }

  if (item.audit) {
    if (item.audit.evidence_validation_summary) {
      out.evidence_validation_result = item.audit.evidence_validation_summary.overall_status || 'unknown'
    }
    if (item.audit.evidence_gatekeeping_summary) {
      const gk = item.audit.evidence_gatekeeping_summary
      const blocked = gk.blocked_count || 0
      out.evidence_gatekeeping_result = blocked > 0 ? 'BLOCKED' : 'PASS'
    }
    if (item.audit.confidence !== undefined) {
      out.confidence = item.audit.confidence
    }
  }

  if (item.reasoningMetadata) {
    if (item.reasoningMetadata.llm_invoked !== undefined) {
      out.llm_invoked = item.reasoningMetadata.llm_invoked
    }
    if (item.reasoningMetadata.reasoning_backend) {
      out.reasoning_backend = item.reasoningMetadata.reasoning_backend
    }
    if (item.reasoningMetadata.reasoning_error) {
      out.reasoning_error = item.reasoningMetadata.reasoning_error
    }
  }

  if (item.evidence) {
    const srcCount = Number(item.evidence.source_count || 0)
    const simCount = Number(item.evidence.simulation_quote_count || 0)
    if (!out.source_type) {
      if (srcCount > 0 && simCount > 0) {
        out.source_type = 'mixed'
      } else if (simCount > 0) {
        out.source_type = 'simulation'
      } else if (srcCount > 0) {
        out.source_type = 'material'
      }
    }
    if (!out.source_visibility) {
      out.source_visibility = item.evidence.support_level || 'unknown'
    }
  }

  if (item.support) {
    if (!out.source_visibility) {
      out.source_visibility = item.support
    }
  }

  if (item.supportLevel) {
    if (!out.source_visibility) {
      out.source_visibility = item.supportLevel
    }
    if (!out.evidence_validation_result) {
      out.evidence_validation_result = item.supportLevel
    }
    if (!out.evidence_gatekeeping_result) {
      out.evidence_gatekeeping_result = item.supportLevel === 'supported'
        ? 'PASS'
        : item.supportLevel === 'weak_support'
          ? 'downgraded'
          : 'BLOCKED'
    }
  }

  if (item.sourceLabel || item.sourceId) {
    if (!out.source_visibility) {
      out.source_visibility = item.sourceLabel || item.sourceId
    }
    if (!out.source_type) {
      const sourceText = `${item.sourceLabel || ''} ${item.sourceId || ''}`.toLowerCase()
      out.source_type = sourceText.includes('simulation') || sourceText.includes('auto_enrich')
        ? 'simulation'
        : 'material'
    }
  }

  return Object.keys(out).length > 0 ? out : null
}

defineProps({
  reportId: String,
  title: String,
  summary: String,
  isConsumerMode: Boolean,
  consumerReportTag: String,
  consumerMetricCards: { type: Array, default: () => [] },
  consumerReportConfidence: Object,
  consumerReplayAlignment: Object,
  consumerEvidenceValidationSummary: Object,
  consumerSourceQualitySummary: { type: Array, default: () => [] },
  consumerVocHighlights: { type: Array, default: () => [] },
  consumerEventCounts: { type: Array, default: () => [] },
  consumerRiskFindings: { type: Array, default: () => [] },
  consumerClarificationOpportunities: { type: Array, default: () => [] },
  consumerCausalChains: { type: Array, default: () => [] },
  consumerCascadeMetrics: { type: Array, default: () => [] },
  consumerPersonaGroupSignals: { type: Array, default: () => [] },
  consumerResearchSnapshot: Object,
  consumerSourceCatalog: { type: Array, default: () => [] },
  consumerEnrichedFindings: { type: Array, default: () => [] },
  consumerEnrichedTraces: { type: Array, default: () => [] },
  consumerTaskType: String,
  consumerPackagingHooks: { type: Array, default: () => [] },
  consumerPackagingTrustObjections: { type: Array, default: () => [] },
  consumerPackagingConfusionTriggers: { type: Array, default: () => [] },
  consumerABWinningVariant: String,
  consumerABVariantDeltas: { type: Array, default: () => [] },
  consumerABPersonaDivergences: { type: Array, default: () => [] },
  consumerPriceAcceptablePoints: { type: Array, default: () => [] },
  consumerPriceResistedPoints: { type: Array, default: () => [] },
  consumerPriceObjections: { type: Array, default: () => [] },
  consumerPriceContext: String,
  branchComparisonFormatted: Object,
  consumerLowConfidenceRiskFindings: { type: Array, default: () => [] },
  consumerFindingsRequiringMoreEvidence: { type: Array, default: () => [] },
  consumerCausalVocQuotes: { type: Array, default: () => [] },
})
</script>

<style scoped>
.report-header-block {
  margin-bottom: 30px;
}

.report-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 24px;
}

.report-tag {
  background: #000000;
  color: #FFFFFF;
  font-size: 11px;
  font-weight: 700;
  padding: 4px 8px;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.report-id {
  font-size: 11px;
  color: #9CA3AF;
  font-weight: 500;
  letter-spacing: 0.02em;
}

.main-title {
  font-family: 'Times New Roman', Times, serif;
  font-size: 36px;
  font-weight: 700;
  color: #111827;
  line-height: 1.2;
  margin: 0 0 16px 0;
  letter-spacing: -0.02em;
}

.sub-title {
  font-family: 'Times New Roman', Times, serif;
  font-size: 16px;
  color: #6B7280;
  font-style: italic;
  line-height: 1.6;
  margin: 0 0 30px 0;
  font-weight: 400;
}

.header-divider {
  height: 1px;
  background: #E5E7EB;
  width: 100%;
}

.mono {
  font-family: 'JetBrains Mono', monospace;
}

.consumer-header-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-top: 24px;
}

.consumer-header-card {
  border: 1px solid #E5E7EB;
  background: #FAFAFA;
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.consumer-header-label {
  font-size: 11px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: #6B7280;
}

.consumer-header-value {
  font-size: 20px;
  font-weight: 700;
  color: #111827;
}

.consumer-voc-strip {
  margin-top: 18px;
  border: 1px solid #E5E7EB;
  background: #FCFCFC;
  padding: 16px 18px;
}

.consumer-voc-header {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #6B7280;
  margin-bottom: 10px;
}

.consumer-voc-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.consumer-voc-item {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}

.consumer-voc-bucket {
  min-width: 82px;
  font-size: 11px;
  font-weight: 700;
  color: #FF4500;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.consumer-voc-text {
  color: #374151;
  line-height: 1.6;
}

.snapshot-grid.report {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(90px, 1fr));
  gap: 10px;
  margin-top: 8px;
}

.snapshot-grid.report .snapshot-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 8px;
  background: #FAFAFA;
  border: 1px solid #EEE;
  border-radius: 4px;
}

.snapshot-grid.report .snapshot-value {
  font-family: 'JetBrains Mono', monospace;
  font-size: 1.1rem;
  font-weight: 600;
  color: #1E293B;
}

.snapshot-grid.report .snapshot-label {
  font-size: 0.65rem;
  color: #94A3B8;
  margin-top: 2px;
}

.finding-provenance {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 6px;
}

.prov-badge {
  font-size: 0.65rem;
  font-family: 'JetBrains Mono', monospace;
  padding: 2px 6px;
  background: #E0F2FE;
  color: #0369A1;
  border-radius: 4px;
}

.prov-id {
  font-size: 0.65rem;
  font-family: 'JetBrains Mono', monospace;
  color: #94A3B8;
}

.consumer-source-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.consumer-source-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  background: #F3F4F6;
  border: 1px solid #E5E7EB;
  border-radius: 999px;
  font-size: 12px;
}

.consumer-source-chip .source-label {
  color: #374151;
  font-weight: 500;
}

.consumer-source-chip .source-lane {
  font-size: 0.65rem;
  font-family: 'JetBrains Mono', monospace;
  padding: 1px 5px;
  background: #E0F2FE;
  color: #0369A1;
  border-radius: 3px;
}

.consumer-source-chip .source-trust {
  font-size: 0.65rem;
  font-family: 'JetBrains Mono', monospace;
  color: #6B7280;
}

.finding-evidence {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 8px;
  padding: 10px 12px;
  background: #FAFAF9;
  border-left: 3px solid #D6D3D1;
  border-radius: 0 6px 6px 0;
}

.evidence-source {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.evidence-source-title {
  font-size: 12px;
  font-weight: 600;
  color: #44403C;
}

.evidence-source-uri {
  font-size: 11px;
  color: #0369A1;
  text-decoration: none;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.evidence-source-uri:hover {
  text-decoration: underline;
}

.evidence-lane-badge {
  font-size: 0.65rem;
  font-family: 'JetBrains Mono', monospace;
  padding: 1px 5px;
  background: #E0F2FE;
  color: #0369A1;
  border-radius: 3px;
}

.evidence-type-badge {
  font-size: 0.65rem;
  font-family: 'JetBrains Mono', monospace;
  padding: 1px 5px;
  background: #F3E8FF;
  color: #7C3AED;
  border-radius: 3px;
}

.evidence-trust-tier {
  font-size: 0.65rem;
  font-family: 'JetBrains Mono', monospace;
  color: #6B7280;
}

.evidence-preview {
  font-size: 12px;
  color: #57534E;
  line-height: 1.5;
  font-style: italic;
}

.evidence-previews {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.consumer-comparison-summary {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 10px 12px;
  background: #F9FAFB;
  border-radius: 6px;
}

.comparison-row {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
}

.comparison-label {
  color: #6B7280;
  min-width: 140px;
}

.comparison-value {
  font-weight: 600;
  color: #111827;
}

.delta-positive {
  color: #059669;
}

.delta-negative {
  color: #DC2626;
}

.delta-text {
  font-weight: 700;
}

.comparison-delta-quotes {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 4px;
}

.comparison-quote-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.comparison-quote {
  font-size: 12px;
  color: #4B5563;
  font-style: italic;
  padding: 4px 8px;
  background: #FFFFFF;
  border-radius: 4px;
  border: 1px solid #E5E7EB;
}

.confidence-badge {
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 600;
  margin-right: 6px;
}

.badge-high {
  background: #D1FAE5;
  color: #065F46;
}

.badge-medium {
  background: #FEF3C7;
  color: #92400E;
}

.badge-low {
  background: #FEE2E2;
  color: #991B1B;
}

.badge-unknown {
  background: #F3F4F6;
  color: #6B7280;
}

.consumer-confidence-strip {
  margin-top: 12px;
  padding: 12px;
  background: #F9FAFB;
  border-radius: 8px;
  border: 1px solid #E5E7EB;
}

.consumer-confidence-header {
  font-size: 12px;
  font-weight: 600;
  color: #374151;
  margin-bottom: 8px;
}

.consumer-confidence-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 8px;
}

.consumer-confidence-card {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.consumer-confidence-label {
  font-size: 11px;
  color: #6B7280;
}

.consumer-confidence-value {
  font-size: 14px;
  font-weight: 600;
  color: #111827;
}

.replay-aligned {
  color: #047857;
}

.replay-partial {
  color: #B45309;
}

.replay-drift {
  color: #DC2626;
}

.replay-not_replayed {
  color: #6B7280;
}

.consumer-replay-summary {
  margin-top: 8px;
  font-size: 12px;
  color: #6B7280;
  line-height: 1.5;
}
</style>
