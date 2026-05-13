import { test } from 'vitest'
import assert from 'node:assert/strict'

import { useComparisonState } from '../../src/composables/consumer/useComparisonState.ts'

test('useComparisonState returns refs with default values', () => {
  const state = useComparisonState()

  assert.equal(state.branchComparisonRaw.value, null)
  assert.deepEqual(state.comparisons.value, [])
  assert.equal(state.comparisonSnapshot.value, null)
  assert.equal(state.comparing.value, false)
  assert.equal(state.compareTargetSimId.value, '')
  assert.equal(state.compareTargetProjectId.value, '')
})

test('each call returns a fresh independent instance', () => {
  const a = useComparisonState()
  const b = useComparisonState()

  a.comparing.value = true
  assert.equal(a.comparing.value, true)
  assert.equal(b.comparing.value, false)
})

test('ref mutations are visible on the returned object', () => {
  const state = useComparisonState()

  state.branchComparisonRaw.value = { left: { acceptance_positive: 0.6 } }
  state.comparisons.value = [{ id: 'cmp-1' }]
  state.comparing.value = true
  state.compareTargetSimId.value = 'sim-123'
  state.compareTargetProjectId.value = 'proj-456'

  assert.deepEqual(state.branchComparisonRaw.value, { left: { acceptance_positive: 0.6 } })
  assert.deepEqual(state.comparisons.value, [{ id: 'cmp-1' }])
  assert.equal(state.comparing.value, true)
  assert.equal(state.compareTargetSimId.value, 'sim-123')
  assert.equal(state.compareTargetProjectId.value, 'proj-456')
})

test('reset restores all defaults', () => {
  const state = useComparisonState()

  state.branchComparisonRaw.value = { left: {} }
  state.comparisons.value = [{ id: 'cmp-1' }]
  state.comparisonSnapshot.value = { mode: 'branch_vs_base' }
  state.comparing.value = true
  state.compareTargetSimId.value = 'sim-1'
  state.compareTargetProjectId.value = 'proj-1'

  state.reset()

  assert.equal(state.branchComparisonRaw.value, null)
  assert.deepEqual(state.comparisons.value, [])
  assert.equal(state.comparisonSnapshot.value, null)
  assert.equal(state.comparing.value, false)
  assert.equal(state.compareTargetSimId.value, '')
  assert.equal(state.compareTargetProjectId.value, '')
})

test('setComparisons replaces the list', () => {
  const state = useComparisonState()
  const list = [{ id: 'a' }, { id: 'b' }]

  state.setComparisons(list)

  assert.deepEqual(state.comparisons.value, list)
})

test('addComparison appends an item', () => {
  const state = useComparisonState()

  state.setComparisons([{ id: 'a' }])
  state.addComparison({ id: 'b' })

  assert.deepEqual(state.comparisons.value, [{ id: 'a' }, { id: 'b' }])
})

test('removeComparison filters by id', () => {
  const state = useComparisonState()

  state.setComparisons([{ id: 'a' }, { id: 'b' }, { id: 'c' }])
  state.removeComparison('b')

  assert.deepEqual(state.comparisons.value, [{ id: 'a' }, { id: 'c' }])
})

test('setComparisonSnapshot sets the snapshot ref', () => {
  const state = useComparisonState()
  const snap = { mode: 'branch_vs_base' }

  state.setComparisonSnapshot(snap)

  assert.deepEqual(state.comparisonSnapshot.value, snap)
})

test('setComparing toggles the comparing flag', () => {
  const state = useComparisonState()

  state.setComparing(true)
  assert.equal(state.comparing.value, true)

  state.setComparing(false)
  assert.equal(state.comparing.value, false)
})

test('helper methods are instance-independent', () => {
  const a = useComparisonState()
  const b = useComparisonState()

  a.setComparisons([{ id: 'x' }])
  a.setComparing(true)

  assert.deepEqual(b.comparisons.value, [])
  assert.equal(b.comparing.value, false)
})
