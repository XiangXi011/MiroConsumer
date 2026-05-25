import { test } from 'vitest'
import assert from 'node:assert/strict'

import { buildOntologyFormData } from '../src/api/ontologyFormData.ts'

test('buildOntologyFormData defaults project_type to consumer_test when payload omits projectType', () => {
  const fd = buildOntologyFormData({
    files: [{ name: 'brief.pdf' }],
    simulationRequirement: 'Test simulation',
  })

  assert.equal(fd.get('project_type'), 'consumer_test')
  assert.equal(fd.get('simulation_requirement'), 'Test simulation')
})

test('buildOntologyFormData respects explicit projectType from payload', () => {
  const fd = buildOntologyFormData({
    files: [],
    simulationRequirement: 'Run sim',
    projectType: 'consumer_test',
  })

  assert.equal(fd.get('project_type'), 'consumer_test')
})

test('buildOntologyFormData includes consumer_brief JSON when provided', () => {
  const brief = {
    task_type: 'concept_test',
    product_concept_assets: ['Protein yogurt'],
    target_audience: ['working moms'],
    research_goal: 'Find resonance',
  }

  const fd = buildOntologyFormData({
    files: [],
    simulationRequirement: 'Run sim',
    projectType: 'consumer_test',
    consumerBrief: brief,
    enableLaneB: true,
  })

  const parsed = JSON.parse(fd.get('consumer_brief'))
  assert.equal(parsed.task_type, 'concept_test')
  assert.equal(parsed.enable_lane_b, true)
})

test('buildOntologyFormData omits consumer_brief when not provided', () => {
  const fd = buildOntologyFormData({
    files: [],
    simulationRequirement: 'Run sim',
  })

  assert.equal(fd.get('consumer_brief'), null)
})

test('buildOntologyFormData appends files to form data', () => {
  const fileA = { name: 'a.pdf' }
  const fileB = { name: 'b.txt' }
  const fd = buildOntologyFormData({
    files: [fileA, fileB],
    simulationRequirement: 'Run sim',
  })

  const entries = Array.from(fd.entries()).filter(([key]) => key === 'files')
  assert.equal(entries.length, 2)
})

test('buildOntologyFormData carries packaging pdf and image assets into consumer test payload', () => {
  const packagingPdf = new File(['pdf'], 'shuke-packaging-front.pdf', { type: 'application/pdf' })
  const packagingImage = new File(['png'], 'shuke-packaging-shelf.png', { type: 'image/png' })
  const fd = buildOntologyFormData({
    files: [packagingPdf, packagingImage],
    simulationRequirement: 'Run packaging test',
    projectType: 'consumer_test',
    consumerBrief: {
      task_type: 'packaging_test',
      packaging_assets: ['Packaging asset files: shuke-packaging-front.pdf, shuke-packaging-shelf.png'],
      target_audience: ['daily toothpaste buyers'],
      research_goal: 'Evaluate whether the pack communicates gentle whitening',
    },
  })

  const files = fd.getAll('files')
  assert.equal(files.length, 2)
  assert.equal(files[0].name, 'shuke-packaging-front.pdf')
  assert.equal(files[1].name, 'shuke-packaging-shelf.png')

  const parsed = JSON.parse(fd.get('consumer_brief'))
  assert.equal(parsed.task_type, 'packaging_test')
  assert.deepEqual(parsed.packaging_assets, [
    'Packaging asset files: shuke-packaging-front.pdf, shuke-packaging-shelf.png',
  ])
})

test('buildOntologyFormData handles empty payload gracefully', () => {
  const fd = buildOntologyFormData()

  assert.equal(fd.get('project_type'), 'consumer_test')
  assert.equal(fd.get('simulation_requirement'), '')
  assert.deepEqual(fd.getAll('files'), [])
})
