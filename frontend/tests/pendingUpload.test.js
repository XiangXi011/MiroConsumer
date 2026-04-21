import { afterEach, test } from 'node:test'
import assert from 'node:assert/strict'

import {
  clearPendingUpload,
  getPendingUpload,
  setPendingUpload,
} from '../src/store/pendingUpload.js'

afterEach(() => {
  clearPendingUpload()
})

test('setPendingUpload keeps legacy signature backward compatible', () => {
  const files = [{ name: 'brief.pdf' }]

  setPendingUpload(files, 'Run legacy simulation')

  assert.deepEqual(getPendingUpload(), {
    files,
    simulationRequirement: 'Run legacy simulation',
    projectType: 'default',
    consumerBrief: null,
    researchMode: 'manual_only',
    enableLaneB: false,
    isPending: true,
  })
})

test('setPendingUpload stores consumer payload and clearPendingUpload resets it', () => {
  const files = [{ name: 'concept.pdf' }]
  const consumerBrief = {
    task_type: 'concept_test',
    product_concept_assets: ['High-protein yogurt'],
    copy_material: ['14g protein'],
    target_audience: ['working moms'],
    research_goal: 'Find resonance',
  }

  setPendingUpload({
    files,
    simulationRequirement: 'Run consumer propagation test',
    projectType: 'consumer_test',
    consumerBrief,
  })

  assert.deepEqual(getPendingUpload(), {
    files,
    simulationRequirement: 'Run consumer propagation test',
    projectType: 'consumer_test',
    consumerBrief,
    researchMode: 'manual_only',
    enableLaneB: false,
    isPending: true,
  })

  clearPendingUpload()

  assert.deepEqual(getPendingUpload(), {
    files: [],
    simulationRequirement: '',
    projectType: 'default',
    consumerBrief: null,
    researchMode: 'manual_only',
    enableLaneB: false,
    isPending: false,
  })
})

test('setPendingUpload stores enableLaneB when provided', () => {
  const files = [{ name: 'concept.pdf' }]
  const consumerBrief = {
    task_type: 'concept_test',
    product_concept_assets: ['High-protein yogurt'],
    copy_material: ['14g protein'],
    target_audience: ['working moms'],
    research_goal: 'Find resonance',
    enable_lane_b: true,
  }

  setPendingUpload({
    files,
    simulationRequirement: 'Run consumer propagation test',
    projectType: 'consumer_test',
    consumerBrief,
    enableLaneB: true,
  })

  const pending = getPendingUpload()
  assert.equal(pending.enableLaneB, true)
})
