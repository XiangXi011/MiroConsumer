import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'url'
import { dirname, join } from 'path'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

const panelPath = join(__dirname, '../src/components/consumer/ConsumerExplainabilityPanel.vue')
const drawerPath = join(__dirname, '../src/components/consumer/ConsumerInsightDrawer.vue')

const panelContent = readFileSync(panelPath, 'utf-8')
const drawerContent = readFileSync(drawerPath, 'utf-8')

// --- ConsumerExplainabilityPanel.vue token/label assertions ---

test('ConsumerExplainabilityPanel.vue renders all required field labels', () => {
  for (const label of [
    'Explainability',
    'Source Visibility',
    'Source Type',
    'LLM Invoked',
    'Reasoning Backend',
    'Reasoning Error',
    'Template Fallback',
    'Confidence',
    'Evidence Validation',
    'Evidence Gatekeeping',
  ]) {
    assert.ok(panelContent.includes(label), `missing label: ${label}`)
  }
})

test('ConsumerExplainabilityPanel.vue binds required data paths', () => {
  for (const token of [
    'data.source_visibility',
    'data.source_type',
    'data.llm_invoked',
    'data.reasoning_backend',
    'data.reasoning_error',
    'data.confidence',
    'data.evidence_validation_result',
    'data.evidence_gatekeeping_result',
  ]) {
    assert.ok(panelContent.includes(token), `missing data path: ${token}`)
  }
})

test('ConsumerExplainabilityPanel.vue supports all three source type badges', () => {
  for (const badge of ['material', 'simulation', 'mixed']) {
    assert.ok(panelContent.includes(`xp-badge--${badge}`), `missing badge class for ${badge}`)
  }
})

test('ConsumerExplainabilityPanel.vue shows template fallback marker for template/template_fallback/mock backends', () => {
  assert.ok(panelContent.includes("'template_fallback'"), 'must check template_fallback')
  assert.ok(panelContent.includes("'template'"), 'must check template')
  assert.ok(panelContent.includes("'mock'"), 'must check mock')
  assert.ok(panelContent.includes('isTemplateFallback'), 'must use isTemplateFallback computed')
})

test('ConsumerExplainabilityPanel.vue formats confidence as percentage', () => {
  assert.ok(panelContent.includes('formatConfidence'), 'must have formatConfidence helper')
  assert.ok(panelContent.includes('Math.round(value * 100)'), 'must convert confidence to percentage')
})

// --- ConsumerInsightDrawer.vue integration assertions ---

test('ConsumerInsightDrawer.vue imports ConsumerExplainabilityPanel', () => {
  assert.ok(drawerContent.includes("import ConsumerExplainabilityPanel from './ConsumerExplainabilityPanel.vue'"), 'must import ConsumerExplainabilityPanel')
})

test('ConsumerInsightDrawer.vue mounts ConsumerExplainabilityPanel', () => {
  assert.ok(drawerContent.includes('ConsumerExplainabilityPanel'), 'must reference ConsumerExplainabilityPanel in template')
  assert.ok(drawerContent.includes(':data="explainabilityData"'), 'must bind explainabilityData prop')
  assert.ok(drawerContent.includes('v-if="hasExplainabilityData"'), 'must conditionally render with hasExplainabilityData')
})

test('ConsumerInsightDrawer.vue checks all four explainability trigger fields', () => {
  assert.ok(drawerContent.includes('result.evidence'), 'must check result.evidence')
  assert.ok(drawerContent.includes('result.explainability'), 'must check result.explainability')
  assert.ok(drawerContent.includes('result.audit'), 'must check result.audit')
  assert.ok(drawerContent.includes('result.reasoning_metadata'), 'must check result.reasoning_metadata')
})

test('ConsumerInsightDrawer.vue derives source_type from evidence counts', () => {
  assert.ok(drawerContent.includes("out.source_type = 'mixed'"), 'must derive mixed source_type')
  assert.ok(drawerContent.includes("out.source_type = 'simulation'"), 'must derive simulation source_type')
  assert.ok(drawerContent.includes("out.source_type = 'material'"), 'must derive material source_type')
})

test('ConsumerInsightDrawer.vue maps audit evidence gatekeeping to PASS/BLOCKED', () => {
  assert.ok(drawerContent.includes('evidence_gatekeeping_result'), 'must compute evidence_gatekeeping_result')
  assert.ok(drawerContent.includes("'PASS'"), 'must produce PASS result')
  assert.ok(drawerContent.includes("'BLOCKED'"), 'must produce BLOCKED result')
})

test('ConsumerInsightDrawer.vue preserves existing safeMarkdown rendering', () => {
  assert.ok(drawerContent.includes('renderSafeMarkdown'), 'must import renderSafeMarkdown')
  assert.ok(drawerContent.includes('renderMarkdown'), 'must use renderMarkdown helper')
  assert.ok(drawerContent.includes('v-html="renderMarkdown(result.details_markdown)"'), 'must render details_markdown via safeMarkdown')
})

test('ConsumerInsightDrawer.vue reads reasoning fields from reasoning_metadata', () => {
  assert.ok(drawerContent.includes('r.reasoning_metadata.llm_invoked'), 'must read llm_invoked from reasoning_metadata')
  assert.ok(drawerContent.includes('r.reasoning_metadata.reasoning_backend'), 'must read reasoning_backend from reasoning_metadata')
  assert.ok(drawerContent.includes('r.reasoning_metadata.reasoning_error'), 'must read reasoning_error from reasoning_metadata')
})

test('ConsumerInsightDrawer.vue reads audit validation and gatekeeping from audit object', () => {
  assert.ok(drawerContent.includes('r.audit.evidence_validation_summary'), 'must read evidence_validation_summary from audit')
  assert.ok(drawerContent.includes('r.audit.evidence_gatekeeping_summary'), 'must read evidence_gatekeeping_summary from audit')
})

