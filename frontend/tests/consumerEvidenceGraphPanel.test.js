import { test } from 'vitest'
import assert from 'node:assert/strict'
import { readFileSync, existsSync } from 'node:fs'
import { fileURLToPath } from 'url'
import { dirname, join } from 'path'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

const componentPath = join(__dirname, '../src/components/consumer/EvidenceGraphPanel.vue')
const step4Path = join(__dirname, '../src/components/Step4Report.vue')
const consumerApiPath = join(__dirname, '../src/api/consumer.ts')
const evidenceGraphStatePath = join(__dirname, '../src/composables/useStep4EvidenceGraphState.ts')

test('EvidenceGraphPanel.vue exists as a consumer report component', () => {
  assert.ok(existsSync(componentPath), 'EvidenceGraphPanel.vue must exist')
})

test('EvidenceGraphPanel.vue renders finding, evidence, and source graph structures', () => {
  const content = readFileSync(componentPath, 'utf-8')
  for (const token of [
    'graph.nodes',
    'graph.edges',
    'finding',
    'evidence',
    'source',
    'supported_by',
    'sourced_from',
    'low_confidence',
  ]) {
    assert.ok(content.includes(token), `missing graph token: ${token}`)
  }
})

test('Step4Report.vue fetches and mounts EvidenceGraphPanel in consumer mode', () => {
  const content = readFileSync(step4Path, 'utf-8')
  assert.ok(content.includes("import EvidenceGraphPanel from './consumer/EvidenceGraphPanel.vue'"), 'must import EvidenceGraphPanel')
  assert.ok(content.includes('useStep4EvidenceGraphState'), 'must delegate evidence graph fetching state')
  assert.ok(content.includes('<EvidenceGraphPanel'), 'must mount EvidenceGraphPanel')
  assert.ok(content.includes(':graph="evidenceGraph"'), 'must pass graph prop')
})

test('useStep4EvidenceGraphState fetches through consumer API', () => {
  const content = readFileSync(evidenceGraphStatePath, 'utf-8')
  assert.ok(content.includes('getReportEvidenceGraph'), 'must fetch evidence graph through consumer API')
})

test('consumer.js exports getReportEvidenceGraph', () => {
  const content = readFileSync(consumerApiPath, 'utf-8')
  assert.ok(content.includes('getReportEvidenceGraph'), 'consumer API must export getReportEvidenceGraph')
})
