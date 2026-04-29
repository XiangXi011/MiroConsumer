import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const consumerSrc = readFileSync(
  new URL('../src/api/consumer.js', import.meta.url),
  'utf-8'
)
const factorySrc = readFileSync(
  new URL('../src/api/consumerFactory.js', import.meta.url),
  'utf-8'
)

// ============== Canonical route path tests (source-level smoke) ==============

test('consumer factory uses correct backend route for getConsumerSummary', () => {
  assert.ok(
    factorySrc.includes('/api/consumer/simulation/${simulationId}/consumer-summary'),
    'Expected getConsumerSummary to use /api/consumer/simulation/${simulationId}/consumer-summary'
  )
})

test('consumer factory uses correct backend routes for Phase 6H channel APIs', () => {
  for (const path of [
    '/api/consumer/simulations/${simulationId}/channel-summary',
    '/api/consumer/simulations/${simulationId}/channel-events',
    '/api/consumer/simulations/${simulationId}/propagation-paths',
  ]) {
    assert.ok(factorySrc.includes(path), `Expected factory to include ${path}`)
  }
})

test('consumer factory uses correct backend routes for Phase 6I interview APIs', () => {
  for (const path of [
    '/api/consumer/simulations/${simulationId}/representative-agents',
    '/api/consumer/simulations/${simulationId}/interviews',
    '/api/consumer/simulations/${simulationId}/focus-groups',
    '/api/consumer/simulations/${simulationId}/interviews/history',
    '/api/consumer/simulations/${simulationId}/focus-groups/history',
  ]) {
    assert.ok(factorySrc.includes(path), `Expected factory to include ${path}`)
  }
})

test('consumer factory uses correct backend route for listBranches', () => {
  assert.ok(
    factorySrc.includes('/api/consumer/simulations/${simulationId}/branches'),
    'Expected listBranches to use /api/consumer/simulations/${simulationId}/branches'
  )
})

test('consumer factory uses correct backend route for createBranch', () => {
  assert.ok(
    factorySrc.includes('/api/consumer/simulations/${simulationId}/branches'),
    'Expected createBranch to use /api/consumer/simulations/${simulationId}/branches'
  )
})

test('consumer factory uses correct backend route for listInterventions', () => {
  assert.ok(
    factorySrc.includes('/api/consumer/simulations/${simulationId}/interventions'),
    'Expected listInterventions to use /api/consumer/simulations/${simulationId}/interventions'
  )
})

test('consumer factory uses correct backend route for addIntervention', () => {
  assert.ok(
    factorySrc.includes('/api/consumer/simulations/${simulationId}/branches/${branchId}/interventions'),
    'Expected addIntervention to use /api/consumer/simulations/${simulationId}/branches/${branchId}/interventions'
  )
})

test('consumer factory uses correct backend route for getBranchComparison', () => {
  assert.ok(
    factorySrc.includes('/api/consumer/simulations/${simulationId}/branches/${branchId}/comparison'),
    'Expected getBranchComparison to use /api/consumer/simulations/${simulationId}/branches/${branchId}/comparison'
  )
})

test('consumer factory uses correct backend route for runBranch', () => {
  assert.ok(
    factorySrc.includes('/api/consumer/simulations/${simulationId}/branches/${branchId}/resume'),
    'Expected runBranch to use /api/consumer/simulations/${simulationId}/branches/${branchId}/resume'
  )
})

test('consumer factory uses correct backend route for getBranchStatus', () => {
  assert.ok(
    factorySrc.includes('/api/consumer/simulations/${simulationId}/branches/${branchId}/status'),
    'Expected getBranchStatus to use /api/consumer/simulations/${simulationId}/branches/${branchId}/status'
  )
})

test('consumer factory uses correct backend routes for comparison functions', () => {
  assert.ok(
    factorySrc.includes("service.post('/api/consumer/comparisons', data)"),
    'Expected compareResearchSnapshots to POST to /api/consumer/comparisons'
  )
  assert.ok(
    factorySrc.includes('/api/consumer/comparisons'),
    'Expected listComparisons to use /api/consumer/comparisons'
  )
  assert.ok(
    factorySrc.includes('/api/consumer/comparisons/${comparisonId}'),
    'Expected getComparison to use /api/consumer/comparisons/${comparisonId}'
  )
})

