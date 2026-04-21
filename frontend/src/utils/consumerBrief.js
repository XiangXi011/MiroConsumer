const ITEM_SPLIT_PATTERN = /[\n,，;；]+/

function normalizeText(value) {
  return typeof value === 'string' ? value.trim() : ''
}

function splitLines(value) {
  return normalizeText(value)
    .split('\n')
    .map(item => item.trim())
    .filter(Boolean)
}

function splitItems(value) {
  return normalizeText(value)
    .split(ITEM_SPLIT_PATTERN)
    .map(item => item.trim())
    .filter(Boolean)
}

export function buildConsumerBrief(formData = {}) {
  const claims = splitItems(formData.consumerClaims)

  const brief = {
    task_type: 'concept_test',
    product_concept_assets: splitLines(formData.consumerConcept),
    copy_material: splitLines(formData.consumerCopy),
    target_audience: splitItems(formData.consumerAudience),
    usage_scene: splitItems(formData.consumerScene),
    research_goal: normalizeText(formData.consumerResearchGoal),
    research_mode: normalizeText(formData.consumerResearchMode) || 'manual_only',
    enable_lane_b: Boolean(formData.consumerEnableLaneB),
  }

  if (claims.length > 0) {
    brief.claims = claims
  }

  const background = splitLines(formData.consumerBackgroundMaterials)
  if (background.length > 0) {
    brief.optional_background_materials = background
  }

  return brief
}

export function isConsumerBriefComplete(formData = {}) {
  const brief = buildConsumerBrief(formData)
  return (
    brief.product_concept_assets.length > 0 &&
    brief.copy_material.length > 0 &&
    brief.target_audience.length > 0 &&
    brief.research_goal !== ''
  )
}

export function resolveSimulationRequirement(projectType, simulationRequirement, consumerFallback = '') {
  const prompt = normalizeText(simulationRequirement)
  if (projectType === 'consumer_test') {
    return prompt || normalizeText(consumerFallback)
  }
  return prompt
}
