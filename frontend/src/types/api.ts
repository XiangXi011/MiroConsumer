export interface ApiEnvelope<T = unknown> {
  success: boolean
  data?: T
  error?: string
  message?: string
  details?: Record<string, unknown>
}

export interface PaginationMeta {
  page: number
  page_size: number
  total: number
}

export interface ProjectSummary {
  project_id: string
  name: string
  project_type?: string
  tenant_id?: string
  status?: string
}

export interface SimulationSummary {
  simulation_id: string
  project_id: string
  graph_id?: string
  status: string
  current_round?: number
  tenant_id?: string
}

export interface ConsumerReportSummary {
  report_id: string
  simulation_id: string
  status: string
  markdown_content?: string
}

export interface ConsumerBranch {
  branch_id: string
  simulation_id: string
  parent_branch_id?: string | null
  fork_round: number
  name: string
  description?: string
  status?: string
}

export interface ConsumerIntervention {
  intervention_id: string
  branch_id: string
  simulation_id: string
  intervention_type: string
  payload: Record<string, unknown>
  target_round?: number | null
}

export interface ResearchAsset {
  asset_id: string
  project_id: string
  simulation_id: string
  name: string
  created_at?: string
}
