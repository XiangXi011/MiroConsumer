function formatPercent(value) {
  const numeric = Number(value)
  if (!Number.isFinite(numeric)) return '0%'
  return `${Math.round(numeric * 100)}%`
}

export function formatSocietyDelta(value) {
  const numeric = Number(value)
  if (!Number.isFinite(numeric) || numeric === 0) return '0pp'
  const points = Math.round(numeric * 100)
  return points > 0 ? `+${points}pp` : `${points}pp`
}

export function buildSocietyRunSummaryItems(context = {}) {
  const metrics = context.society_metrics || {}
  return [
    {
      key: 'mode',
      label: 'Society Mode',
      value: context.society_mode || 'quick',
    },
    {
      key: 'agents',
      label: 'Agents',
      value: String(context.society_agents_count || 0),
    },
    {
      key: 'rounds',
      label: 'Rounds',
      value: String(context.society_rounds_completed || context.current_round || 0),
    },
    {
      key: 'llmBudget',
      label: 'LLM Budget',
      value: String(context.society_llm_budget_used || 0),
    },
    {
      key: 'reach',
      label: 'Reach',
      value: formatPercent(metrics.reach_rate),
    },
    {
      key: 'misread',
      label: 'Misread',
      value: formatPercent(metrics.misread_rate),
    },
    {
      key: 'trustRecovery',
      label: 'Trust Recovery',
      value: formatPercent(metrics.trust_recovery_rate),
    },
    {
      key: 'purchaseIntentDelta',
      label: 'Purchase Intent',
      value: formatSocietyDelta(metrics.purchase_intent_delta),
    },
  ]
}
