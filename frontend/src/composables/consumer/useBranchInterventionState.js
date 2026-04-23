import { ref, computed } from 'vue'

export function useBranchInterventionState() {
  const branches = ref([])
  const selectedBranchId = ref('')
  const showCreateBranch = ref(false)
  const newBranchName = ref('')
  const newBranchForkRound = ref(0)
  const newBranchDescription = ref('')
  const creatingBranch = ref(false)

  const branchInterventions = ref([])
  const showAddIntervention = ref(false)
  const newInterventionType = ref('')
  const newInterventionPayload = ref('')
  const newInterventionTargetRound = ref(null)
  const addingIntervention = ref(false)

  const runningBranch = ref(false)
  const branchRunStatus = ref(null)

  const selectedBranch = computed(() =>
    branches.value.find(b => b.branch_id === selectedBranchId.value) || null
  )

  function reset() {
    branches.value = []
    selectedBranchId.value = ''
    showCreateBranch.value = false
    newBranchName.value = ''
    newBranchForkRound.value = 0
    newBranchDescription.value = ''
    creatingBranch.value = false
    branchInterventions.value = []
    showAddIntervention.value = false
    newInterventionType.value = ''
    newInterventionPayload.value = ''
    newInterventionTargetRound.value = null
    addingIntervention.value = false
    runningBranch.value = false
    branchRunStatus.value = null
  }

  return {
    branches,
    selectedBranchId,
    selectedBranch,
    showCreateBranch,
    newBranchName,
    newBranchForkRound,
    newBranchDescription,
    creatingBranch,
    branchInterventions,
    showAddIntervention,
    newInterventionType,
    newInterventionPayload,
    newInterventionTargetRound,
    addingIntervention,
    runningBranch,
    branchRunStatus,
    reset,
  }
}
