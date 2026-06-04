import { test } from 'vitest'
import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

const step5Path = join(__dirname, '../src/components/Step5Interaction.vue')
const reportShellPath = join(__dirname, '../src/components/report/InteractionReportShell.vue')
const handoffPanelPath = join(__dirname, '../src/components/report/InteractionHandoffPanel.vue')

const step5Content = readFileSync(step5Path, 'utf-8')
const reportShellContent = readFileSync(reportShellPath, 'utf-8')

test('Step5Interaction delegates interview handoff rendering', () => {
  assert.ok(existsSync(handoffPanelPath), 'InteractionHandoffPanel component must exist')
  assert.ok(step5Content.includes("import InteractionReportShell from './report/InteractionReportShell.vue'"), 'Step5 must import InteractionReportShell')
  assert.ok(step5Content.includes('<InteractionReportShell'), 'Step5 must render InteractionReportShell')
  assert.ok(step5Content.includes(':interview-handoff-context="interviewHandoffContext"'), 'Step5 must pass the handoff context')
  assert.ok(step5Content.includes('@clear-interview-handoff="clearInterviewHandoff"'), 'Step5 must keep clear handling')
  assert.ok(reportShellContent.includes("import InteractionHandoffPanel from './InteractionHandoffPanel.vue'"), 'InteractionReportShell must import InteractionHandoffPanel')
  assert.ok(reportShellContent.includes('<InteractionHandoffPanel'), 'InteractionReportShell must render InteractionHandoffPanel')
  assert.ok(reportShellContent.includes('v-if="showTechnical && interviewHandoffContext"'), 'InteractionReportShell must keep the handoff visibility guard')
  assert.ok(reportShellContent.includes(':handoff-context="interviewHandoffContext"'), 'InteractionReportShell must pass the handoff context')
  assert.ok(reportShellContent.includes("@clear-handoff=\"emit('clear-interview-handoff')\""), 'InteractionReportShell must forward clear handling')
  assert.ok(!step5Content.includes('class="handoff-panel"'), 'handoff panel markup should live outside Step5Interaction')
  assert.ok(!step5Content.includes('class="handoff-panel-body"'), 'handoff rows should live outside Step5Interaction')
})

test('InteractionHandoffPanel owns handoff context rows and clear action', () => {
  const handoffPanelContent = readFileSync(handoffPanelPath, 'utf-8')
  for (const token of [
    'class="handoff-panel"',
    'class="handoff-panel-header"',
    'class="handoff-panel-body"',
    "t('step5.technicalInterviewContext')",
    "emit('clear-handoff')",
    'handoffContext.report_id',
    'handoffContext.section_index',
    'handoffContext.finding_id',
    'handoffContext.claim',
    'handoffContext.branch_id',
  ]) {
    assert.ok(handoffPanelContent.includes(token), `missing handoff panel token: ${token}`)
  }
})
