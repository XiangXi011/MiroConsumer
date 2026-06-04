import { test } from 'vitest'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

const step4Path = join(__dirname, '../src/components/Step4Report.vue')
const sectionsPath = join(__dirname, '../src/components/report/ReportSectionsList.vue')

const step4Content = readFileSync(step4Path, 'utf-8')
const sectionsContent = readFileSync(sectionsPath, 'utf-8')

test('Step4Report delegates report section rendering to ReportSectionsList', () => {
  assert.ok(step4Content.includes("import ReportSectionsList from './report/ReportSectionsList.vue'"), 'Step4 must import ReportSectionsList')
  assert.ok(step4Content.includes('<ReportSectionsList'), 'Step4 must render ReportSectionsList')
  assert.ok(!step4Content.includes('class="sections-list"'), 'section list markup should live outside Step4Report')
  assert.ok(step4Content.includes('@toggle-section-collapse="toggleSectionCollapse"'), 'Step4 must keep collapse state handling')
  assert.ok(step4Content.includes('@run-action="handleRunAction"'), 'Step4 must keep research action handling')
})

test('ReportSectionsList owns section list rendering contract', () => {
  for (const token of [
    'class="sections-list"',
    'v-for="(section, idx) in sections"',
    'renderMarkdown(generatedSections[idx + 1])',
    'ConsumerResearchActionBar',
    'currentSectionIndex === idx + 1',
    "t('step4.generatingSection'",
    "emit('toggle-section-collapse', idx)",
  ]) {
    assert.ok(sectionsContent.includes(token), `missing report sections token: ${token}`)
  }
})
