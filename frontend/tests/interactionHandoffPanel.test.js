import { test } from 'vitest'
import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

const step5Path = join(__dirname, '../src/components/Step5Interaction.vue')
const handoffPanelPath = join(__dirname, '../src/components/report/InteractionHandoffPanel.vue')

const step5Content = readFileSync(step5Path, 'utf-8')

test('Step5Interaction delegates interview handoff rendering', () => {
  assert.ok(existsSync(handoffPanelPath), 'InteractionHandoffPanel component must exist')
  assert.ok(step5Content.includes("import InteractionHandoffPanel from './report/InteractionHandoffPanel.vue'"), 'Step5 must import InteractionHandoffPanel')
  assert.ok(step5Content.includes('<InteractionHandoffPanel'), 'Step5 must render InteractionHandoffPanel')
  assert.ok(step5Content.includes('v-if="showTechnical && interviewHandoffContext"'), 'Step5 must keep the handoff visibility guard')
  assert.ok(step5Content.includes(':handoff-context="interviewHandoffContext"'), 'Step5 must pass the handoff context')
  assert.ok(step5Content.includes('@clear-handoff="clearInterviewHandoff"'), 'Step5 must keep clear handling')
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
