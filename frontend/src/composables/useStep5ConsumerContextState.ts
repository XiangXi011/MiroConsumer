// @ts-nocheck
import { computed, ref } from 'vue'
import {
  buildConsumerQuickPrompts,
  buildBranchAwarePrompts,
  buildCascadeAwarePrompts,
  buildComparisonAwarePrompts,
  buildReplayAwarePrompts,
  isConsumerProject,
  pickTopVocQuotes,
} from '../utils/consumerMode'

export function useStep5ConsumerContextState({ props, t }) {
  const isConsumerMode = computed(() => (
    isConsumerProject(props.reportData) || isConsumerProject(props.projectData)
  ))

  const reportContext = computed(() => props.reportData?.report_context || {})

  const workspaceBranchComparison = ref(null)
  const workspaceComparisonSnapshot = ref(null)

  const effectiveComparisonSnapshot = computed(() => props.comparisonSnapshot || workspaceComparisonSnapshot.value)

  const consumerQuickPrompts = computed(() => {
    if (!isConsumerMode.value) return []
    const basePrompts = props.reportData?.report_context
      ? buildConsumerQuickPrompts(props.reportData.report_context, t)
      : []
    const branchPrompts = workspaceBranchComparison.value
      ? buildBranchAwarePrompts(workspaceBranchComparison.value, t)
      : []
    const cascadePrompts = props.reportData?.report_context
      ? buildCascadeAwarePrompts(props.reportData.report_context, t)
      : []
    const snapshot = effectiveComparisonSnapshot.value
    const comparisonPrompts = snapshot
      ? buildComparisonAwarePrompts(snapshot, t)
      : []
    const replayPrompts = props.reportData?.report_context
      ? buildReplayAwarePrompts(props.reportData.report_context, t)
      : []
    return [...basePrompts, ...branchPrompts, ...cascadePrompts, ...comparisonPrompts, ...replayPrompts]
  })

  const consumerVocHighlights = computed(() => (
    isConsumerMode.value && props.reportData?.report_context
      ? pickTopVocQuotes(props.reportData.report_context, t)
      : []
  ))

  const consumerSourceCatalog = computed(() => (
    isConsumerMode.value && props.reportData?.report_context
      ? (props.reportData.report_context.source_catalog || [])
      : []
  ))

  const consumerEnrichedFindings = computed(() => {
    if (!isConsumerMode.value || !props.reportData?.report_context) return []
    const enriched = props.reportData.report_context.enriched_findings || []
    if (enriched.length > 0) {
      return enriched.filter(f => f && f.summary)
    }
    return (props.reportData.report_context.research_findings || []).filter(f => f && f.summary)
  })

  return {
    isConsumerMode,
    reportContext,
    workspaceBranchComparison,
    workspaceComparisonSnapshot,
    effectiveComparisonSnapshot,
    consumerQuickPrompts,
    consumerVocHighlights,
    consumerSourceCatalog,
    consumerEnrichedFindings,
  }
}
