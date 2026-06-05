import { test } from 'vitest'
import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { reactive } from 'vue'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

const step5Path = join(__dirname, '../src/components/Step5Interaction.vue')
const composablePath = join(__dirname, '../src/composables/useStep5ConsumerContextState.ts')

const t = (key, params = {}) => {
  const templates = {
    'consumer.quickPrompts.resonance': `Why did "${params.point}" become a top resonance point?`,
    'consumer.quickPrompts.risk': `Why did "${params.point}" get amplified during propagation?`,
    'consumer.quickPrompts.misread': `How did "${params.point}" turn into a misread?`,
    'consumer.quickPrompts.branchFork': `How does the branch "${params.branchName}" differ from the base run?`,
    'consumer.quickPrompts.comparisonBranchVsBase': `How does the branch "${params.right}" differ from the base run "${params.left}"?`,
    'consumer.quickPrompts.replayAligned': 'Replay aligns with benchmark. What stable signals hold up best?',
  }
  return templates[key] || key
}

function createProps(reportContext = {}, overrides = {}) {
  return reactive({
    reportData: {
      project_type: 'consumer_test',
      report_context: reportContext,
    },
    projectData: null,
    comparisonSnapshot: null,
    ...overrides,
  })
}

test('useStep5ConsumerContextState derives consumer context and prompts', async () => {
  assert.ok(existsSync(composablePath), 'useStep5ConsumerContextState composable must exist')

  const { useStep5ConsumerContextState } = await import('../src/composables/useStep5ConsumerContextState.ts')
  const props = createProps({
    top_resonance_points: ['fresh taste'],
    top_risk_points: ['too expensive'],
    top_misreads: ['serving size'],
    representative_voc_quotes: {
      resonance: [{ quote: 'It feels modern', engagement: 12, agent_id: 'a1' }],
    },
    source_catalog: [{ title: 'Taste report' }],
    enriched_findings: [
      { summary: 'Trust improved', source_title: 'Diary' },
      { summary: '', source_title: 'Ignored' },
    ],
    replay_alignment: {
      status: 'aligned',
    },
  })

  const state = useStep5ConsumerContextState({ props, t })
  assert.equal(state.isConsumerMode.value, true)
  assert.equal(state.reportContext.value.top_resonance_points[0], 'fresh taste')
  assert.equal(state.consumerVocHighlights.value[0].quote, 'It feels modern')
  assert.deepEqual(state.consumerSourceCatalog.value, [{ title: 'Taste report' }])
  assert.deepEqual(state.consumerEnrichedFindings.value, [
    { summary: 'Trust improved', source_title: 'Diary' },
  ])

  state.workspaceBranchComparison.value = {
    branch_name: 'Safer claim',
    fork_round: 2,
    interventions: [{ intervention_type: 'clarification' }],
  }
  props.comparisonSnapshot = {
    mode: 'branch_vs_base',
    left: { label: 'Base' },
    right: { label: 'Safer' },
    acceptance_delta_pp: 12,
  }

  const prompts = state.consumerQuickPrompts.value.join('\n')
  assert.match(prompts, /fresh taste/)
  assert.match(prompts, /Safer claim/)
  assert.match(prompts, /Safer/)
  assert.match(prompts, /Replay aligns/)
  assert.deepEqual(state.effectiveComparisonSnapshot.value, props.comparisonSnapshot)
})

test('useStep5ConsumerContextState gates consumer-only derived data and falls back to research findings', async () => {
  const { useStep5ConsumerContextState } = await import('../src/composables/useStep5ConsumerContextState.ts')
  const props = createProps({
    enriched_findings: [],
    research_findings: [
      { summary: 'Fallback finding' },
      { summary: '' },
    ],
  }, {
    reportData: { project_type: 'standard', report_context: { research_findings: [{ summary: 'Hidden' }] } },
    projectData: { projectType: 'standard' },
  })

  const state = useStep5ConsumerContextState({ props, t })
  assert.equal(state.isConsumerMode.value, false)
  assert.deepEqual(state.consumerQuickPrompts.value, [])
  assert.deepEqual(state.consumerVocHighlights.value, [])
  assert.deepEqual(state.consumerSourceCatalog.value, [])
  assert.deepEqual(state.consumerEnrichedFindings.value, [])

  props.reportData.project_type = 'consumer_test'
  assert.deepEqual(state.consumerEnrichedFindings.value, [{ summary: 'Hidden' }])
})

test('Step5Interaction delegates consumer context state to useStep5ConsumerContextState', () => {
  const step5Content = readFileSync(step5Path, 'utf-8')
  assert.ok(step5Content.includes("import { useStep5ConsumerContextState } from '../composables/useStep5ConsumerContextState'"), 'Step5 must import useStep5ConsumerContextState')
  assert.ok(step5Content.includes('useStep5ConsumerContextState({'), 'Step5 must initialize consumer context state via composable')

  for (const token of [
    'const isConsumerMode = computed(()',
    'const reportContext = computed(()',
    'const workspaceBranchComparison = ref(null)',
    'const workspaceComparisonSnapshot = ref(null)',
    'const effectiveComparisonSnapshot = computed(()',
    'const consumerQuickPrompts = computed(()',
    'const consumerVocHighlights = computed(()',
    'const consumerSourceCatalog = computed(()',
    'const consumerEnrichedFindings = computed(()',
  ]) {
    assert.ok(!step5Content.includes(token), `Step5 should not inline consumer context token: ${token}`)
  }
})
