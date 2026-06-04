import { test } from 'vitest'
import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

const step5Path = join(__dirname, '../src/components/Step5Interaction.vue')
const cardPath = join(__dirname, '../src/components/report/ReportAgentToolsCard.vue')

const step5Content = readFileSync(step5Path, 'utf-8')

test('Step5Interaction delegates report agent tools card rendering', () => {
  assert.ok(existsSync(cardPath), 'ReportAgentToolsCard component must exist')
  assert.ok(step5Content.includes("import ReportAgentToolsCard from './report/ReportAgentToolsCard.vue'"), 'Step5 must import ReportAgentToolsCard')
  assert.ok(step5Content.includes('<ReportAgentToolsCard'), 'Step5 must render ReportAgentToolsCard')
  assert.ok(!step5Content.includes('class="report-agent-tools-card"'), 'tools card markup should live outside Step5Interaction')
  assert.ok(!step5Content.includes('showToolsDetail'), 'tools detail state should live inside ReportAgentToolsCard')
})

test('ReportAgentToolsCard owns report agent tools rendering contract', () => {
  const cardContent = readFileSync(cardPath, 'utf-8')
  for (const token of [
    'class="report-agent-tools-card"',
    'showToolsDetail',
    'class="tools-grid"',
    "t('step5.reportAgentChat')",
    "t('step5.toolInsightForge')",
    "t('step5.toolPanoramaSearch')",
    "t('step5.toolQuickSearch')",
    "t('step5.toolInterviewSubAgent')",
  ]) {
    assert.ok(cardContent.includes(token), `missing tools card token: ${token}`)
  }
})
