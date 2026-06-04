// @ts-nocheck
export function buildSurveyInterviewRequests(selectedAgentIndexes, question) {
  const prompt = String(question || '').trim()
  return Array.from(selectedAgentIndexes || []).map(idx => ({
    agent_id: idx,
    prompt,
  }))
}

export function normalizeSurveyResults({
  interviews,
  profiles,
  resultData,
  question,
  noResponseText,
}) {
  const rawResults = resultData?.results || resultData
  const fallback = noResponseText || ''

  return (interviews || []).map(interview => {
    const agentIdx = interview.agent_id
    const agent = (profiles || [])[agentIdx]
    let responseContent = fallback

    if (rawResults && typeof rawResults === 'object' && !Array.isArray(rawResults)) {
      const redditKey = `reddit_${agentIdx}`
      const twitterKey = `twitter_${agentIdx}`
      const agentResult = rawResults[redditKey] || rawResults[twitterKey]
      if (agentResult) {
        responseContent = agentResult.response || agentResult.answer || fallback
      }
    } else if (Array.isArray(rawResults)) {
      const matchedResult = rawResults.find(result => result.agent_id === agentIdx)
      if (matchedResult) {
        responseContent = matchedResult.response || matchedResult.answer || fallback
      }
    }

    return {
      agent_id: agentIdx,
      agent_name: agent?.username || `Agent ${agentIdx}`,
      profession: agent?.profession,
      question,
      answer: responseContent,
    }
  })
}

export function extractAgentChatResponse({ resultData, agentId }) {
  const rawResults = resultData?.results || resultData

  if (rawResults && typeof rawResults === 'object' && !Array.isArray(rawResults)) {
    const redditKey = `reddit_${agentId}`
    const twitterKey = `twitter_${agentId}`
    const agentResult = rawResults[redditKey] || rawResults[twitterKey] || Object.values(rawResults)[0]
    return agentResult?.response || agentResult?.answer || ''
  }

  if (Array.isArray(rawResults) && rawResults.length > 0) {
    return rawResults[0].response || rawResults[0].answer || ''
  }

  return ''
}
