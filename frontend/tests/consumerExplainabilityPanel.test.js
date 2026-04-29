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
