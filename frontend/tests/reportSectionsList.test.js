import { test } from 'vitest'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

const step4Path = join(__dirname, '../src/components/Step4Report.vue')
const step5Path = join(__dirname, '../src/components/Step5Interaction.vue')
const reportShellPath = join(__dirname, '../src/components/report/InteractionReportShell.vue')
const sectionsPath = join(__dirname, '../src/components/report/ReportSectionsList.vue')

const step4Content = readFileSync(step4Path, 'utf-8')
const step5Content = readFileSync(step5Path, 'utf-8')
const reportShellContent = readFileSync(reportShellPath, 'utf-8')
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

test('Step5Interaction reuses ReportSectionsList for report sections', () => {
  assert.ok(step5Content.includes("import InteractionReportShell from './report/InteractionReportShell.vue'"), 'Step5 must import InteractionReportShell')
  assert.ok(step5Content.includes('<InteractionReportShell'), 'Step5 must render InteractionReportShell')
  assert.ok(reportShellContent.includes("import ReportSectionsList from './ReportSectionsList.vue'"), 'InteractionReportShell must import ReportSectionsList')
  assert.ok(reportShellContent.includes('<ReportSectionsList'), 'InteractionReportShell must render ReportSectionsList')
  assert.ok(!step5Content.includes('class="sections-list"'), 'section list markup should live outside Step5Interaction')
  assert.ok(!step5Content.includes('renderMarkdown(generatedSections[idx + 1])'), 'section markdown rendering should live outside Step5Interaction')
  assert.ok(step5Content.includes('@toggle-section-collapse="toggleSectionCollapse"'), 'Step5 must keep collapse state handling')
})
