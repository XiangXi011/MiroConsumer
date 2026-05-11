import service from './index'
import { createConsumerApi } from './consumerFactory'

export const {
  getConsumerSummary,
  getChannelSummary,
  getChannelEvents,
  getPropagationPaths,
  listRepresentativeAgents,
  runConsumerInterview,
  runFocusGroup,
  listInterviewHistory,
  listFocusGroupHistory,
  listBranches,
  createBranch,
  getBranchComparison,
  runBranch,
  getBranchStatus,
  listInterventions,
  addIntervention,
  exportResearchAsset,
  listResearchAssets,
  getResearchAsset,
  compareResearchSnapshots,
  listComparisons,
  getComparison,
  getReportEvidenceGraph,
  runConsumerResearchAction,
} = createConsumerApi(service)
