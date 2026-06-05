import { test } from 'vitest'
import assert from 'node:assert/strict'

import {
  buildConsumerMetricCards,
  buildConsumerQuickPrompts,
  buildTaskAwareConsumerQuickPrompts,
  buildSourceAwarePrompts,
  buildStep3StatusCards,
  formatCascadeMetrics,
  buildCascadeAwarePrompts,
  buildComparisonAwarePrompts,
  buildReplayAwarePrompts,
  isConsumerProject,
  pickTopVocQuotes,
  formatSourceQualitySummary,
  resolveSourceQualitySummary,
  getConfidenceBadgeClass,
  getConfidenceLabelText,
  mergeFindingConfidence,
  buildConfidenceAwarePrompts,
  formatComparisonConfidence,
  getConsumerTaskType,
} from '../src/utils/consumerMode.ts'

test('isConsumerProject supports backend and frontend project type shapes', () => {
  assert.equal(isConsumerProject({ project_type: 'consumer_test' }), true)
  assert.equal(isConsumerProject({ projectType: 'consumer_test' }), true)
  assert.equal(isConsumerProject({ project_type: 'default' }), false)
  assert.equal(isConsumerProject(null), false)
})

test('buildConsumerMetricCards formats propagation summary into compact cards', () => {
  const cards = buildConsumerMetricCards({
    summary: {
      initial_acceptance: { positive: 0.42 },
      post_propagation_acceptance: { positive: 0.67 },
      attitude_shift_rate: 0.31,
    },
    events_count: 18,
  })

  assert.deepEqual(cards, [
    { key: 'initial', label: 'Initial Acceptance', value: '42%' },
    { key: 'post', label: 'Post-Propagation Acceptance', value: '67%' },
    { key: 'shift', label: 'Attitude Shift', value: '31%' },
    { key: 'events', label: 'Captured Events', value: '18' },
  ])
})

test('pickTopVocQuotes returns one highlight per bucket in display order', () => {
  const quotes = pickTopVocQuotes({
    representative_voc_quotes: {
      resonance: [{ quote: 'This one feels easy to share.', engagement: 9, agent_id: 'a1' }],
      risk: [{ quote: 'I would question the low sugar promise.', engagement: 8, agent_id: 'a2' }],
      misread: [{ quote: 'Is this medicine or food?', engagement: 6, agent_id: 'a3' }],
    },
  })

  assert.deepEqual(quotes, [
    { bucket: 'resonance', label: 'Resonance', quote: 'This one feels easy to share.', engagement: 9, agentId: 'a1' },
    { bucket: 'risk', label: 'Risk', quote: 'I would question the low sugar promise.', engagement: 8, agentId: 'a2' },
    { bucket: 'misread', label: 'Misread', quote: 'Is this medicine or food?', engagement: 6, agentId: 'a3' },
  ])
})

test('buildConsumerQuickPrompts turns top findings into follow-up questions', () => {
  const prompts = buildConsumerQuickPrompts({
    top_resonance_points: ['portable breakfast'],
    top_risk_points: ['sweetener debate'],
    top_misreads: ['meal replacement confusion'],
  })

  assert.deepEqual(prompts, [
    'Why did "portable breakfast" become a top resonance point?',
    'Why did "sweetener debate" get amplified during propagation?',
    'How did "meal replacement confusion" turn into a misread?',
  ])
})

import { getConsumerEventLabel } from '../src/utils/consumerMode.ts'

test('getConsumerEventLabel returns label for known phase2 event types', () => {
  assert.ok(getConsumerEventLabel('risk_discovery').toLowerCase().includes('risk'))
  assert.ok(getConsumerEventLabel('positive_relay').toLowerCase().includes('positive') || getConsumerEventLabel('positive_relay').toLowerCase().includes('relay'))
  assert.ok(getConsumerEventLabel('misread_amplification').toLowerCase().includes('misread'))
  assert.ok(getConsumerEventLabel('skeptical_challenge').toLowerCase().includes('skeptical') || getConsumerEventLabel('skeptical_challenge').toLowerCase().includes('challenge'))
  assert.ok(getConsumerEventLabel('clarification_recovery').toLowerCase().includes('clarification') || getConsumerEventLabel('clarification_recovery').toLowerCase().includes('recovery'))
})

test('getConsumerEventLabel returns fallback for unknown event type', () => {
  assert.equal(getConsumerEventLabel('unknown_event'), 'unknown_event')
})

test('buildConsumerQuickPrompts includes causal spread prompt when persona_group_signals is a non-empty object map', () => {
  const prompts = buildConsumerQuickPrompts({
    persona_group_signals: {
      health_conscious_mom: { amplified: ['risk_discovery'], blocked: [] },
      fitness_beginner: { amplified: ['misread_amplification'], blocked: [] },
    },
  })

  const spreadPrompt = prompts.find(p => p.includes('spread'))
  assert.ok(spreadPrompt, 'Expected spread prompt to be present for non-empty object-map persona_group_signals')
})

test('buildConsumerQuickPrompts uses backend field shapes for phase2 gating', () => {
  const prompts = buildConsumerQuickPrompts({
    top_risk_findings: [{ finding_id: 'r1', finding_type: 'risk_discovery', summary: 'Sugar concern' }],
    causal_chains: [{ finding_summary: 'Sugar concern', event_ids: ['e1'], event_types: ['risk_discovery'] }],
    top_clarification_opportunities: [{ finding_id: 'c1', finding_type: 'clarification_recovery', summary: 'Protein clarified' }],
    event_led_reversals: [{ event_id: 'e2', event_type: 'clarification_recovery' }],
  })

  const triggerPrompt = prompts.find(p => p.includes('triggered'))
  const recoveryPrompt = prompts.find(p => p.includes('recover'))
  assert.ok(triggerPrompt, 'Expected trigger prompt from top_risk_findings/causal_chains')
  assert.ok(recoveryPrompt, 'Expected recovery prompt from clarifications/reversals')
})

test('buildConsumerQuickPrompts omits causal spread prompt when persona_group_signals is empty object', () => {
  const prompts = buildConsumerQuickPrompts({
    persona_group_signals: {},
  })

  const spreadPrompt = prompts.find(p => p.includes('spread'))
  assert.equal(spreadPrompt, undefined, 'Expected no spread prompt for empty object-map persona_group_signals')
})

test('buildConsumerQuickPrompts omits causal spread prompt when persona_group_signals is missing', () => {
  const prompts = buildConsumerQuickPrompts({
    top_resonance_points: ['portable breakfast'],
  })

  const spreadPrompt = prompts.find(p => p.includes('spread'))
  assert.equal(spreadPrompt, undefined, 'Expected no spread prompt when persona_group_signals is missing')
})

