import { test } from 'vitest'
import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

const step5Path = join(__dirname, '../src/components/Step5Interaction.vue')
const reportShellPath = join(__dirname, '../src/components/report/InteractionReportShell.vue')

const step5Content = readFileSync(step5Path, 'utf-8')

test('Step5Interaction delegates left report shell rendering', () => {
  assert.ok(existsSync(reportShellPath), 'InteractionReportShell component must exist')
  assert.ok(step5Content.includes("import InteractionReportShell from './report/InteractionReportShell.vue'"), 'Step5 must import InteractionReportShell')
  assert.ok(step5Content.includes('<InteractionReportShell'), 'Step5 must render InteractionReportShell')
  assert.ok(step5Content.includes('ref="leftPanel"'), 'Step5 must keep left panel ref')
  assert.ok(step5Content.includes(':report-outline="reportOutline"'), 'Step5 must pass report outline')
  assert.ok(step5Content.includes(':generated-sections="generatedSections"'), 'Step5 must pass generated sections')
  assert.ok(step5Content.includes(':collapsed-sections="collapsedSections"'), 'Step5 must pass collapsed sections')
  assert.ok(step5Content.includes(':current-section-index="currentSectionIndex"'), 'Step5 must pass current section index')
  assert.ok(step5Content.includes(':interview-handoff-context="interviewHandoffContext"'), 'Step5 must pass handoff context')
  assert.ok(step5Content.includes('@toggle-section-collapse="toggleSectionCollapse"'), 'Step5 must keep section collapse handling')
  assert.ok(step5Content.includes('@clear-interview-handoff="clearInterviewHandoff"'), 'Step5 must keep handoff clear handling')
  assert.ok(!step5Content.includes('class="report-header-block"'), 'report header markup should live outside Step5Interaction')
  assert.ok(!step5Content.includes('class="waiting-placeholder"'), 'waiting markup should live outside Step5Interaction')
})

test('InteractionReportShell owns report header, sections, handoff, and waiting rendering', () => {
  const reportShellContent = readFileSync(reportShellPath, 'utf-8')
  for (const token of [
    'class="left-panel report-style"',
    'class="report-content-wrapper"',
    'class="report-header-block"',
    'class="waiting-placeholder"',
    '<ReportSectionsList',
    '<InteractionHandoffPanel',
    "emit('toggle-section-collapse', idx)",
    "emit('clear-interview-handoff')",
    "t('step5.loadingInteraction')",
    "t('consumer.reportTag')",
  ]) {
    assert.ok(reportShellContent.includes(token), `missing report shell token: ${token}`)
  }
})
