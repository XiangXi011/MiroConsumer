import { test } from 'vitest'
import assert from 'node:assert/strict'

import { useResearchAssetState } from '../../src/composables/consumer/useResearchAssetState.ts'

test('useResearchAssetState returns refs with default values', () => {
  const state = useResearchAssetState()

  assert.deepEqual(state.researchAssets.value, [])
  assert.equal(state.exportingAsset.value, false)
  assert.equal(state.assetExportName.value, '')
})

test('each call returns a fresh independent instance', () => {
  const a = useResearchAssetState()
  const b = useResearchAssetState()

  a.exportingAsset.value = true
  assert.equal(a.exportingAsset.value, true)
  assert.equal(b.exportingAsset.value, false)
})

test('ref mutations are visible on the returned object', () => {
  const state = useResearchAssetState()

  state.researchAssets.value = [{ id: 'asset-1', name: 'Pack A' }]
  state.exportingAsset.value = true
  state.assetExportName.value = 'My Research Pack'

  assert.deepEqual(state.researchAssets.value, [{ id: 'asset-1', name: 'Pack A' }])
  assert.equal(state.exportingAsset.value, true)
  assert.equal(state.assetExportName.value, 'My Research Pack')
})

test('reset restores all defaults', () => {
  const state = useResearchAssetState()

  state.researchAssets.value = [{ id: 'asset-1' }]
  state.exportingAsset.value = true
  state.assetExportName.value = 'test'

  state.reset()

  assert.deepEqual(state.researchAssets.value, [])
  assert.equal(state.exportingAsset.value, false)
  assert.equal(state.assetExportName.value, '')
})

test('setResearchAssets replaces the list', () => {
  const state = useResearchAssetState()
  const list = [{ id: 'a' }, { id: 'b' }]

  state.setResearchAssets(list)

  assert.deepEqual(state.researchAssets.value, list)
})

test('addResearchAsset appends an item', () => {
  const state = useResearchAssetState()

  state.setResearchAssets([{ id: 'a' }])
  state.addResearchAsset({ id: 'b' })

  assert.deepEqual(state.researchAssets.value, [{ id: 'a' }, { id: 'b' }])
})

test('removeResearchAsset filters by id', () => {
  const state = useResearchAssetState()

  state.setResearchAssets([{ id: 'a' }, { id: 'b' }, { id: 'c' }])
  state.removeResearchAsset('b')

  assert.deepEqual(state.researchAssets.value, [{ id: 'a' }, { id: 'c' }])
})

test('setExportingAsset toggles the flag', () => {
  const state = useResearchAssetState()

  state.setExportingAsset(true)
  assert.equal(state.exportingAsset.value, true)

  state.setExportingAsset(false)
  assert.equal(state.exportingAsset.value, false)
})

test('setAssetExportName sets the name ref', () => {
  const state = useResearchAssetState()

  state.setAssetExportName('Export Pack')

  assert.equal(state.assetExportName.value, 'Export Pack')
})

test('helper methods are instance-independent', () => {
  const a = useResearchAssetState()
  const b = useResearchAssetState()

  a.setResearchAssets([{ id: 'x' }])
  a.setExportingAsset(true)

  assert.deepEqual(b.researchAssets.value, [])
  assert.equal(b.exportingAsset.value, false)
})