// Mirrors Step4Report.vue computed-property mapping; fails if field names drift from backend.
test('Step4Report field mapping renders non-empty results with real backend schema', () => {
  const reportContext = {
    top_risk_findings: [
      { finding_id: 'r1', finding_type: 'risk_discovery', summary: 'Sugar too high' },
    ],
    top_clarification_opportunities: [
      { finding_id: 'c1', finding_type: 'clarification_recovery', summary: 'Protein explained' },
    ],
    causal_chains: [
      { finding_summary: 'Sugar too high', event_ids: ['e1'], event_types: ['risk_discovery', 'misread_amplification'] },
    ],
  }

  const riskFindings = (reportContext.top_risk_findings || [])
    .filter(f => f && f.summary)
    .map(f => ({ text: f.summary, type: f.finding_type || '' }))

  const clarifications = (reportContext.top_clarification_opportunities || [])
    .filter(c => c && c.summary)
    .map(c => ({ text: c.summary }))

  const causalChains = (reportContext.causal_chains || [])
    .filter(c => c && c.finding_summary)
    .map(c => ({ description: `${c.finding_summary} → ${(c.event_types || []).join(', ')}` }))

  assert.equal(riskFindings.length, 1, 'Expected risk findings mapped from summary field')
  assert.equal(riskFindings[0].text, 'Sugar too high')
  assert.equal(clarifications.length, 1, 'Expected clarifications mapped from summary field')
  assert.equal(clarifications[0].text, 'Protein explained')
  assert.equal(causalChains.length, 1, 'Expected causal chains mapped from finding_summary field')
  assert.ok(causalChains[0].description.includes('Sugar too high'))
  assert.ok(causalChains[0].description.includes('risk_discovery'))
})

test('buildSourceAwarePrompts generates risk-source prompt when enriched risk finding has source_title', () => {
  const prompts = buildSourceAwarePrompts({
    enriched_findings: [
      { finding_type: 'risk_signal', summary: 'Sugar too high', source_title: 'Brief Background' },
    ],
    source_catalog: [{ source_id: 'src_a', label: 'Brief Background', lane: 'lane_a' }],
    causal_chains: [{ finding_summary: 'Sugar too high', event_ids: ['e1'], event_types: ['risk_discovery'] }],
  })

  assert.ok(prompts.some(p => p.includes('source') || p.includes('Source') || p.includes('来源')), 'Expected source-aware prompt')
  assert.ok(prompts.some(p => p.includes('Sugar too high')), 'Expected prompt to mention finding summary')
})

test('buildSourceAwarePrompts generates influence prompt when catalog and causal chains exist', () => {
  const prompts = buildSourceAwarePrompts({
    enriched_findings: [],
    source_catalog: [{ source_id: 'src_a', label: 'Brief Background' }],
    causal_chains: [{ finding_summary: 'X', event_ids: ['e1'], event_types: ['risk_discovery'] }],
  })

  assert.ok(prompts.some(p => p.includes('influenced') || p.includes('spread') || p.includes('扩散')), 'Expected influence prompt')
})

test('buildSourceAwarePrompts generates evidence prompt when finding has evidence_preview and source_title', () => {
  const prompts = buildSourceAwarePrompts({
    enriched_findings: [
      { finding_type: 'risk_signal', summary: 'Sugar concern', source_title: 'Web Article', evidence_preview: 'High sugar' },
    ],
    source_catalog: [],
    causal_chains: [],
  })

  assert.ok(prompts.some(p => p.includes('evidence') || p.includes('Evidence') || p.includes('证据') || p.includes('Web Article')), 'Expected evidence prompt')
})

test('buildSourceAwarePrompts returns empty array when no enriched data exists', () => {
  const prompts = buildSourceAwarePrompts({})
  assert.deepEqual(prompts, [])
})

test('buildConsumerQuickPrompts includes source-aware prompts when enriched findings exist', () => {
  const prompts = buildConsumerQuickPrompts({
    top_resonance_points: ['portable breakfast'],
    enriched_findings: [
      { finding_type: 'risk_signal', summary: 'Sugar too high', source_title: 'Brief Background', evidence_preview: 'High sugar' },
    ],
    source_catalog: [{ source_id: 'src_a', label: 'Brief Background', lane: 'lane_a' }],
    causal_chains: [{ finding_summary: 'Sugar too high', event_ids: ['e1'], event_types: ['risk_discovery'] }],
  })

  assert.ok(prompts.some(p => p.includes('portable breakfast')), 'Expected resonance prompt')
  assert.ok(prompts.some(p => p.includes('Sugar too high')), 'Expected source-risk prompt')
})

test('Step4 enriched field mapping renders readable provenance when backend provides enriched_findings', () => {
  const reportContext = {
    enriched_findings: [
      {
        finding_id: 'f1',
        finding_type: 'risk_signal',
        summary: 'Sugar concern',
        source_title: 'Brief Background',
        source_uri: 'file://brief.pdf',
        source_lane: 'lane_a',
        source_type: 'upload',
        trust_tier: 2,
        evidence_preview: 'Sugar content is higher than claimed.',
      },
    ],
  }

  const findings = (reportContext.enriched_findings || [])
    .filter(f => f && f.summary)
    .map(f => ({
      findingId: f.finding_id || '',
      findingType: f.finding_type || '',
      summary: f.summary,
      sourceTitle: f.source_title || '',
      sourceUri: f.source_uri || '',
      sourceLane: f.source_lane || '',
      sourceType: f.source_type || '',
      trustTier: f.trust_tier || 0,
      evidencePreview: f.evidence_preview || '',
    }))

  assert.equal(findings.length, 1)
  assert.equal(findings[0].sourceTitle, 'Brief Background')
  assert.equal(findings[0].sourceUri, 'file://brief.pdf')
  assert.equal(findings[0].sourceLane, 'lane_a')
  assert.equal(findings[0].trustTier, 2)
  assert.ok(findings[0].evidencePreview.includes('Sugar content'))
})

test('Step4 enriched field mapping falls back gracefully to raw findings when enriched_findings absent', () => {
  const reportContext = {
    research_findings: [
      { finding_id: 'f1', finding_type: 'risk_signal', summary: 'Sugar concern', source_label: 'brief_background' },
    ],
  }

  const enriched = reportContext.enriched_findings || []
  const findings = enriched.length > 0
    ? enriched.filter(f => f && f.summary)
    : (reportContext.research_findings || []).filter(f => f && f.summary)

  assert.equal(findings.length, 1)
  assert.equal(findings[0].summary, 'Sugar concern')
})

