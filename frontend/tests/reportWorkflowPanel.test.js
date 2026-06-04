import { test } from 'vitest'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

const step4Path = join(__dirname, '../src/components/Step4Report.vue')
const panelPath = join(__dirname, '../src/components/report/ReportWorkflowPanel.vue')

const step4Content = readFileSync(step4Path, 'utf-8')
const panelContent = readFileSync(panelPath, 'utf-8')

test('Step4Report delegates technical workflow timeline to ReportWorkflowPanel', () => {
  assert.ok(step4Content.includes("import ReportWorkflowPanel from './report/ReportWorkflowPanel.vue'"), 'Step4 must import ReportWorkflowPanel')
  assert.ok(step4Content.includes('<ReportWorkflowPanel'), 'Step4 must render ReportWorkflowPanel')
  assert.ok(step4Content.includes('ref="rightPanel"'), 'Step4 must keep the rightPanel scroll ref on the extracted component')
  assert.ok(!step4Content.includes('class="workflow-timeline"'), 'workflow timeline markup should live outside Step4Report')
})

test('ReportWorkflowPanel owns workflow overview and timeline rendering contract', () => {
  for (const token of [
    'class="workflow-overview"',
    'class="workflow-timeline"',
    'TransitionGroup',
    'getActionLabel(log.action)',
    'getToolDisplayName(log.details?.tool_name)',
    'showRawResult[log.timestamp]',
    'Structured View',
    'Raw Output',
    'Report Generation Complete',
    'Waiting for agent activity...',
  ]) {
    assert.ok(panelContent.includes(token), `missing workflow panel token: ${token}`)
  }
})
