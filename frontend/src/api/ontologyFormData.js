/**
 * Build the multipart payload used by /api/graph/ontology/generate.
 * Accepts the shared pending-upload payload shape from the Home page.
 */
export function buildOntologyFormData(payload = {}) {
  const formData = new FormData()

  for (const file of payload.files || []) {
    formData.append('files', file)
  }

  formData.append('simulation_requirement', payload.simulationRequirement || '')
  formData.append('project_type', payload.projectType || 'consumer_test')

  if (payload.projectName) {
    formData.append('project_name', payload.projectName)
  }

  if (payload.additionalContext) {
    formData.append('additional_context', payload.additionalContext)
  }

  if (payload.consumerBrief) {
    const brief = { ...payload.consumerBrief }
    if (payload.enableLaneB !== undefined) {
      brief.enable_lane_b = Boolean(payload.enableLaneB)
    }
    formData.append('consumer_brief', JSON.stringify(brief))
  }

  if (payload.personaPackFile) {
    formData.append('persona_pack_file', payload.personaPackFile)
  }

  return formData
}