test('Step5 enriched trace mapping renders readable provenance when backend provides enriched_traces', () => {
  const reportContext = {
    enriched_traces: [
      {
        trace_id: 't1',
        query: 'sugar claims',
        lane: 'lane_a',
        source_title: 'Brief Background',
        source_uri: 'file://brief.pdf',
        source_type: 'upload',
        trust_tier: 2,
        chunk_previews: [{ chunk_id: 'chk_1', text_preview: 'Sugar content...' }],
        source_count: 1,
      },
    ],
  }

  const traces = (reportContext.enriched_traces || []).map(t => ({
    traceId: t.trace_id || '',
    query: t.query,
    lane: t.lane,
    sourceTitle: t.source_title || '',
    sourceUri: t.source_uri || '',
    sourceType: t.source_type || '',
    trustTier: t.trust_tier || 0,
    chunkPreviews: t.chunk_previews || [],
    sourceCount: t.source_count || 0,
  }))

  assert.equal(traces.length, 1)
  assert.equal(traces[0].sourceTitle, 'Brief Background')
  assert.equal(traces[0].sourceCount, 1)
  assert.equal(traces[0].chunkPreviews.length, 1)
})

import {
  loadSelectedBranch,
  saveSelectedBranch,
  clearSelectedBranch,
  loadSelectedComparison,
  saveSelectedComparison,
  clearSelectedComparison,
  formatBranchComparison,
  buildBranchAwarePrompts,
  buildInterventionPayload,
  getInterventionDisplayText,
  restorePersistedBranchSelectionAfterLoad,
} from '../src/utils/consumerMode.ts'

test('loadSelectedBranch returns null in non-browser environment', () => {
  assert.equal(loadSelectedBranch('sim_123'), null)
})

test('saveSelectedBranch does not throw in non-browser environment', () => {
  assert.doesNotThrow(() => saveSelectedBranch('sim_123', 'branch_abc'))
})

test('clearSelectedBranch does not throw in non-browser environment', () => {
  assert.doesNotThrow(() => clearSelectedBranch('sim_123'))
})

test('formatBranchComparison returns readable summary from backend context', () => {
  const context = {
    branch_id: 'branch_a',
    base_branch_id: 'branch_base',
    fork_round: 3,
    branch_name: 'Clarify sugar claim',
    branch_description: 'Inject clarification about sugar content',
    interventions: [{ intervention_id: 'i1', intervention_type: 'clarification_injection' }],
    base_summary: {
      events_count: 12,
      has_data: true,
      initial_acceptance: { positive: 0.4, neutral: 0.4, negative: 0.2 },
      post_propagation_acceptance: { positive: 0.35, neutral: 0.35, negative: 0.3 },
      attitude_shift_rate: 0.05,
      top_resonance_quotes: [{ quote: 'Easy to share' }],
      top_risk_quotes: [{ quote: 'Too sweet' }],
    },
    branch_summary: {
      events_count: 14,
      has_data: true,
      initial_acceptance: { positive: 0.4, neutral: 0.4, negative: 0.2 },
      post_propagation_acceptance: { positive: 0.55, neutral: 0.25, negative: 0.2 },
      attitude_shift_rate: 0.15,
      top_resonance_quotes: [{ quote: 'Easy to share' }, { quote: 'Good for kids' }],
      top_risk_quotes: [{ quote: 'Too sweet' }],
    },
  }

  const result = formatBranchComparison(context)
  assert.equal(result.branchId, 'branch_a')
  assert.equal(result.forkRound, 3)
  assert.equal(result.branchName, 'Clarify sugar claim')
  assert.equal(result.interventionCount, 1)
  assert.equal(result.baseAcceptancePct, '35%')
  assert.equal(result.branchAcceptancePct, '55%')
  assert.equal(result.deltaText, '+20pp')
  assert.equal(result.topResonanceDelta.length, 1)
  assert.equal(result.topResonanceDelta[0], 'Good for kids')
  assert.equal(result.topRiskDelta.length, 0)
})

test('formatBranchComparison handles missing data gracefully', () => {
  const result = formatBranchComparison({})
  assert.equal(result.forkRound, 0)
  assert.equal(result.interventionCount, 0)
  assert.equal(result.baseAcceptancePct, '0%')
  assert.equal(result.branchAcceptancePct, '0%')
  assert.equal(result.deltaText, '+0pp')
})

test('buildBranchAwarePrompts generates fork and intervention prompts when branch data exists', () => {
  const comparison = {
    branch_name: 'Test Branch',
    fork_round: 2,
    interventions: [{ intervention_type: 'clarification_injection' }],
    base_summary: { post_propagation_acceptance: { positive: 0.4 } },
    branch_summary: { post_propagation_acceptance: { positive: 0.5 } },
  }

  const prompts = buildBranchAwarePrompts(comparison)
  assert.ok(prompts.some(p => p.includes('Test Branch')), 'Expected branch name prompt')
  assert.ok(prompts.some(p => p.includes('intervention')), 'Expected intervention prompt')
  assert.ok(prompts.some(p => p.includes('improved') || p.includes('worsened')), 'Expected delta prompt')
})

test('buildBranchAwarePrompts returns empty array when no branch data', () => {
  const prompts = buildBranchAwarePrompts({})
  assert.equal(prompts.length, 0)
})

test('buildInterventionPayload uses type-specific keys per backend contract', () => {
  assert.deepEqual(buildInterventionPayload('clarification_injection', ' Hello '), { message: 'Hello' })
  assert.deepEqual(buildInterventionPayload('revised_claim_injection', ' New claim '), { claim: 'New claim' })
  assert.deepEqual(buildInterventionPayload('evidence_reveal', ' Evidence text '), { evidence: 'Evidence text' })
  assert.deepEqual(buildInterventionPayload('unknown_type', ' Fallback '), { text: 'Fallback' })
})

test('buildInterventionPayload trims and stringifies input', () => {
  assert.deepEqual(buildInterventionPayload('clarification_injection', '  '), { message: '' })
  assert.deepEqual(buildInterventionPayload('evidence_reveal', 123), { evidence: '123' })
})

test('getInterventionDisplayText reads correct payload key by type', () => {
  assert.equal(getInterventionDisplayText('clarification_injection', { message: 'Fix it' }), 'Fix it')
  assert.equal(getInterventionDisplayText('revised_claim_injection', { claim: 'Better claim' }), 'Better claim')
  assert.equal(getInterventionDisplayText('evidence_reveal', { evidence: 'Source A' }), 'Source A')
  assert.equal(getInterventionDisplayText('unknown_type', { text: 'Plain text' }), 'Plain text')
})

