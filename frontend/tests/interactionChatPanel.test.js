import { test } from 'vitest'
import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

const step5Path = join(__dirname, '../src/components/Step5Interaction.vue')
const workspaceShellPath = join(__dirname, '../src/components/report/InteractionWorkspaceShell.vue')
const chatPanelPath = join(__dirname, '../src/components/report/InteractionChatPanel.vue')

const step5Content = readFileSync(step5Path, 'utf-8')
const workspaceShellContent = readFileSync(workspaceShellPath, 'utf-8')

test('Step5Interaction delegates chat messages and input rendering', () => {
  assert.ok(existsSync(chatPanelPath), 'InteractionChatPanel component must exist')
  assert.ok(step5Content.includes("import InteractionWorkspaceShell from './report/InteractionWorkspaceShell.vue'"), 'Step5 must import InteractionWorkspaceShell')
  assert.ok(step5Content.includes('<InteractionWorkspaceShell'), 'Step5 must render InteractionWorkspaceShell')
  assert.ok(workspaceShellContent.includes("import InteractionChatPanel from './InteractionChatPanel.vue'"), 'InteractionWorkspaceShell must import InteractionChatPanel')
  assert.ok(workspaceShellContent.includes('<InteractionChatPanel'), 'InteractionWorkspaceShell must render InteractionChatPanel')
  assert.ok(step5Content.includes(':chat-history="chatHistory"'), 'Step5 must pass chat history')
  assert.ok(step5Content.includes('v-model:chat-input="chatInput"'), 'Step5 must bind chat input')
  assert.ok(step5Content.includes(':is-sending="isSending"'), 'Step5 must pass sending state')
  assert.ok(step5Content.includes('@send-message="sendMessage"'), 'Step5 must keep send handling')
  assert.ok(step5Content.includes('ref="chatPanelRef"'), 'Step5 must keep a component ref for chat scrolling and focus')
  assert.ok(!step5Content.includes('class="chat-messages"'), 'chat messages markup should live outside Step5Interaction')
  assert.ok(!step5Content.includes('class="chat-input-area"'), 'chat input markup should live outside Step5Interaction')
})

test('InteractionChatPanel owns chat message, typing, and input rendering', () => {
  const chatPanelContent = readFileSync(chatPanelPath, 'utf-8')
  for (const token of [
    'class="chat-messages"',
    'class="chat-input-area"',
    'chatHistory.length === 0',
    'v-for="(msg, idx) in chatHistory"',
    'renderMarkdown(msg.content)',
    'formatTime(msg.timestamp)',
    'class="typing-indicator"',
    "emit('send-message')",
    "emit('update:chat-input'",
    'defineExpose',
    "t('step5.chatEmptyReportAgent')",
    "t('step5.chatInputPlaceholder')",
  ]) {
    assert.ok(chatPanelContent.includes(token), `missing chat panel token: ${token}`)
  }
})
