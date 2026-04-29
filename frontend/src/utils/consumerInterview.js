const ROLE_LABELS = {
  advocate: 'Advocate',
  skeptic: 'Skeptic',
  misreader: 'Misreader',
  price_sensitive: 'Price Sensitive',
  amplifier: 'Amplifier',
  trust_repairable: 'Trust Repairable',
}

const CHANNEL_LABELS = {
  xiaohongshu: '小红书',
  douyin: '抖音',
  wechat_group: '微信群',
  ecommerce_review: '电商评论区',
  zhihu_qa: '知乎/问答社区',
  offline_word_of_mouth: '线下口碑',
  livestream: '直播间',
  sales_assistant: '导购场景',
}

export function buildRepresentativeCardView(agent) {
  const role = agent.role || ''
  const channelId = agent.channel_id || ''
  const start = agent.purchase_intent_start ?? 0
  const latest = agent.purchase_intent_latest ?? 0
  const delta = Math.round((latest - start) * 100)
  const influence = Math.round((agent.influence_score || 0) * 100)

  return {
    roleLabel: ROLE_LABELS[role] || role,
    segment: agent.segment || '',
    channelLabel: CHANNEL_LABELS[channelId] || channelId,
    keyQuote: agent.key_quote || '',
    attitudeText: `${agent.attitude_start || ''} -> ${agent.attitude_latest || ''}`,
    purchaseIntentDeltaText: `${delta >= 0 ? '+' : ''}${delta}pp`,
    influenceText: `${influence}%`,
  }
}

export const INTERVIEW_ROLE_PRESETS = [
  { role: 'advocate', label: 'Advocate', description: 'Positive, willing to recommend' },
  { role: 'skeptic', label: 'Skeptic', description: 'Questions claims, demands proof' },
  { role: 'misreader', label: 'Misreader', description: 'Misinterprets key messages' },
  { role: 'price_sensitive', label: 'Price Sensitive', description: 'Focuses on value and cost' },
  { role: 'amplifier', label: 'Amplifier', description: 'Shares widely, high reach' },
  { role: 'trust_repairable', label: 'Trust Repairable', description: 'Lost trust but could recover' },
]

export function buildInterviewRequest({
  topic,
  questionsText,
  selectedAgentIds,
  selectedRoles,
  mode,
  maxAgents,
  targetContext,
}) {
  return {
    topic: topic || '',
    questions: (questionsText || '').split('\n').map((q) => q.trim()).filter(Boolean),
    agent_ids: selectedAgentIds || [],
    roles: selectedRoles || [],
    mode: mode || 'snapshot',
    max_agents: maxAgents || 3,
    target_context: targetContext || {},
  }
}

export function buildFocusGroupRequest({
  topic,
  moderatorGoal,
  selectedRoles,
  maxAgents,
  targetContext,
}) {
  return {
    topic: topic || '',
    moderator_goal: moderatorGoal || '',
    roles: selectedRoles || [],
    mode: 'snapshot',
    max_agents: Math.min(maxAgents || 8, 8),
    target_context: targetContext || {},
  }
}

export function extractConsumerItems(response) {
  if (!response || typeof response !== 'object') return []
  const data = 'data' in response ? response.data : response
  if (Array.isArray(data)) return data
  if (data && Array.isArray(data.items)) return data.items
  return []
}

export function normalizeInterviewHistoryItems({ interviews, focusGroups }) {
  const items = []
  for (const interview of interviews || []) {
    items.push({
      id: interview.interview_id,
      type: 'interview',
      topic: interview.topic || '',
      roles: interview.roles || [],
      createdAt: interview.created_at || '',
      summary: interview.summary || '',
    })
  }
  for (const fg of focusGroups || []) {
    items.push({
      id: fg.focus_group_id,
      type: 'focus_group',
      topic: fg.topic || '',
      roles: fg.roles || [],
      createdAt: fg.created_at || '',
      summary: (fg.consensus || []).join(', '),
    })
  }
  return items
}