test('getInterventionDisplayText falls back gracefully for missing payload', () => {
  assert.equal(getInterventionDisplayText('clarification_injection', null), '')
  assert.equal(getInterventionDisplayText('evidence_reveal', {}), '')
  assert.equal(getInterventionDisplayText('unknown_type', { foo: 'bar' }), JSON.stringify({ foo: 'bar' }))
})

test('clearSelectedBranch removes persisted selection so missing branch is reset', () => {
  // Simulate save + clear cycle in a minimal way
  assert.doesNotThrow(() => {
    saveSelectedBranch('sim_reset_test', 'branch_old')
    clearSelectedBranch('sim_reset_test')
    const after = loadSelectedBranch('sim_reset_test')
    assert.equal(after, null)
  })
})

test('loadSelectedComparison returns null in non-browser environment', () => {
  assert.equal(loadSelectedComparison('sim_123'), null)
})

test('saveSelectedComparison does not throw in non-browser environment', () => {
  assert.doesNotThrow(() => saveSelectedComparison('sim_123', 'comp_abc'))
})

test('clearSelectedComparison does not throw in non-browser environment', () => {
  assert.doesNotThrow(() => clearSelectedComparison('sim_123'))
})

test('clearSelectedComparison removes persisted selection so missing comparison is reset', () => {
  assert.doesNotThrow(() => {
    saveSelectedComparison('sim_reset_test', 'comp_old')
    clearSelectedComparison('sim_reset_test')
    const after = loadSelectedComparison('sim_reset_test')
    assert.equal(after, null)
  })
})

test('formatCascadeMetrics returns readable cards for non-empty cascade metrics', () => {
  const items = formatCascadeMetrics({
    community_coverage: 0.75,
    cross_community_event_count: 3,
    bridge_event_count: 1,
    reversal_event_count: 2,
    narrative_takeover_score: 0.4,
    blocked_event_count: 1,
    amplifier_event_count: 4,
  })
  assert.ok(items.length > 0)
  assert.ok(items.some(i => i.key === 'community_coverage' && i.value === '75%'))
  assert.ok(items.some(i => i.key === 'cross_community_event_count' && i.value === '3'))
  assert.ok(items.some(i => i.key === 'bridge_event_count' && i.value === '1'))
})

test('formatCascadeMetrics returns empty array for empty metrics', () => {
  assert.deepEqual(formatCascadeMetrics({}), [])
  assert.deepEqual(formatCascadeMetrics(null), [])
})

test('buildCascadeAwarePrompts generates cross-community prompt when cross_community_event_count > 0', () => {
  const prompts = buildCascadeAwarePrompts({
    cascade_metrics: { cross_community_event_count: 2 },
  })
  assert.ok(prompts.some(p => p.includes('cross-community') || p.includes('spread across')), 'Expected cross-community prompt')
})

test('buildCascadeAwarePrompts generates blockage prompt when blocked_event_count > 0', () => {
  const prompts = buildCascadeAwarePrompts({
    cascade_metrics: { blocked_event_count: 1 },
  })
  assert.ok(prompts.some(p => p.includes('blockage') || p.includes('阻断')), 'Expected blockage prompt')
})

test('buildCascadeAwarePrompts generates narrative takeover prompt when narrative_takeover_score > 0', () => {
  const prompts = buildCascadeAwarePrompts({
    cascade_metrics: { narrative_takeover_score: 0.5 },
  })
  assert.ok(prompts.some(p => p.includes('narrative') || p.includes('dominating')), 'Expected narrative takeover prompt')
})

test('buildCascadeAwarePrompts returns empty array when all metrics are zero or absent', () => {
  const prompts = buildCascadeAwarePrompts({
    cascade_metrics: { cross_community_event_count: 0, blocked_event_count: 0 },
  })
  assert.deepEqual(prompts, [])
})

test('buildConsumerQuickPrompts includes cascade prompts when cascade_metrics present', () => {
  const prompts = buildConsumerQuickPrompts({
    top_resonance_points: ['portable breakfast'],
    cascade_metrics: { cross_community_event_count: 2, reversal_event_count: 1 },
  })
  assert.ok(prompts.some(p => p.includes('portable breakfast')), 'Expected resonance prompt')
  assert.ok(prompts.some(p => p.includes('cross-community') || p.includes('spread across')), 'Expected cascade cross-community prompt')
  assert.ok(prompts.some(p => p.includes('reversal') || p.includes('patterns')), 'Expected cascade reversal prompt')
})

test('buildComparisonAwarePrompts generates branch_vs_base prompt', () => {
  const prompts = buildComparisonAwarePrompts({
    mode: 'branch_vs_base',
    left: { label: 'Base Run', acceptance_positive: 0.35 },
    right: { label: 'Clarified Branch', acceptance_positive: 0.55 },
  })
  assert.ok(prompts.some(p => p.includes('Clarified Branch') && p.includes('Base Run')), 'Expected branch vs base prompt')
})

test('buildComparisonAwarePrompts generates run_vs_run prompt', () => {
  const prompts = buildComparisonAwarePrompts({
    mode: 'run_vs_run',
    left: { label: 'Run A' },
    right: { label: 'Run B' },
  })
  assert.ok(prompts.some(p => p.includes('Run A') && p.includes('Run B')), 'Expected run vs run prompt')
})

test('buildComparisonAwarePrompts generates project_vs_project prompt', () => {
  const prompts = buildComparisonAwarePrompts({
    mode: 'project_vs_project',
    left: { label: 'Project X' },
    right: { label: 'Project Y' },
  })
  assert.ok(prompts.some(p => p.includes('Project X') && p.includes('Project Y')), 'Expected project vs project prompt')
})

test('buildComparisonAwarePrompts generates resonance overlap prompt', () => {
  const prompts = buildComparisonAwarePrompts({
    mode: 'run_vs_run',
    left: { label: 'Run A' },
    right: { label: 'Run B' },
    resonance_overlap: ['portable breakfast', 'easy to share'],
  })
  assert.ok(prompts.some(p => p.includes('overlapping resonance') || p.includes('core message')), 'Expected resonance overlap prompt')
})

test('buildComparisonAwarePrompts generates recurring risk prompt', () => {
  const prompts = buildComparisonAwarePrompts({
    mode: 'run_vs_run',
    left: { label: 'Run A' },
    right: { label: 'Run B' },
    recurring_risk_signals: ['sugar concern', 'price too high'],
  })
  assert.ok(prompts.some(p => p.includes('risk signals') || p.includes('keep appearing')), 'Expected recurring risk prompt')
})

