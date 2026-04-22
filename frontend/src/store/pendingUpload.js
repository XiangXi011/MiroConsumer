/**
 * Temporary cross-route payload for the existing Home -> Process flow.
 *
 * Payload shape by example:
 * {
 *   files: [File, ...],
 *   simulationRequirement: 'Run consumer propagation test',
 *   projectType: 'consumer_test',
 *   consumerBrief: {
 *     task_type: 'concept_test',
 *     product_concept_assets: ['High-protein yogurt for busy mornings'],
 *     copy_material: ['14g protein', 'Low sugar'],
 *     claims: ['14g protein', 'Low sugar'],
 *     target_audience: ['working moms'],
 *     usage_scene: ['weekday breakfast'],
 *     research_goal: 'Find resonance and misread risks'
 *   }
 * }
 */
import { reactive } from 'vue'

const createDefaultState = () => ({
  files: [],
  simulationRequirement: '',
  projectType: 'default',
  consumerBrief: null,
  researchMode: 'manual_only',
  enableLaneB: false,
  personaPackSelection: null,
  personaPackFile: null,
  isPending: false
})

const state = reactive(createDefaultState())

export function setPendingUpload(filesOrPayload, requirement) {
  const payload = Array.isArray(filesOrPayload)
    ? {
        files: filesOrPayload,
        simulationRequirement: requirement || ''
      }
    : (filesOrPayload || {})

  state.files = payload.files || []
  state.simulationRequirement = payload.simulationRequirement || ''
  state.projectType = payload.projectType || 'default'
  state.consumerBrief = payload.consumerBrief || null
  state.researchMode = payload.researchMode || 'manual_only'
  state.enableLaneB = payload.enableLaneB || false
  state.personaPackSelection = payload.personaPackSelection || null
  state.personaPackFile = payload.personaPackFile || null
  state.isPending = true
}

export function getPendingUpload() {
  return {
    files: state.files,
    simulationRequirement: state.simulationRequirement,
    projectType: state.projectType,
    consumerBrief: state.consumerBrief,
    researchMode: state.researchMode,
    enableLaneB: state.enableLaneB,
    personaPackSelection: state.personaPackSelection,
    personaPackFile: state.personaPackFile,
    isPending: state.isPending
  }
}

export function clearPendingUpload() {
  Object.assign(state, createDefaultState())
}

export default state
