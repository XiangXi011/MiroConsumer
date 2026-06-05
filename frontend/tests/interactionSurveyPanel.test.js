import { test } from 'vitest'
import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

const step5Path = join(__dirname, '../src/components/Step5Interaction.vue')
const workspaceShellPath = join(__dirname, '../src/components/report/InteractionWorkspaceShell.vue')
const surveyPanelPath = join(__dirname, '../src/components/report/InteractionSurveyPanel.vue')

const step5Content = readFileSync(step5Path, 'utf-8')
const workspaceShellContent = readFileSync(workspaceShellPath, 'utf-8')

test('Step5Interaction delegates survey setup and results rendering', () => {
  assert.ok(existsSync(surveyPanelPath), 'InteractionSurveyPanel component must exist')
  assert.ok(step5Content.includes("import InteractionWorkspaceShell from './report/InteractionWorkspaceShell.vue'"), 'Step5 must import InteractionWorkspaceShell')
  assert.ok(step5Content.includes('<InteractionWorkspaceShell'), 'Step5 must render InteractionWorkspaceShell')
  assert.ok(workspaceShellContent.includes("import InteractionSurveyPanel from './InteractionSurveyPanel.vue'"), 'InteractionWorkspaceShell must import InteractionSurveyPanel')
  assert.ok(workspaceShellContent.includes('<InteractionSurveyPanel'), 'InteractionWorkspaceShell must render InteractionSurveyPanel')
  assert.ok(step5Content.includes(':profiles="profiles"'), 'Step5 must pass profiles')
  assert.ok(step5Content.includes(':selected-agents="selectedAgents"'), 'Step5 must pass selected agents')
  assert.ok(step5Content.includes('v-model:survey-question="surveyQuestion"'), 'Step5 must bind survey question')
  assert.ok(step5Content.includes(':survey-results="surveyResults"'), 'Step5 must pass survey results')
  assert.ok(step5Content.includes(':is-surveying="isSurveying"'), 'Step5 must pass surveying state')
  assert.ok(step5Content.includes('@toggle-agent-selection="toggleAgentSelection"'), 'Step5 must keep agent selection handling')
  assert.ok(step5Content.includes('@select-all-agents="selectAllAgents"'), 'Step5 must keep select all handling')
  assert.ok(step5Content.includes('@clear-agent-selection="clearAgentSelection"'), 'Step5 must keep clear handling')
  assert.ok(step5Content.includes('@submit-survey="submitSurvey"'), 'Step5 must keep survey submission handling')
  assert.ok(!step5Content.includes('class="survey-setup"'), 'survey setup markup should live outside Step5Interaction')
  assert.ok(!step5Content.includes('class="survey-results"'), 'survey results markup should live outside Step5Interaction')
})

test('InteractionSurveyPanel owns survey target, question, and result rendering', () => {
  const surveyPanelContent = readFileSync(surveyPanelPath, 'utf-8')
  for (const token of [
    'class="survey-setup"',
    'class="survey-results"',
    'v-for="(profile, idx) in profiles"',
    "emit('toggle-agent-selection', idx)",
    "emit('select-all-agents')",
    "emit('clear-agent-selection')",
    "emit('update:survey-question'",
    "emit('submit-survey')",
    'v-for="(result, idx) in surveyResults"',
    'renderMarkdown(result.answer)',
    "t('step5.selectSurveyTarget')",
    "t('step5.surveyInputPlaceholder')",
  ]) {
    assert.ok(surveyPanelContent.includes(token), `missing survey panel token: ${token}`)
  }
})
