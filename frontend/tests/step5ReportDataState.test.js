import { test } from 'vitest'
import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

const step5Path = join(__dirname, '../src/components/Step5Interaction.vue')
const composablePath = join(__dirname, '../src/composables/useStep5ReportDataState.ts')

test('useStep5ReportDataState manages report sections, logs, and profiles', async () => {
  assert.ok(existsSync(composablePath), 'useStep5ReportDataState composable must exist')

  const { useStep5ReportDataState } = await import('../src/composables/useStep5ReportDataState.ts')
  const state = useStep5ReportDataState()

  assert.equal(state.reportOutline.value, null)
  assert.deepEqual(state.generatedSections.value, {})
  assert.equal(state.collapsedSections.value.size, 0)
  assert.equal(state.currentSectionIndex.value, null)
  assert.deepEqual(state.profiles.value, [])

  state.toggleSectionCollapse(0)
  assert.equal(state.collapsedSections.value.has(0), false)

  state.generatedSections.value[1] = 'First section'
  state.toggleSectionCollapse(0)
  assert.equal(state.collapsedSections.value.has(0), true)

  state.toggleSectionCollapse(0)
  assert.equal(state.collapsedSections.value.has(0), false)

  state.applyReportLogs([
    { action: 'planning_complete', details: { outline: [{ title: 'Intro' }] } },
    { action: 'section_complete', section_index: 1, details: { content: 'Updated first section' } },
    { action: 'section_complete', section_index: 2, details: { content: 'Second section' } },
    { action: 'section_complete', section_index: 100, details: { content: 'Ignored appendix' } },
    { action: 'section_complete', section_index: 3, details: {} },
    { action: 'other_action', details: { outline: [{ title: 'Ignored' }] } },
  ])

  assert.deepEqual(state.reportOutline.value, [{ title: 'Intro' }])
  assert.equal(state.generatedSections.value[1], 'Updated first section')
  assert.equal(state.generatedSections.value[2], 'Second section')
  assert.equal(state.generatedSections.value[100], undefined)
  assert.equal(state.generatedSections.value[3], undefined)

  state.setProfiles([{ username: 'Ava' }, { username: 'Bo' }])
  assert.deepEqual(state.profiles.value, [{ username: 'Ava' }, { username: 'Bo' }])

  state.setProfiles(null)
  assert.deepEqual(state.profiles.value, [])
})

test('Step5Interaction delegates report data state to useStep5ReportDataState', () => {
  const step5Content = readFileSync(step5Path, 'utf-8')
  assert.ok(step5Content.includes("import { useStep5ReportDataState } from '../composables/useStep5ReportDataState'"), 'Step5 must import useStep5ReportDataState')
  assert.ok(step5Content.includes('useStep5ReportDataState()'), 'Step5 must initialize report data state via composable')
  assert.ok(step5Content.includes('applyReportLogs(logs)'), 'Step5 must delegate agent log application')
  assert.ok(step5Content.includes('setProfiles(res.data.profiles || [])'), 'Step5 must delegate profile updates')

  for (const token of [
    'const reportOutline = ref(null)',
    'const generatedSections = ref({})',
    'const collapsedSections = ref(new Set())',
    'const currentSectionIndex = ref(null)',
    'const profiles = ref([])',
    'const toggleSectionCollapse = (idx)',
    "if (log.action === 'planning_complete' && log.details?.outline)",
    "if (log.action === 'section_complete' && log.section_index < 100 && log.details?.content)",
    'profiles.value = res.data.profiles || []',
  ]) {
    assert.ok(!step5Content.includes(token), `Step5 should not inline report data token: ${token}`)
  }
})
