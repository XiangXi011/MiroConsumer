import { test } from 'vitest'
import assert from 'node:assert/strict'

import { useBranchInterventionState } from '../../src/composables/consumer/useBranchInterventionState.js'

test('useBranchInterventionState returns refs with default values', () => {
  const state = useBranchInterventionState()

  assert.deepEqual(state.branches.value, [])
  assert.equal(state.selectedBranchId.value, '')
  assert.equal(state.selectedBranch.value, null)
  assert.equal(state.showCreateBranch.value, false)
  assert.equal(state.newBranchName.value, '')
  assert.equal(state.newBranchForkRound.value, 0)
  assert.equal(state.newBranchDescription.value, '')
  assert.equal(state.creatingBranch.value, false)
  assert.deepEqual(state.branchInterventions.value, [])
  assert.equal(state.showAddIntervention.value, false)
  assert.equal(state.newInterventionType.value, '')
  assert.equal(state.newInterventionPayload.value, '')
  assert.equal(state.newInterventionTargetRound.value, null)
  assert.equal(state.addingIntervention.value, false)
  assert.equal(state.runningBranch.value, false)
  assert.equal(state.branchRunStatus.value, null)
})

test('each call returns a fresh independent instance', () => {
  const a = useBranchInterventionState()
  const b = useBranchInterventionState()

  a.creatingBranch.value = true
  assert.equal(a.creatingBranch.value, true)
  assert.equal(b.creatingBranch.value, false)
})

test('ref mutations are visible on the returned object', () => {
  const state = useBranchInterventionState()

  state.branches.value = [{ branch_id: 'b1', name: 'Main', fork_round: 0 }]
  state.selectedBranchId.value = 'b1'
  state.showCreateBranch.value = true
  state.newBranchName.value = 'Test'
  state.newBranchForkRound.value = 3
  state.newBranchDescription.value = 'desc'
  state.creatingBranch.value = true
  state.branchInterventions.value = [{ intervention_id: 'i1' }]
  state.showAddIntervention.value = true
  state.newInterventionType.value = 'clarification_injection'
  state.newInterventionPayload.value = 'payload'
  state.newInterventionTargetRound.value = 5
  state.addingIntervention.value = true
  state.runningBranch.value = true
  state.branchRunStatus.value = { status: 'running' }

  assert.deepEqual(state.branches.value, [{ branch_id: 'b1', name: 'Main', fork_round: 0 }])
  assert.equal(state.selectedBranchId.value, 'b1')
  assert.equal(state.showCreateBranch.value, true)
  assert.equal(state.newBranchName.value, 'Test')
  assert.equal(state.newBranchForkRound.value, 3)
  assert.equal(state.newBranchDescription.value, 'desc')
  assert.equal(state.creatingBranch.value, true)
  assert.deepEqual(state.branchInterventions.value, [{ intervention_id: 'i1' }])
  assert.equal(state.showAddIntervention.value, true)
  assert.equal(state.newInterventionType.value, 'clarification_injection')
  assert.equal(state.newInterventionPayload.value, 'payload')
  assert.equal(state.newInterventionTargetRound.value, 5)
  assert.equal(state.addingIntervention.value, true)
  assert.equal(state.runningBranch.value, true)
  assert.deepEqual(state.branchRunStatus.value, { status: 'running' })
})

test('selectedBranch resolves correctly from branches list', () => {
  const state = useBranchInterventionState()

  state.branches.value = [
    { branch_id: 'b1', name: 'Alpha', fork_round: 0 },
    { branch_id: 'b2', name: 'Beta', fork_round: 5 },
  ]
  state.selectedBranchId.value = 'b2'

  assert.deepEqual(state.selectedBranch.value, { branch_id: 'b2', name: 'Beta', fork_round: 5 })
})

test('selectedBranch returns null when no match', () => {
  const state = useBranchInterventionState()

  state.branches.value = [{ branch_id: 'b1', name: 'Alpha', fork_round: 0 }]
  state.selectedBranchId.value = 'nonexistent'

  assert.equal(state.selectedBranch.value, null)
})

test('reset restores all defaults', () => {
  const state = useBranchInterventionState()

  state.branches.value = [{ branch_id: 'b1' }]
  state.selectedBranchId.value = 'b1'
  state.showCreateBranch.value = true
  state.newBranchName.value = 'X'
  state.newBranchForkRound.value = 9
  state.newBranchDescription.value = 'd'
  state.creatingBranch.value = true
  state.branchInterventions.value = [{ intervention_id: 'i1' }]
  state.showAddIntervention.value = true
  state.newInterventionType.value = 'evidence_reveal'
  state.newInterventionPayload.value = 'p'
  state.newInterventionTargetRound.value = 3
  state.addingIntervention.value = true
  state.runningBranch.value = true
  state.branchRunStatus.value = { status: 'completed' }

  state.reset()

  assert.deepEqual(state.branches.value, [])
  assert.equal(state.selectedBranchId.value, '')
  assert.equal(state.selectedBranch.value, null)
  assert.equal(state.showCreateBranch.value, false)
  assert.equal(state.newBranchName.value, '')
  assert.equal(state.newBranchForkRound.value, 0)
  assert.equal(state.newBranchDescription.value, '')
  assert.equal(state.creatingBranch.value, false)
  assert.deepEqual(state.branchInterventions.value, [])
  assert.equal(state.showAddIntervention.value, false)
  assert.equal(state.newInterventionType.value, '')
  assert.equal(state.newInterventionPayload.value, '')
  assert.equal(state.newInterventionTargetRound.value, null)
  assert.equal(state.addingIntervention.value, false)
  assert.equal(state.runningBranch.value, false)
  assert.equal(state.branchRunStatus.value, null)
})

test('helper methods are instance-independent', () => {
  const a = useBranchInterventionState()
  const b = useBranchInterventionState()

  a.branches.value = [{ branch_id: 'b1' }]
  a.selectedBranchId.value = 'b1'
  a.runningBranch.value = true

  assert.deepEqual(b.branches.value, [])
  assert.equal(b.selectedBranchId.value, '')
  assert.equal(b.runningBranch.value, false)
})