test('consumer factory uses correct backend routes for research asset functions', () => {
  assert.ok(
    factorySrc.includes('/api/consumer/research-assets/export'),
    'Expected exportResearchAsset to use /api/consumer/research-assets/export'
  )
  assert.ok(
    factorySrc.includes('/api/consumer/research-assets'),
    'Expected listResearchAssets to use /api/consumer/research-assets'
  )
  assert.ok(
    factorySrc.includes('/api/consumer/research-assets/${assetId}'),
    'Expected getResearchAsset to use /api/consumer/research-assets/${assetId}'
  )
  assert.ok(
    factorySrc.includes("service.post('/api/consumer/research-assets/export', data)"),
    'Expected exportResearchAsset to POST to /api/consumer/research-assets/export'
  )
})

test('consumer.js exports all required consumer functions', () => {
  const expectedExports = [
    'getConsumerSummary',
    'getChannelSummary',
    'getChannelEvents',
    'getPropagationPaths',
    'listRepresentativeAgents',
    'runConsumerInterview',
    'runFocusGroup',
    'listInterviewHistory',
    'listFocusGroupHistory',
    'listBranches',
    'createBranch',
    'getBranchComparison',
    'runBranch',
    'getBranchStatus',
    'listInterventions',
    'addIntervention',
    'exportResearchAsset',
    'listResearchAssets',
    'getResearchAsset',
    'compareResearchSnapshots',
    'listComparisons',
    'getComparison',
  ]
  for (const name of expectedExports) {
    assert.ok(
      consumerSrc.includes(name),
      `Expected consumer.js to export ${name}`
    )
  }
})

// ============== Backward compatibility: simulation.js re-exports ==============

import { readFileSync as readFile } from 'node:fs'
const simulationSrc = readFile(
  new URL('../src/api/simulation.js', import.meta.url),
  'utf-8'
)

test('simulation.js re-exports consumer functions from consumer.js', () => {
  assert.ok(
    simulationSrc.includes("from './consumer'"),
    'Expected simulation.js to re-export from consumer.js'
  )
  const reExported = ['getConsumerSummary', 'listBranches', 'createBranch',
    'listInterventions', 'addIntervention', 'getBranchComparison',
    'runBranch', 'getBranchStatus']
  for (const name of reExported) {
    assert.ok(
      simulationSrc.includes(name),
      `Expected simulation.js to re-export ${name} from consumer.js`
    )
  }
})

// ============== Backward compatibility: report.js re-exports ==============

const reportSrc = readFile(
  new URL('../src/api/report.js', import.meta.url),
  'utf-8'
)

test('report.js re-exports consumer functions from consumer.js', () => {
  assert.ok(
    reportSrc.includes("from './consumer'"),
    'Expected report.js to re-export from consumer.js'
  )
  const reExported = ['exportResearchAsset', 'listResearchAssets',
    'getResearchAsset', 'compareResearchSnapshots', 'listComparisons', 'getComparison']
  for (const name of reExported) {
    assert.ok(
      reportSrc.includes(name),
      `Expected report.js to re-export ${name} from consumer.js`
    )
  }
})

// ============== Component import tests ==============

const step3Src = readFile(
  new URL('../src/components/Step3Simulation.vue', import.meta.url),
  'utf-8'
)

test('Step3Simulation.vue imports consumer functions from consumer.js', () => {
  assert.ok(
    step3Src.includes("from '../api/consumer'"),
    'Expected Step3Simulation.vue to import from ../api/consumer'
  )
  const consumerImports = ['getConsumerSummary', 'listBranches', 'createBranch',
    'listInterventions', 'addIntervention', 'runBranch', 'getBranchStatus']
  // These should all come from the consumer import line
  const consumerImportBlock = step3Src.match(/from '\.\.\/api\/consumer'/g)
  assert.ok(consumerImportBlock, 'Expected consumer import statement in Step3Simulation.vue')
})

