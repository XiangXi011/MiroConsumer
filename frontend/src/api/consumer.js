import service from './index'
import { createConsumerApi } from './consumerFactory'

export const {
  getConsumerSummary,
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
} = createConsumerApi(service)