test('buildComparisonAwarePrompts generates divergence prompt for evidence-backed divergences', () => {
  const prompts = buildComparisonAwarePrompts({
    mode: 'run_vs_run',
    left: { label: 'Run A' },
    right: { label: 'Run B' },
    evidence_backed_divergences: [
      { signal: 'sweetener debate', left_presence: true, right_presence: false, left_sources: ['Source A'], right_sources: [] },
    ],
  })
  assert.ok(prompts.some(p => p.includes('sweetener debate') && p.includes('diverges')), 'Expected divergence prompt')
})

test('buildComparisonAwarePrompts generates acceptance delta prompt', () => {
  const prompts = buildComparisonAwarePrompts({
    mode: 'run_vs_run',
    left: { label: 'Run A', acceptance_positive: 0.35 },
    right: { label: 'Run B', acceptance_positive: 0.55 },
    acceptance_delta_pp: 20,
  })
  assert.ok(prompts.some(p => p.includes('20') && (p.includes('increased') || p.includes('decreased'))), 'Expected acceptance delta prompt')
})

test('buildComparisonAwarePrompts returns empty array for null or empty snapshot', () => {
  assert.deepEqual(buildComparisonAwarePrompts(null), [])
  assert.deepEqual(buildComparisonAwarePrompts({}), [])
  assert.deepEqual(buildComparisonAwarePrompts(undefined), [])
})

test('buildReplayAwarePrompts generates drift prompt with signal count', () => {
  const calls = []
  const t = (key, params) => {
    calls.push({ key, params })
    return `translated:${key}`
  }

  const prompts = buildReplayAwarePrompts({
    replay_alignment: {
      status: 'drift',
      drift_signals: ['risk_signal', 'acceptance_drop'],
    },
  }, t)

  assert.deepEqual(prompts, ['translated:consumer.quickPrompts.replayDrift'])
  assert.deepEqual(calls, [
    {
      key: 'consumer.quickPrompts.replayDrift',
      params: { count: 2 },
    },
  ])
})

test('buildReplayAwarePrompts generates aligned prompt', () => {
  const prompts = buildReplayAwarePrompts({
    replay_alignment: { status: 'aligned' },
  })

  assert.deepEqual(prompts, [
    'Replay aligns with benchmark. What stable signals hold up best?',
  ])
})

test('buildReplayAwarePrompts generates partial alignment prompt', () => {
  const prompts = buildReplayAwarePrompts({
    replay_alignment: { status: 'partial' },
  })

  assert.deepEqual(prompts, [
    'Replay is partially aligned. Which signals are inconsistent?',
  ])
})

test('buildReplayAwarePrompts returns empty array without replay alignment data', () => {
  assert.deepEqual(buildReplayAwarePrompts({}), [])
  assert.deepEqual(buildReplayAwarePrompts(null), [])
  assert.deepEqual(buildReplayAwarePrompts({ replay_alignment: null }), [])
  assert.deepEqual(buildReplayAwarePrompts({
    replay_alignment: {
      status: 'drift',
      drift_signals: [],
    },
  }), [])
})

// ============== Phase 4A: Source Quality / Confidence helpers ==============

test('resolveSourceQualitySummary reads source_quality_summary from top-level backend context', () => {
  const backendContext = {
    research_snapshot: { source_count: 10 },
    source_quality_summary: { source_count: 10, lane_a_count: 7, lane_b_count: 3 },
  }
  assert.deepEqual(resolveSourceQualitySummary(backendContext), backendContext.source_quality_summary)
  assert.equal(resolveSourceQualitySummary(null), null)
  assert.equal(resolveSourceQualitySummary({}), null)
  assert.equal(resolveSourceQualitySummary({ research_snapshot: {} }), null)
})

test('formatSourceQualitySummary returns empty array when summary is missing', () => {
  assert.deepEqual(formatSourceQualitySummary(null), [])
  assert.deepEqual(formatSourceQualitySummary({}), [])
})

test('formatSourceQualitySummary formats backend source_quality_summary into display items', () => {
  const items = formatSourceQualitySummary({
    source_count: 5,
    lane_a_count: 2,
    lane_b_count: 3,
    average_source_confidence: 0.72,
    average_freshness_score: 65,
    trust_tier_distribution: { '1': 2, '2': 3 },
    coverage_tag_distribution: { user_provided: 2, public_web: 3 },
  })
  assert.ok(items.length > 0, 'Expected non-empty items')
  assert.ok(items.some(i => i.key === 'source_count' && i.value === '5'), 'Expected source_count item')
  assert.ok(items.some(i => i.key === 'lane_a_count' && i.value === '2'), 'Expected lane_a_count item')
  assert.ok(items.some(i => i.key === 'lane_b_count' && i.value === '3'), 'Expected lane_b_count item')
  assert.ok(items.some(i => i.key === 'average_source_confidence' && i.value === '72%'), 'Expected confidence formatted as percent')
  assert.ok(items.some(i => i.key === 'average_freshness_score' && i.value === '65'), 'Expected freshness score')
})

test('getConfidenceBadgeClass maps confidence labels to CSS classes', () => {
  assert.equal(getConfidenceBadgeClass('high'), 'badge-high')
  assert.equal(getConfidenceBadgeClass('medium'), 'badge-medium')
  assert.equal(getConfidenceBadgeClass('low'), 'badge-low')
  assert.equal(getConfidenceBadgeClass('unknown'), 'badge-unknown')
  assert.equal(getConfidenceBadgeClass(''), 'badge-unknown')
})

test('getConfidenceLabelText maps confidence labels to readable text', () => {
  assert.equal(getConfidenceLabelText('high'), 'High Confidence')
  assert.equal(getConfidenceLabelText('medium'), 'Medium Confidence')
  assert.equal(getConfidenceLabelText('low'), 'Low Confidence')
  assert.equal(getConfidenceLabelText('unknown'), 'Unknown')
  assert.equal(getConfidenceLabelText(''), 'Unknown')
})

test('mergeFindingConfidence attaches confidence data to matching findings by finding_id', () => {
  const findings = [
    { findingId: 'f1', summary: 'Sugar concern' },
    { findingId: 'f2', summary: 'Protein benefit' },
  ]
  const confidences = [
    { finding_id: 'f1', confidence_label: 'high', confidence_score: 0.85 },
    { finding_id: 'f2', confidence_label: 'medium', confidence_score: 0.55 },
  ]
  const merged = mergeFindingConfidence(findings, confidences)
  assert.equal(merged[0].confidenceLabel, 'high')
  assert.equal(merged[0].confidenceScore, 0.85)
  assert.equal(merged[1].confidenceLabel, 'medium')
  assert.equal(merged[1].confidenceScore, 0.55)
})