test('Step3Simulation.vue simulation import does not include consumer functions', () => {
  // Extract the import block that ends with from '../api/simulation'
  const simMarker = "from '../api/simulation'"
  const markerIdx = step3Src.indexOf(simMarker)
  const blockStart = step3Src.lastIndexOf('import {', markerIdx)
  const simImportBlock = step3Src.substring(blockStart, markerIdx + simMarker.length)
  const consumerOnlyFunctions = ['getConsumerSummary', 'listBranches', 'createBranch',
    'listInterventions', 'addIntervention', 'getBranchComparison', 'runBranch', 'getBranchStatus']
  for (const fn of consumerOnlyFunctions) {
    assert.ok(
      !simImportBlock.includes(fn),
      `${fn} should not be in simulation import block (should be in consumer import)`
    )
  }
})

const step4Src = readFile(
  new URL('../src/components/Step4Report.vue', import.meta.url),
  'utf-8'
)

test('Step4Report.vue imports consumer functions from consumer.js', () => {
  assert.ok(
    step4Src.includes("from '../api/consumer'"),
    'Expected Step4Report.vue to import from ../api/consumer'
  )
})

test('Step4Report.vue does not import consumer functions from report.js', () => {
  // Find the import block that ends with from '../api/report'
  const reportMarker = "from '../api/report'"
  const markerIdx = step4Src.indexOf(reportMarker)
  const blockStart = step4Src.lastIndexOf('import {', markerIdx)
  const reportImportBlock = step4Src.substring(blockStart, markerIdx + reportMarker.length)
  assert.ok(
    !reportImportBlock.includes('exportResearchAsset'),
    'exportResearchAsset should not be in report import block'
  )
  assert.ok(
    !reportImportBlock.includes('compareResearchSnapshots'),
    'compareResearchSnapshots should not be in report import block'
  )
  assert.ok(
    !reportImportBlock.includes('getComparison'),
    'getComparison should not be in report import block'
  )
})

test('Step4Report.vue does not import getBranchComparison from simulation.js', () => {
  assert.ok(
    !step4Src.includes("import { getBranchComparison } from '../api/simulation'"),
    'getBranchComparison should not be imported from simulation.js in Step4Report.vue'
  )
})

const step5Src = readFile(
  new URL('../src/components/Step5Interaction.vue', import.meta.url),
  'utf-8'
)

test('Step5Interaction.vue does not import from consumer.js', () => {
  assert.ok(
    !step5Src.includes("from '../api/consumer'"),
    'Step5Interaction.vue should not import from ../api/consumer'
  )
})

test('Step5Interaction.vue does not import consumer functions from report.js or simulation.js', () => {
  // getComparison should come from consumer, not report
  const reportImportLine = step5Src.split('\n').find(l => l.includes("from '../api/report'"))
  assert.ok(
    !reportImportLine.includes('getComparison'),
    'getComparison should not be in report import block of Step5Interaction.vue'
  )
  // getBranchComparison should come from consumer, not simulation
  const simImportLine = step5Src.split('\n').find(l => l.includes("from '../api/simulation'"))
  assert.ok(
    !simImportLine.includes('getBranchComparison'),
    'getBranchComparison should not be in simulation import block of Step5Interaction.vue'
  )
})

// ============== No legacy paths remain ==============

test('consumer.js contains zero /api/simulation/ or /api/report/ paths', () => {
  const legacyPaths = consumerSrc.match(/\/api\/simulation\//g) || []
  const legacyReportPaths = consumerSrc.match(/\/api\/report\//g) || []
  assert.equal(legacyPaths.length, 0, `Found legacy /api/simulation/ paths in consumer.js: ${legacyPaths.join(', ')}`)
  assert.equal(legacyReportPaths.length, 0, `Found legacy /api/report/ paths in consumer.js: ${legacyReportPaths.join(', ')}`)
})
