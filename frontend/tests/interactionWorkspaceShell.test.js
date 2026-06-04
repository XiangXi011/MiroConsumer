import { test } from 'vitest'
import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

const step5Path = join(__dirname, '../src/components/Step5Interaction.vue')
const workspaceShellPath = join(__dirname, '../src/components/report/InteractionWorkspaceShell.vue')

const step5Content = readFileSync(step5Path, 'utf-8')

test('Step5Interaction delegates right interaction workspace rendering', () => {
  assert.ok(existsSync(workspaceShellPath), 'InteractionWorkspaceShell component must exist')
  assert.ok(step5Content.includes("import InteractionWorkspaceShell from './report/InteractionWorkspaceShell.vue'"), 'Step5 must import InteractionWorkspaceShell')
  assert.ok(step5Content.includes('<InteractionWorkspaceShell'), 'Step5 must render InteractionWorkspaceShell')
  assert.ok(step5Content.includes('ref="chatPanelRef"'), 'Step5 must keep chat panel ref through the shell')
  assert.ok(step5Content.includes(':active-tab="activeTab"'), 'Step5 must pass active tab')
  assert.ok(step5Content.includes(':chat-target="chatTarget"'), 'Step5 must pass chat target')
  assert.ok(step5Content.includes('v-model:chat-input="chatInput"'), 'Step5 must bind chat input')
  assert.ok(step5Content.includes('v-model:survey-question="surveyQuestion"'), 'Step5 must bind survey question')
  assert.ok(step5Content.includes('@send-message="sendMessage"'), 'Step5 must keep send handling')
  assert.ok(step5Content.includes('@submit-survey="submitSurvey"'), 'Step5 must keep survey handling')
  assert.ok(!step5Content.includes('class="right-panel"'), 'right panel markup should live outside Step5Interaction')
  assert.ok(!step5Content.includes('class="chat-container"'), 'chat container markup should live outside Step5Interaction')
  assert.ok(!step5Content.includes('class="consumer-interview-workspace"'), 'consumer interview workspace should live outside Step5Interaction')
})

test('InteractionWorkspaceShell owns action bar, chat, interview, and survey rendering', () => {
  const shellContent = readFileSync(workspaceShellPath, 'utf-8')
  for (const token of [
    'class="right-panel"',
    'class="chat-container"',
    'class="consumer-interview-workspace"',
    '<InteractionActionBar',
    '<ReportAgentToolsCard',
    '<ComparisonSnapshotWorkspace',
    '<PropagationPathGraph',
    '<ConsumerChatBrief',
    '<AgentProfileCard',
    '<InteractionChatPanel',
    '<RepresentativeConsumerInterview',
    '<VirtualFocusGroupPanel',
    '<InterviewHistoryPanel',
    '<InteractionSurveyPanel',
    'defineExpose',
    'chatPanelRef',
  ]) {
    assert.ok(shellContent.includes(token), `missing workspace shell token: ${token}`)
  }
})