test('mergeFindingConfidence falls back to unknown when no matching confidence', () => {
  const findings = [{ findingId: 'f1', summary: 'Sugar concern' }]
  const merged = mergeFindingConfidence(findings, [])
  assert.equal(merged[0].confidenceLabel, 'unknown')
  assert.equal(merged[0].confidenceScore, 0)
})

test('buildConfidenceAwarePrompts generates weak-evidence prompt when low-confidence findings exist', () => {
  const prompts = buildConfidenceAwarePrompts({
    report_confidence: {
      confidence_label: 'medium',
      confidence_score: 0.55,
      finding_confidences: [
        { finding_id: 'f1', confidence_label: 'low', confidence_score: 0.3 },
      ],
    },
  })
  assert.ok(prompts.some(p => p.includes('weak') || p.includes('low confidence') || p.includes('evidence')), 'Expected weak-evidence prompt')
})

test('buildConfidenceAwarePrompts generates replay prompt when replay_alignment is not_replayed', () => {
  const prompts = buildConfidenceAwarePrompts({
    report_confidence: {
      confidence_label: 'medium',
      confidence_score: 0.55,
      replay_alignment: 'not_replayed',
      finding_confidences: [],
    },
  })
  assert.ok(prompts.some(p => p.includes('replay') || p.includes('benchmark') || p.includes('calibration')), 'Expected replay prompt')
})

test('buildConfidenceAwarePrompts returns empty array when report_confidence is missing', () => {
  assert.deepEqual(buildConfidenceAwarePrompts({}), [])
  assert.deepEqual(buildConfidenceAwarePrompts(null), [])
})

test('formatComparisonConfidence formats comparison confidence into readable summary', () => {
  const result = formatComparisonConfidence({
    comparison_label: 'strongly_supported',
    confidence_delta: 0.15,
    left_confidence_label: 'medium',
    right_confidence_label: 'high',
    left_confidence_score: 0.55,
    right_confidence_score: 0.7,
  })
  assert.equal(result.label, 'strongly_supported')
  assert.equal(result.delta, 0.15)
  assert.equal(result.leftLabel, 'medium')
  assert.equal(result.rightLabel, 'high')
  assert.equal(result.leftScore, 0.55)
  assert.equal(result.rightScore, 0.7)
})

test('formatComparisonConfidence returns null-like fallback for missing data', () => {
  const result = formatComparisonConfidence(null)
  assert.equal(result.label, 'unknown')
  assert.equal(result.leftScore, 0)
  assert.equal(result.rightScore, 0)
})

// ============== Phase 4B: Task-aware quick prompts ==============

test('buildTaskAwareConsumerQuickPrompts generates packaging_test prompts', () => {
  const prompts = buildTaskAwareConsumerQuickPrompts({
    task_type: 'packaging_test',
    top_packaging_hooks: ['Eco-friendly design', 'Clear label'],
    top_trust_objections: ['Looks expensive'],
    top_confusion_triggers: ['Unclear disposal instructions'],
  })
  assert.ok(prompts.some(p => p.includes('Eco-friendly design')), 'Expected packaging hook prompt')
  assert.ok(prompts.some(p => p.includes('Looks expensive')), 'Expected trust objection prompt')
  assert.ok(prompts.some(p => p.includes('Unclear disposal instructions')), 'Expected confusion trigger prompt')
})

test('getConsumerTaskType reads task_type from report_context when present', () => {
  assert.equal(
    getConsumerTaskType({ report_context: { task_type: 'price_test' } }),
    'price_test'
  )
})

test('buildTaskAwareConsumerQuickPrompts generates ab_test prompts', () => {
  const prompts = buildTaskAwareConsumerQuickPrompts({
    task_type: 'ab_test',
    winning_variant: 'Variant A',
    top_variant_deltas: [{ left: 'Variant A', right: 'Variant B', description: 'A outperforms B on trust' }],
    top_persona_divergences: [{ variant_a: 'Variant A', variant_b: 'Variant B', description: 'Moms prefer A' }],
  })
  assert.ok(prompts.some(p => p.includes('Variant A') && p.includes('outperform')), 'Expected winning variant prompt')
  assert.ok(prompts.some(p => p.includes('Variant A') && p.includes('Variant B')), 'Expected variant delta prompt')
  assert.ok(prompts.some(p => p.includes('diverge') && p.includes('Variant A') && p.includes('Variant B')), 'Expected persona divergence prompt')
})

test('buildTaskAwareConsumerQuickPrompts generates price_test prompts', () => {
  const prompts = buildTaskAwareConsumerQuickPrompts({
    task_type: 'price_test',
    acceptable_price_points: ['$9.99', '$12.99'],
    resisted_price_points: ['$19.99'],
    top_price_objections: ['Too expensive for students'],
  })
  assert.ok(prompts.some(p => p.includes('$9.99')), 'Expected acceptable price prompt')
  assert.ok(prompts.some(p => p.includes('$19.99')), 'Expected resisted price prompt')
  assert.ok(prompts.some(p => p.includes('Too expensive for students')), 'Expected price objection prompt')
})

test('buildTaskAwareConsumerQuickPrompts returns empty array for concept_test with no task data', () => {
  const prompts = buildTaskAwareConsumerQuickPrompts({
    task_type: 'concept_test',
  })
  assert.deepEqual(prompts, [])
})

test('buildConsumerQuickPrompts includes task-aware prompts for packaging_test', () => {
  const prompts = buildConsumerQuickPrompts({
    task_type: 'packaging_test',
    top_packaging_hooks: ['Eco-friendly design'],
    top_resonance_points: ['portable breakfast'],
  })
  assert.ok(prompts.some(p => p.includes('Eco-friendly design')), 'Expected packaging hook prompt')
  assert.ok(!prompts.some(p => p.includes('portable breakfast')), 'Expected no resonance prompt in packaging_test')
})

test('buildConsumerQuickPrompts includes task-aware prompts for ab_test', () => {
  const prompts = buildConsumerQuickPrompts({
    task_type: 'ab_test',
    winning_variant: 'Variant A',
    top_resonance_points: ['portable breakfast'],
  })
  assert.ok(prompts.some(p => p.includes('Variant A')), 'Expected winning variant prompt')
  assert.ok(prompts.some(p => p.includes('portable breakfast')), 'Expected resonance prompt in ab_test')
})