// --- Phase 6J P1: ConsumerReportHeader explainability convergence ---

const headerPath = join(__dirname, '../src/components/consumer/ConsumerReportHeader.vue')
const headerContent = readFileSync(headerPath, 'utf-8')

const step4Path = join(__dirname, '../src/components/Step4Report.vue')
const step4Content = readFileSync(step4Path, 'utf-8')

test('ConsumerReportHeader.vue imports ConsumerExplainabilityPanel', () => {
  assert.ok(headerContent.includes("import ConsumerExplainabilityPanel from './ConsumerExplainabilityPanel.vue'"), 'must import ConsumerExplainabilityPanel')
})

test('ConsumerReportHeader.vue renders ConsumerExplainabilityPanel for top_risk_findings', () => {
  assert.ok(headerContent.includes('consumerRiskFindings'), 'must reference consumerRiskFindings')
  assert.ok(headerContent.includes('ConsumerExplainabilityPanel'), 'must render ConsumerExplainabilityPanel in header')
  assert.ok(headerContent.includes('buildExplainabilityData') || headerContent.includes('explainabilityData') || headerContent.includes(':data='), 'must bind explainability data')
})

test('ConsumerReportHeader.vue renders ConsumerExplainabilityPanel for low_confidence_risk_findings', () => {
  assert.ok(headerContent.includes('low_confidence_risk_findings') || headerContent.includes('consumerLowConfidence'), 'must handle low_confidence_risk_findings')
  assert.ok(headerContent.includes('ConsumerExplainabilityPanel'), 'must render ConsumerExplainabilityPanel')
})

test('ConsumerReportHeader.vue renders ConsumerExplainabilityPanel for findings_requiring_more_evidence', () => {
  assert.ok(headerContent.includes('findings_requiring_more_evidence') || headerContent.includes('consumerFindingsRequiring'), 'must handle findings_requiring_more_evidence')
  assert.ok(headerContent.includes('ConsumerExplainabilityPanel'), 'must render ConsumerExplainabilityPanel')
})

test('ConsumerReportHeader.vue renders ConsumerExplainabilityPanel for causal_voc_quotes', () => {
  assert.ok(headerContent.includes('causal_voc_quotes') || headerContent.includes('consumerCausalVoc'), 'must handle causal_voc_quotes')
  assert.ok(headerContent.includes('ConsumerExplainabilityPanel'), 'must render ConsumerExplainabilityPanel')
})

// --- Phase 6J P1: Step4Report explainability prop mapping ---

test('Step4Report.vue passes props for low confidence findings, findings requiring more evidence, and causal VOC quotes', () => {
  assert.ok(step4Content.includes('consumer-low-confidence-risk-findings'), 'must pass consumer-low-confidence-risk-findings prop')
  assert.ok(step4Content.includes('consumer-findings-requiring-more-evidence'), 'must pass consumer-findings-requiring-more-evidence prop')
  assert.ok(step4Content.includes('consumer-causal-voc-quotes'), 'must pass consumer-causal-voc-quotes prop')
})

test('Step4Report.vue maps explainability and audit data from reportContext finding fields', () => {
  assert.ok(step4Content.includes('explainability') && step4Content.includes('audit'), 'must reference explainability and audit')
  assert.ok(step4Content.includes('reportContext'), 'must derive from reportContext')
})

test('Step4Report.vue preserves source, evidence, and support metadata in top risk findings', () => {
  assert.ok(step4Content.includes('source') && step4Content.includes('evidence') && step4Content.includes('support'), 'must preserve source/evidence/support')
  assert.ok(step4Content.includes('top_risk_findings'), 'must reference top_risk_findings')
})

test('Step4Report.vue preserves support_level and source provenance for finding audit data', () => {
  assert.ok(step4Content.includes('supportLevel') && step4Content.includes('support_level'), 'must preserve support_level')
  assert.ok(step4Content.includes('sourceId') && step4Content.includes('source_id'), 'must preserve source_id')
  assert.ok(step4Content.includes('sourceLabel') && step4Content.includes('source_label'), 'must preserve source_label')
})

test('ConsumerReportHeader.vue builds explainability from finding source provenance fields', () => {
  assert.ok(headerContent.includes('item.sourceId'), 'must read sourceId')
  assert.ok(headerContent.includes('item.sourceLabel'), 'must read sourceLabel')
  assert.ok(headerContent.includes('item.supportLevel'), 'must read supportLevel')
})

// --- Phase 6J P1: i18n locale key assertions ---

const enPath = join(__dirname, '../../locales/en.json')
const zhPath = join(__dirname, '../../locales/zh.json')

const enJson = JSON.parse(readFileSync(enPath, 'utf-8'))
const zhJson = JSON.parse(readFileSync(zhPath, 'utf-8'))

function getPath(obj, path) {
  return path.split('.').reduce((o, k) => (o == null ? undefined : o[k]), obj)
}

const requiredI18nKeys = [
  'consumer.step4.lowConfidenceRiskFindingsTitle',
  'consumer.step4.findingsRequiringMoreEvidenceTitle',
  'consumer.step4.causalVocQuotesTitle',
]

for (const key of requiredI18nKeys) {
  test(`en.json contains i18n key ${key}`, () => {
    assert.notStrictEqual(getPath(enJson, key), undefined, `missing en.json key: ${key}`)
  })
  test(`zh.json contains i18n key ${key}`, () => {
    assert.notStrictEqual(getPath(zhJson, key), undefined, `missing zh.json key: ${key}`)
  })
}
