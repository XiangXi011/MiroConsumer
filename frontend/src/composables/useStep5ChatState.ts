// @ts-nocheck
import { nextTick, ref } from 'vue'

export function useStep5ChatState({
  addLog = () => {},
  formatSelectChatTargetLog = agent => agent?.username || '',
} = {}) {
  const activeTab = ref('chat')
  const chatTarget = ref('report_agent')
  const showAgentDropdown = ref(false)
  const selectedAgent = ref(null)
  const selectedAgentIndex = ref(null)

  const chatInput = ref('')
  const chatHistory = ref([])
  const chatHistoryCache = ref({})
  const isSending = ref(false)
  const chatPanelRef = ref(null)

  const focusChatInput = () => {
    nextTick(() => {
      chatPanelRef.value?.chatPanelRef?.chatInputRef?.focus()
    })
  }

  const applyQuickPrompt = (prompt) => {
    chatInput.value = prompt
    activeTab.value = 'chat'
    chatTarget.value = 'report_agent'
    focusChatInput()
  }

  const selectChatTarget = (target) => {
    chatTarget.value = target
    if (target === 'report_agent') {
      showAgentDropdown.value = false
    }
  }

  const saveChatHistory = () => {
    if (chatHistory.value.length === 0) return

    if (chatTarget.value === 'report_agent') {
      chatHistoryCache.value.report_agent = [...chatHistory.value]
    } else if (selectedAgentIndex.value !== null) {
      chatHistoryCache.value[`agent_${selectedAgentIndex.value}`] = [...chatHistory.value]
    }
  }

  const selectReportAgentChat = () => {
    saveChatHistory()

    activeTab.value = 'chat'
    chatTarget.value = 'report_agent'
    selectedAgent.value = null
    selectedAgentIndex.value = null
    showAgentDropdown.value = false

    chatHistory.value = chatHistoryCache.value.report_agent || []
  }

  const selectSurveyTab = () => {
    activeTab.value = 'survey'
    selectedAgent.value = null
    selectedAgentIndex.value = null
    showAgentDropdown.value = false
  }

  const toggleAgentDropdown = () => {
    showAgentDropdown.value = !showAgentDropdown.value
    if (showAgentDropdown.value) {
      activeTab.value = 'chat'
      chatTarget.value = 'agent'
    }
  }

  const selectAgent = (agent, idx) => {
    saveChatHistory()

    selectedAgent.value = agent
    selectedAgentIndex.value = idx
    chatTarget.value = 'agent'
    showAgentDropdown.value = false

    chatHistory.value = chatHistoryCache.value[`agent_${idx}`] || []
    addLog(formatSelectChatTargetLog(agent))
  }

  const scrollToBottom = () => {
    nextTick(() => {
      const chatMessages = chatPanelRef.value?.chatPanelRef?.chatMessages
      if (chatMessages) {
        chatMessages.scrollTop = chatMessages.scrollHeight
      }
    })
  }

  return {
    activeTab,
    chatTarget,
    showAgentDropdown,
    selectedAgent,
    selectedAgentIndex,
    chatInput,
    chatHistory,
    chatHistoryCache,
    isSending,
    chatPanelRef,
    applyQuickPrompt,
    selectChatTarget,
    saveChatHistory,
    selectReportAgentChat,
    selectSurveyTab,
    toggleAgentDropdown,
    selectAgent,
    scrollToBottom,
  }
}