test('buildConsumerQuickPrompts includes task-aware prompts for price_test', () => {
  const prompts = buildConsumerQuickPrompts({
    task_type: 'price_test',
    acceptable_price_points: ['$9.99'],
    top_resonance_points: ['portable breakfast'],
  })
  assert.ok(prompts.some(p => p.includes('$9.99')), 'Expected acceptable price prompt')
  assert.ok(prompts.some(p => p.includes('portable breakfast')), 'Expected resonance prompt in price_test')
})

// Mirrors Step4Report.vue computed-property mapping for task-aware fields.
test('Step4Report task-aware field mapping renders non-empty results for packaging_test', () => {
  const reportContext = {
    task_type: 'packaging_test',
    top_packaging_hooks: ['Eco-friendly design', 'Clear label'],
    top_trust_objections: ['Looks expensive'],
    top_confusion_triggers: ['Unclear disposal instructions'],
  }

  const hooks = (reportContext.top_packaging_hooks || []).filter(Boolean).map(text => ({ text }))
  const trust = (reportContext.top_trust_objections || []).filter(Boolean).map(text => ({ text }))
  const confusion = (reportContext.top_confusion_triggers || []).filter(Boolean).map(text => ({ text }))

  assert.equal(hooks.length, 2)
  assert.equal(hooks[0].text, 'Eco-friendly design')
  assert.equal(trust.length, 1)
  assert.equal(trust[0].text, 'Looks expensive')
  assert.equal(confusion.length, 1)
  assert.equal(confusion[0].text, 'Unclear disposal instructions')
})

test('Step4Report task-aware field mapping renders non-empty results for ab_test', () => {
  const reportContext = {
    task_type: 'ab_test',
    winning_variant: 'Variant A',
    top_variant_deltas: [
      { left: 'Variant A', right: 'Variant B', description: 'A outperforms B on trust' },
    ],
    top_persona_divergences: [
      { variant_a: 'Variant A', variant_b: 'Variant B', description: 'Moms prefer A' },
    ],
  }

  const winning = reportContext.winning_variant || ''
  const deltas = (reportContext.top_variant_deltas || [])
    .filter(d => d && (d.left || d.right))
    .map(d => ({
      left: d.left || '',
      right: d.right || '',
      description: d.description || `${d.left || ''} vs ${d.right || ''}`,
    }))
  const divergences = (reportContext.top_persona_divergences || [])
    .filter(d => d && (d.variant_a || d.variant_b))
    .map(d => ({
      variantA: d.variant_a || '',
      variantB: d.variant_b || '',
      description: d.description || `${d.variant_a || ''} vs ${d.variant_b || ''}`,
    }))

  assert.equal(winning, 'Variant A')
  assert.equal(deltas.length, 1)
  assert.equal(deltas[0].description, 'A outperforms B on trust')
  assert.equal(divergences.length, 1)
  assert.equal(divergences[0].description, 'Moms prefer A')
})

test('Step4Report task-aware field mapping renders non-empty results for price_test', () => {
  const reportContext = {
    task_type: 'price_test',
    acceptable_price_points: ['$9.99', '$12.99'],
    resisted_price_points: ['$19.99'],
    top_price_objections: ['Too expensive for students'],
    price_context: 'subscription monthly',
  }

  const acceptable = (reportContext.acceptable_price_points || []).filter(Boolean).map(text => ({ text }))
  const resisted = (reportContext.resisted_price_points || []).filter(Boolean).map(text => ({ text }))
  const objections = (reportContext.top_price_objections || []).filter(Boolean).map(text => ({ text }))
  const context = reportContext.price_context || ''

  assert.equal(acceptable.length, 2)
  assert.equal(acceptable[0].text, '$9.99')
  assert.equal(resisted.length, 1)
  assert.equal(resisted[0].text, '$19.99')
  assert.equal(objections.length, 1)
  assert.equal(objections[0].text, 'Too expensive for students')
  assert.equal(context, 'subscription monthly')
})

// ============== Phase 6E: Branch restore-state UX fix ==============

test('restorePersistedBranchSelectionAfterLoad sets branch, loads interventions, fetches status, and starts polling when running', async () => {
  const calls = []
  const branches = [{ branch_id: 'b1', name: 'Alpha', fork_round: 0 }]

  await restorePersistedBranchSelectionAfterLoad({
    branches,
    persistedBranchId: 'b1',
    setSelectedBranchId: (id) => calls.push({ method: 'setSelectedBranchId', id }),
    loadInterventions: async () => calls.push({ method: 'loadInterventions' }),
    fetchBranchStatus: async () => {
      calls.push({ method: 'fetchBranchStatus' })
      return { status: 'running' }
    },
    startPolling: () => calls.push({ method: 'startPolling' }),
    clearPersisted: () => calls.push({ method: 'clearPersisted' }),
  })

  assert.equal(calls.length, 4)
  assert.deepEqual(calls[0], { method: 'setSelectedBranchId', id: 'b1' })
  assert.deepEqual(calls[1], { method: 'loadInterventions' })
  assert.deepEqual(calls[2], { method: 'fetchBranchStatus' })
  assert.deepEqual(calls[3], { method: 'startPolling' })
})

test('restorePersistedBranchSelectionAfterLoad does not start polling when status is completed', async () => {
  const calls = []
  const branches = [{ branch_id: 'b1', name: 'Alpha', fork_round: 0 }]

  await restorePersistedBranchSelectionAfterLoad({
    branches,
    persistedBranchId: 'b1',
    setSelectedBranchId: (id) => calls.push({ method: 'setSelectedBranchId', id }),
    loadInterventions: async () => calls.push({ method: 'loadInterventions' }),
    fetchBranchStatus: async () => {
      calls.push({ method: 'fetchBranchStatus' })
      return { status: 'completed' }
    },
    startPolling: () => calls.push({ method: 'startPolling' }),
    clearPersisted: () => calls.push({ method: 'clearPersisted' }),
  })

  assert.equal(calls.length, 3)
  assert.deepEqual(calls[0], { method: 'setSelectedBranchId', id: 'b1' })
  assert.deepEqual(calls[1], { method: 'loadInterventions' })
  assert.deepEqual(calls[2], { method: 'fetchBranchStatus' })
  assert.ok(!calls.some(c => c.method === 'startPolling'), 'Expected no polling start for completed status')
})

