import { test } from 'vitest'
import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

const step5Path = join(__dirname, '../src/components/Step5Interaction.vue')
const actionBarPath = join(__dirname, '../src/components/report/InteractionActionBar.vue')

const step5Content = readFileSync(step5Path, 'utf-8')

test('Step5Interaction delegates interaction action bar rendering', () => {
  assert.ok(existsSync(actionBarPath), 'InteractionActionBar component must exist')
  assert.ok(step5Content.includes("import InteractionActionBar from './report/InteractionActionBar.vue'"), 'Step5 must import InteractionActionBar')
  assert.ok(step5Content.includes('<InteractionActionBar'), 'Step5 must render InteractionActionBar')
  assert.ok(step5Content.includes(':active-tab="activeTab"'), 'Step5 must pass active tab state')
  assert.ok(step5Content.includes(':chat-target="chatTarget"'), 'Step5 must pass chat target state')
  assert.ok(step5Content.includes(':profiles="profiles"'), 'Step5 must pass profiles')
  assert.ok(step5Content.includes('@select-report-agent-chat="selectReportAgentChat"'), 'Step5 must keep report-agent selection handling')
  assert.ok(step5Content.includes('@toggle-agent-dropdown="toggleAgentDropdown"'), 'Step5 must keep dropdown toggle handling')
  assert.ok(step5Content.includes('@select-agent="selectAgent"'), 'Step5 must keep agent selection handling')
  assert.ok(step5Content.includes('@select-survey-tab="selectSurveyTab"'), 'Step5 must keep survey tab handling')
  assert.ok(!step5Content.includes('class="action-bar"'), 'action bar markup should live outside Step5Interaction')
})

test('InteractionActionBar owns action bar tabs and agent dropdown rendering', () => {
  const actionBarContent = readFileSync(actionBarPath, 'utf-8')
  for (const token of [
    'class="action-bar"',
    'class="action-bar-tabs"',
    'class="agent-dropdown"',
    'showAgentDropdown',
    'selectedAgent',
    'profiles.length',
    "emit('select-report-agent-chat')",
    "emit('toggle-agent-dropdown')",
    "emit('select-agent', agent, idx)",
    "emit('select-survey-tab')",
    "t('step5.businessTitle')",
    "t('step5.chatWithReportAgent')",
    "t('step5.chatWithAgent')",
    "t('step5.sendSurvey')",
  ]) {
    assert.ok(actionBarContent.includes(token), `missing action bar token: ${token}`)
  }
})
