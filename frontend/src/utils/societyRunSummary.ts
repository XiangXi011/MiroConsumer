// @ts-nocheck
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

export function buildSocietyRunDiagnosticItems(context = {}) {
  const items = []
  if (context.phase6j_status !== undefined) {
    items.push({ key: 'phase6j_status', label: 'Phase6J Status', value: String(context.phase6j_status) })
  }
  if (context.error_code !== undefined) {
    items.push({ key: 'error_code', label: 'Error Code', value: String(context.error_code) })
  }
  if (context.blocking_stage !== undefined) {
    items.push({ key: 'blocking_stage', label: 'Blocking Stage', value: String(context.blocking_stage) })
  }
  if (context.next_action !== undefined) {
    items.push({ key: 'next_action', label: 'Next Action', value: String(context.next_action) })
  }
  return items
}

export function buildSocietyRunSummaryItems(context = {}, options = {}) {
  const metrics = context.society_metrics || {}
  const completedAgents = Number(context.completed_agents ?? context.society_completed_agents ?? 0)
  const totalAgents = Number(context.total_agents ?? context.society_agents_count ?? 0)
  const businessItems = [
    {
      key: 'consumers',
      label: '消费者画像',
      value: String(context.society_agents_count || 0),
    },
    {
      key: 'rounds',
      label: '传播轮次',
      value: String(context.society_rounds_completed || context.current_round || 0),
    },
    {
      key: 'reach',
      label: '触达率',
      value: formatPercent(metrics.reach_rate),
    },
    {
      key: 'misread',
      label: '误读风险',
      value: formatPercent(metrics.misread_rate),
    },
    {
      key: 'trustRecovery',
      label: '信任修复',
      value: formatPercent(metrics.trust_recovery_rate),
    },
    {
      key: 'purchaseIntentDelta',
      label: '购买意向变化',
      value: formatSocietyDelta(metrics.purchase_intent_delta),
    },
    {
      key: 'progressStatus',
      label: '测试状态',
      value: context.status || context.progress_status || 'idle',
    },
  ]

  if (!options.includeTechnical) {
    return businessItems
  }

  return [
    {
      key: 'mode',
      label: 'Society Mode',
      value: context.society_mode || 'quick',
    },
    ...businessItems,
    {
      key: 'llmBudget',
      label: 'LLM Budget',
      value: String(context.society_llm_budget_used || 0),
    },
    {
      key: 'agentProgress',
      label: 'Agent Progress',
      value: `${Number.isFinite(completedAgents) ? completedAgents : 0} / ${Number.isFinite(totalAgents) ? totalAgents : 0}`,
    },
    {
      key: 'currentLayer',
      label: 'Current Layer',
      value: context.current_layer || '-',
    },
    {
      key: 'currentBackend',
      label: 'Backend',
      value: context.reasoning_backend || '-',
    },
    {
      key: 'llmInvoked',
      label: 'LLM Calls',
      value: String(context.llm_invoked_count ?? 0),
    },
    {
      key: 'rulesCount',
      label: 'Rules',
      value: String(context.rules_count ?? 0),
    },
    {
      key: 'fallbackCount',
      label: 'Fallback',
      value: String(context.template_fallback_count ?? 0),
    },
    {
      key: 'failedCount',
      label: 'Failed',
      value: String(context.failed_count ?? 0),
    },
  ]
}