test('restorePersistedBranchSelectionAfterLoad does not start polling when status is idle', async () => {
  const calls = []
  const branches = [{ branch_id: 'b1', name: 'Alpha', fork_round: 0 }]

  await restorePersistedBranchSelectionAfterLoad({
    branches,
    persistedBranchId: 'b1',
    setSelectedBranchId: (id) => calls.push({ method: 'setSelectedBranchId', id }),
    loadInterventions: async () => calls.push({ method: 'loadInterventions' }),
    fetchBranchStatus: async () => {
      calls.push({ method: 'fetchBranchStatus' })
      return { status: 'idle' }
    },
    startPolling: () => calls.push({ method: 'startPolling' }),
    clearPersisted: () => calls.push({ method: 'clearPersisted' }),
  })

  assert.equal(calls.length, 3)
  assert.ok(!calls.some(c => c.method === 'startPolling'), 'Expected no polling start for idle status')
})

test('restorePersistedBranchSelectionAfterLoad clears persisted selection when branch is missing', async () => {
  const calls = []
  const branches = [{ branch_id: 'b1', name: 'Alpha', fork_round: 0 }]

  await restorePersistedBranchSelectionAfterLoad({
    branches,
    persistedBranchId: 'missing_branch',
    setSelectedBranchId: (id) => calls.push({ method: 'setSelectedBranchId', id }),
    loadInterventions: async () => calls.push({ method: 'loadInterventions' }),
    fetchBranchStatus: async () => {
      calls.push({ method: 'fetchBranchStatus' })
      return { status: 'idle' }
    },
    startPolling: () => calls.push({ method: 'startPolling' }),
    clearPersisted: () => calls.push({ method: 'clearPersisted' }),
  })

  assert.equal(calls.length, 2)
  assert.deepEqual(calls[0], { method: 'clearPersisted' })
  assert.deepEqual(calls[1], { method: 'setSelectedBranchId', id: '' })
  assert.ok(!calls.some(c => c.method === 'loadInterventions'), 'Expected no intervention load for missing branch')
  assert.ok(!calls.some(c => c.method === 'fetchBranchStatus'), 'Expected no status fetch for missing branch')
})

test('restorePersistedBranchSelectionAfterLoad does nothing when no persisted branch', async () => {
  const calls = []
  const branches = [{ branch_id: 'b1', name: 'Alpha', fork_round: 0 }]

  await restorePersistedBranchSelectionAfterLoad({
    branches,
    persistedBranchId: null,
    setSelectedBranchId: (id) => calls.push({ method: 'setSelectedBranchId', id }),
    loadInterventions: async () => calls.push({ method: 'loadInterventions' }),
    fetchBranchStatus: async () => {
      calls.push({ method: 'fetchBranchStatus' })
      return { status: 'idle' }
    },
    startPolling: () => calls.push({ method: 'startPolling' }),
    clearPersisted: () => calls.push({ method: 'clearPersisted' }),
  })

  assert.equal(calls.length, 0, 'Expected no calls when no persisted branch')
})

// ============== Phase 6E: Step3 consumer-mode status cards ==============

test('buildStep3StatusCards returns one reddit-backed card in consumer mode', () => {
  const cards = buildStep3StatusCards({
    isConsumerMode: true,
    runStatus: {
      reddit_running: true,
      reddit_completed: false,
      reddit_current_round: 3,
      reddit_actions_count: 12,
    },
  })

  assert.equal(cards.length, 1)
  assert.equal(cards[0].platform, 'reddit')
  assert.equal(cards[0].label, 'Consumer Propagation Stream')
  assert.equal(cards[0].active, true)
  assert.equal(cards[0].completed, false)
  assert.equal(cards[0].currentRound, 3)
  assert.equal(cards[0].actionsCount, 12)
  assert.deepEqual(cards[0].tooltipActions, ['POST', 'COMMENT', 'LIKE', 'DISLIKE', 'SEARCH', 'TREND', 'FOLLOW', 'MUTE', 'REFRESH', 'IDLE'])
})

test('buildStep3StatusCards returns two platform cards in non-consumer mode with Info Plaza and Topic Community labels', () => {
  const cards = buildStep3StatusCards({
    isConsumerMode: false,
    runStatus: {
      twitter_running: true,
      twitter_completed: false,
      twitter_current_round: 2,
      twitter_actions_count: 8,
      reddit_running: true,
      reddit_completed: true,
      reddit_current_round: 5,
      reddit_actions_count: 20,
    },
  })

  assert.equal(cards.length, 2)
  assert.equal(cards[0].platform, 'twitter')
  assert.equal(cards[0].label, 'Info Plaza')
  assert.equal(cards[0].active, true)
  assert.equal(cards[0].completed, false)
  assert.equal(cards[0].currentRound, 2)
  assert.equal(cards[0].actionsCount, 8)
  assert.deepEqual(cards[0].tooltipActions, ['POST', 'LIKE', 'REPOST', 'QUOTE', 'FOLLOW', 'IDLE'])

  assert.equal(cards[1].platform, 'reddit')
  assert.equal(cards[1].label, 'Topic Community')
  assert.equal(cards[1].active, true)
  assert.equal(cards[1].completed, true)
  assert.equal(cards[1].currentRound, 5)
  assert.equal(cards[1].actionsCount, 20)
  assert.deepEqual(cards[1].tooltipActions, ['POST', 'COMMENT', 'LIKE', 'DISLIKE', 'SEARCH', 'TREND', 'FOLLOW', 'MUTE', 'REFRESH', 'IDLE'])
})

test('buildStep3StatusCards consumer mode card uses reddit_running/reddit_completed/reddit_current_round/reddit_actions_count', () => {
  const cards = buildStep3StatusCards({
    isConsumerMode: true,
    runStatus: {
      reddit_running: false,
      reddit_completed: true,
      reddit_current_round: 0,
      reddit_actions_count: 0,
    },
  })

  assert.equal(cards.length, 1)
  assert.equal(cards[0].active, false)
  assert.equal(cards[0].completed, true)
  assert.equal(cards[0].currentRound, 0)
  assert.equal(cards[0].actionsCount, 0)
})

test('buildStep3StatusCards handles null runStatus gracefully', () => {
  const consumerCards = buildStep3StatusCards({ isConsumerMode: true, runStatus: null })
  assert.equal(consumerCards.length, 1)
  assert.equal(consumerCards[0].currentRound, 0)
  assert.equal(consumerCards[0].actionsCount, 0)
  assert.equal(consumerCards[0].active, false)

  const normalCards = buildStep3StatusCards({ isConsumerMode: false, runStatus: null })
  assert.equal(normalCards.length, 2)
  assert.equal(normalCards[0].currentRound, 0)
  assert.equal(normalCards[1].currentRound, 0)
})
