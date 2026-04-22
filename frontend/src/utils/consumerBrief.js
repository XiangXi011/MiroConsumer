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
  const taskType = normalizeText(formData.consumerTaskType) || 'concept_test'
  const claims = splitItems(formData.consumerClaims)

  const brief = {
    task_type: taskType,
    target_audience: splitItems(formData.consumerAudience),
    usage_scene: splitItems(formData.consumerScene),
    research_goal: normalizeText(formData.consumerResearchGoal),
    research_mode: normalizeText(formData.consumerResearchMode) || 'manual_only',
    enable_lane_b: Boolean(formData.consumerEnableLaneB),
  }

  if (formData.personaPackSelection) {
    brief.persona_pack_selection = formData.personaPackSelection
  }

  // Task-specific fields
  if (taskType === 'concept_test') {
    brief.product_concept_assets = splitLines(formData.consumerConcept)
    brief.copy_material = splitLines(formData.consumerCopy)
  } else if (taskType === 'packaging_test') {
    brief.packaging_assets = splitLines(formData.consumerPackagingAssets)
    brief.copy_material = splitLines(formData.consumerCopy)
    if (claims.length > 0) {
      brief.claims = claims
    }
  } else if (taskType === 'ab_test') {
    brief.test_variants = buildTestVariants(formData.consumerTestVariants)
  } else if (taskType === 'price_test') {
    brief.price_points = splitItems(formData.consumerPricePoints)
    brief.price_context = normalizeText(formData.consumerPriceContext)
    brief.product_concept_assets = splitLines(formData.consumerConcept)
    brief.copy_material = splitLines(formData.consumerCopy)
    if (claims.length > 0) {
      brief.claims = claims
    }
  }

  // Legacy fallback: always include concept/copy if present for backward compat
  if (taskType === 'concept_test' || taskType === 'price_test') {
    if (claims.length > 0) {
      brief.claims = claims
    }
  }

  const background = splitLines(formData.consumerBackgroundMaterials)
  if (background.length > 0) {
    brief.optional_background_materials = background
  }

  return brief
}

function buildTestVariants(variantsRaw) {
  if (!variantsRaw) return []
  if (typeof variantsRaw === 'string') {
    // Simple line-based parsing for raw text
    return splitLines(variantsRaw).map((label, idx) => ({
      variant_id: `v${idx + 1}`,
      label,
    }))
  }
  if (Array.isArray(variantsRaw)) {
    return variantsRaw
      .filter(v => v && (v.label || v.variant_id))
      .map((v, idx) => ({
        variant_id: v.variant_id || `v${idx + 1}`,
        label: v.label || `Variant ${idx + 1}`,
        concept_assets: v.concept_assets || [],
        copy_material: v.copy_material || [],
        claims: v.claims || [],
        packaging_assets: v.packaging_assets || [],
        price_points: v.price_points || [],
      }))
  }
  return []
}

export function isConsumerBriefComplete(formData = {}) {
  const taskType = normalizeText(formData.consumerTaskType) || 'concept_test'

  const hasAudience = splitItems(formData.consumerAudience).length > 0
  const hasResearchGoal = normalizeText(formData.consumerResearchGoal) !== ''

  if (!hasAudience || !hasResearchGoal) {
    return false
  }

  if (taskType === 'concept_test') {
    return (
      splitLines(formData.consumerConcept).length > 0 &&
      splitLines(formData.consumerCopy).length > 0
    )
  }

  if (taskType === 'packaging_test') {
    return splitLines(formData.consumerPackagingAssets).length > 0
  }

  if (taskType === 'ab_test') {
    const variants = buildTestVariants(formData.consumerTestVariants)
    return variants.length >= 2
  }

  if (taskType === 'price_test') {
    return splitItems(formData.consumerPricePoints).length > 0
  }

  return true
}

export function resolveSimulationRequirement(projectType, simulationRequirement, consumerFallback = '') {
  const prompt = normalizeText(simulationRequirement)
  if (projectType === 'consumer_test') {
    return prompt || normalizeText(consumerFallback)
  }
  return prompt
}
