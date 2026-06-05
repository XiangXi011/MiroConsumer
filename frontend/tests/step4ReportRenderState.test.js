import { test } from 'vitest'
import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

const step4Path = join(__dirname, '../src/components/Step4Report.vue')
const composablePath = join(__dirname, '../src/composables/useStep4ReportRenderState.ts')

const completedReportData = {
  status: 'completed',
  markdown_content: [
    '# Launch Report',
    'Executive summary',
    '',
    '## Path diagnosis',
    'Social post',
    '',
    '## Evidence',
    'Pinned comments',
  ].join('\n'),
}

test('useStep4ReportRenderState applies completed reportData render state', async () => {
  assert.ok(existsSync(composablePath), 'useStep4ReportRenderState composable must exist')

  const { useStep4ReportRenderState } = await import('../src/composables/useStep4ReportRenderState.ts')
  const state = useStep4ReportRenderState()

  state.applyReportRenderState(completedReportData)

  assert.equal(state.isComplete.value, true)
  assert.equal(state.reportOutline.value.title, 'Launch Report')
  assert.deepEqual(state.reportOutline.value.sections.map(section => section.title), ['Path diagnosis', 'Evidence'])
  assert.match(state.generatedSections.value[1], /Social post/)
  assert.match(state.generatedSections.value[2], /Pinned comments/)
})

test('useStep4ReportRenderState ignores incomplete reportData and resets state', async () => {
  const { useStep4ReportRenderState } = await import('../src/composables/useStep4ReportRenderState.ts')
  const state = useStep4ReportRenderState()

  state.applyReportRenderState(completedReportData)
  state.applyReportRenderState({ status: 'running', markdown_content: '# Draft' })

  assert.equal(state.isComplete.value, true)
  assert.equal(state.reportOutline.value.title, 'Launch Report')

  state.resetReportRenderState()
  assert.equal(state.reportOutline.value, null)
  assert.equal(state.currentSectionIndex.value, null)
  assert.deepEqual(state.generatedSections.value, {})
  assert.equal(state.expandedContent.value.size, 0)
  assert.equal(state.collapsedSections.value.size, 0)
  assert.equal(state.isComplete.value, false)
  assert.equal(state.startTime.value, null)
})

test('useStep4ReportRenderState toggles only generated sections', async () => {
  const { useStep4ReportRenderState } = await import('../src/composables/useStep4ReportRenderState.ts')
  const state = useStep4ReportRenderState()

  state.toggleSectionContent(0)
  state.toggleSectionCollapse(0)
  assert.equal(state.expandedContent.value.has(0), false)
  assert.equal(state.collapsedSections.value.has(0), false)

  state.generatedSections.value[1] = 'done'
  state.toggleSectionContent(0)
  state.toggleSectionCollapse(0)
  assert.equal(state.expandedContent.value.has(0), true)
  assert.equal(state.collapsedSections.value.has(0), true)

  state.toggleSectionContent(0)
  state.toggleSectionCollapse(0)
  assert.equal(state.expandedContent.value.has(0), false)
  assert.equal(state.collapsedSections.value.has(0), false)
})

test('useStep4ReportRenderState applies agent log patches and emits completion', async () => {
  const { useStep4ReportRenderState } = await import('../src/composables/useStep4ReportRenderState.ts')
  const statuses = []
  let stopped = false
  const state = useStep4ReportRenderState({
    emitUpdateStatus: status => statuses.push(status),
    stopPolling: () => {
      stopped = true
    },
  })

  const startedAt = new Date('2026-01-01T00:00:00Z')
  state.applyAgentLogStatePatch({
    reportOutline: { sections: [{ title: 'Evidence' }] },
    currentSectionIndex: null,
    generatedSection: { index: 2, content: 'Generated section' },
    expandedContentIndex: 1,
    isComplete: true,
    startTime: startedAt,
    statusUpdate: 'completed',
    shouldStopPolling: true,
  })

  assert.deepEqual(state.reportOutline.value, { sections: [{ title: 'Evidence' }] })
  assert.equal(state.currentSectionIndex.value, null)
  assert.equal(state.generatedSections.value[2], 'Generated section')
  assert.equal(state.expandedContent.value.has(1), true)
  assert.equal(state.isComplete.value, true)
  assert.equal(state.startTime.value, startedAt)
  assert.deepEqual(statuses, ['completed'])
  assert.equal(stopped, true)
})

test('Step4Report delegates report render state to useStep4ReportRenderState', () => {
  const step4Content = readFileSync(step4Path, 'utf-8')
  assert.ok(step4Content.includes("import { useStep4ReportRenderState } from '../composables/useStep4ReportRenderState'"), 'Step4 must import useStep4ReportRenderState')
  assert.ok(step4Content.includes('useStep4ReportRenderState({'), 'Step4 must initialize report render state via composable')

  for (const token of [
    'const reportOutline = ref(null)',
    'const currentSectionIndex = ref(null)',
    'const generatedSections = ref({})',
    'const expandedContent = ref(new Set())',
    'const collapsedSections = ref(new Set())',
    'const isComplete = ref(false)',
    'const startTime = ref(null)',
    'const applyReportRenderState = ()',
    'const toggleSectionContent = (idx)',
    'const toggleSectionCollapse = (idx)',
    'const applyAgentLogStatePatch = (patch)',
  ]) {
    assert.ok(!step4Content.includes(token), `Step4 should not inline report render token: ${token}`)
  }
})
