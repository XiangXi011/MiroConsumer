import service from './index'
import { createConsumerApi } from './consumerFactory'

export const {
  getConsumerSummary,
  getChannelSummary,
  getChannelEvents,
  getPropagationPaths,
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
  runConsumerResearchAction,
} = createConsumerApi(service)
