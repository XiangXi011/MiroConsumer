import { test } from 'vitest'
import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { nextTick } from 'vue'

import { useStep5ChatState } from '../src/composables/useStep5ChatState.ts'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

const step5Path = join(__dirname, '../src/components/Step5Interaction.vue')
const composablePath = join(__dirname, '../src/composables/useStep5ChatState.ts')

test('useStep5ChatState manages chat targets, cached histories, prompts, and scrolling refs', async () => {
  assert.ok(existsSync(composablePath), 'useStep5ChatState composable must exist')

  const logs = []
  const chatDom = { scrollTop: 0, scrollHeight: 240 }
  let focused = false
  const state = useStep5ChatState({
    addLog: message => logs.push(message),
    formatSelectChatTargetLog: agent => `selected ${agent.username}`,
  })

  state.chatHistory.value = [{ role: 'assistant', content: 'report reply' }]
  state.selectAgent({ username: 'Ava' }, 2)
  assert.equal(state.activeTab.value, 'chat')
  assert.equal(state.chatTarget.value, 'agent')
  assert.equal(state.selectedAgent.value.username, 'Ava')
  assert.equal(state.chatHistoryCache.value.report_agent.length, 1)
  assert.deepEqual(state.chatHistory.value, [])
  assert.deepEqual(logs, ['selected Ava'])

  state.chatHistory.value = [{ role: 'user', content: 'agent question' }]
  state.selectReportAgentChat()
  assert.equal(state.chatTarget.value, 'report_agent')
  assert.equal(state.selectedAgent.value, null)
  assert.deepEqual(state.chatHistory.value, [{ role: 'assistant', content: 'report reply' }])
  assert.deepEqual(state.chatHistoryCache.value.agent_2, [{ role: 'user', content: 'agent question' }])

  state.chatPanelRef.value = {
    chatPanelRef: {
      chatInputRef: { focus: () => { focused = true } },
      chatMessages: chatDom,
    },
  }
  state.applyQuickPrompt('Ask about trust')
  await nextTick()
  assert.equal(state.chatInput.value, 'Ask about trust')
  assert.equal(state.chatTarget.value, 'report_agent')
  assert.equal(focused, true)

  state.scrollToBottom()
  await nextTick()
  assert.equal(chatDom.scrollTop, 240)
})

test('Step5Interaction delegates chat state to useStep5ChatState', () => {
  const step5Content = readFileSync(step5Path, 'utf-8')
  assert.ok(step5Content.includes("import { useStep5ChatState } from '../composables/useStep5ChatState'"), 'Step5 must import useStep5ChatState')
  assert.ok(step5Content.includes('useStep5ChatState({'), 'Step5 must initialize chat state via composable')
  for (const token of [
    "const activeTab = ref('chat')",
    "const chatTarget = ref('report_agent')",
    'const showAgentDropdown = ref(false)',
    'const selectedAgent = ref(null)',
    'const selectedAgentIndex = ref(null)',
    "const chatInput = ref('')",
    'const chatHistory = ref([])',
    'const chatHistoryCache = ref({})',
    'const isSending = ref(false)',
    'const chatPanelRef = ref(null)',
    'const saveChatHistory = ()',
    'const selectReportAgentChat = ()',
    'const selectSurveyTab = ()',
    'const toggleAgentDropdown = ()',
    'const selectAgent = (agent, idx)',
    'const scrollToBottom = ()',
  ]) {
    assert.ok(!step5Content.includes(token), `Step5 should not inline chat state token: ${token}`)
  }
})
