import { test } from 'vitest'
import assert from 'node:assert/strict'
import { createConsumerApi } from '../src/api/consumerFactory.js'

function makeFakeService() {
  const calls = []
  let response = { _fake: true, result: 'ok' }

  const get = (url, config) => {
    calls.push({ method: 'get', url, config })
    return Promise.resolve(response)
  }

  const post = (url, data) => {
    calls.push({ method: 'post', url, data })
    return Promise.resolve(response)
  }

  return {
    get,
    post,
    calls,
    get fakeResponse() { return response },
    set fakeResponse(v) { response = v },
  }
}

test('getConsumerSummary uses GET /api/consumer/simulation/{id}/consumer-summary', async () => {
  const fake = makeFakeService()
  const api = createConsumerApi(fake)
  const result = await api.getConsumerSummary('sim-123')

  assert.equal(fake.calls.length, 1)
  assert.equal(fake.calls[0].method, 'get')
  assert.equal(fake.calls[0].url, '/api/consumer/simulation/sim-123/consumer-summary')
  assert.strictEqual(result, fake.fakeResponse)
})

test('channel summary APIs use Phase 6H consumer routes', async () => {
  const fake = makeFakeService()
  const api = createConsumerApi(fake)

  await api.getChannelSummary('sim-channel')
  await api.getChannelEvents('sim-channel')
  await api.getPropagationPaths('sim-channel')

  assert.deepStrictEqual(fake.calls.map(call => call.url), [
    '/api/consumer/simulations/sim-channel/channel-summary',
    '/api/consumer/simulations/sim-channel/channel-events',
    '/api/consumer/simulations/sim-channel/propagation-paths',
  ])
  assert.ok(fake.calls.every(call => call.method === 'get'))
})

test('Phase 6I interview APIs use fixed consumer routes', async () => {
  const fake = makeFakeService()
  const api = createConsumerApi(fake)
  const interviewPayload = { topic: 'proof', mode: 'snapshot' }
  const focusPayload = { topic: 'proof', moderator_goal: 'find disagreement' }

  await api.listRepresentativeAgents('sim-interview')
  await api.runConsumerInterview('sim-interview', interviewPayload)
  await api.runFocusGroup('sim-interview', focusPayload)
  await api.listInterviewHistory('sim-interview')
  await api.listFocusGroupHistory('sim-interview')

  assert.deepStrictEqual(fake.calls.map(call => call.method), ['get', 'post', 'post', 'get', 'get'])
  assert.deepStrictEqual(fake.calls.map(call => call.url), [
    '/api/consumer/simulations/sim-interview/representative-agents',
    '/api/consumer/simulations/sim-interview/interviews',
    '/api/consumer/simulations/sim-interview/focus-groups',
    '/api/consumer/simulations/sim-interview/interviews/history',
    '/api/consumer/simulations/sim-interview/focus-groups/history',
  ])
  assert.deepStrictEqual(fake.calls[1].data, interviewPayload)
  assert.deepStrictEqual(fake.calls[2].data, focusPayload)
})

test('listBranches uses GET /api/consumer/simulations/{id}/branches', async () => {
  const fake = makeFakeService()
  const api = createConsumerApi(fake)
  const result = await api.listBranches('sim-456')

  assert.equal(fake.calls.length, 1)
  assert.equal(fake.calls[0].method, 'get')
  assert.equal(fake.calls[0].url, '/api/consumer/simulations/sim-456/branches')
  assert.strictEqual(result, fake.fakeResponse)
})

test('createBranch posts payload to /api/consumer/simulations/{id}/branches', async () => {
  const fake = makeFakeService()
  const api = createConsumerApi(fake)
  const payload = { name: 'new-branch', fork_round: 3 }
  const result = await api.createBranch('sim-789', payload)

  assert.equal(fake.calls.length, 1)
  assert.equal(fake.calls[0].method, 'post')
  assert.equal(fake.calls[0].url, '/api/consumer/simulations/sim-789/branches')
  assert.deepStrictEqual(fake.calls[0].data, payload)
  assert.strictEqual(result, fake.fakeResponse)
})

test('getBranchComparison uses GET comparison route', async () => {
  const fake = makeFakeService()
  const api = createConsumerApi(fake)
  const result = await api.getBranchComparison('sim-1', 'branch-a')

  assert.equal(fake.calls.length, 1)
  assert.equal(fake.calls[0].method, 'get')
  assert.equal(fake.calls[0].url, '/api/consumer/simulations/sim-1/branches/branch-a/comparison')
  assert.strictEqual(result, fake.fakeResponse)
})

test('runBranch posts data to /resume route', async () => {
  const fake = makeFakeService()
  const api = createConsumerApi(fake)
  const data = { max_rounds: 10 }
  const result = await api.runBranch('sim-2', 'branch-b', data)

  assert.equal(fake.calls.length, 1)
  assert.equal(fake.calls[0].method, 'post')
  assert.equal(fake.calls[0].url, '/api/consumer/simulations/sim-2/branches/branch-b/resume')
  assert.deepStrictEqual(fake.calls[0].data, data)
  assert.strictEqual(result, fake.fakeResponse)
})

test('runBranch defaults data to empty object when omitted', async () => {
  const fake = makeFakeService()
  const api = createConsumerApi(fake)
  const result = await api.runBranch('sim-2', 'branch-b')

  assert.equal(fake.calls.length, 1)
  assert.equal(fake.calls[0].method, 'post')
  assert.deepStrictEqual(fake.calls[0].data, {})
  assert.strictEqual(result, fake.fakeResponse)
})

test('getBranchStatus uses GET status route', async () => {
  const fake = makeFakeService()
  const api = createConsumerApi(fake)
  const result = await api.getBranchStatus('sim-3', 'branch-c')

  assert.equal(fake.calls.length, 1)
  assert.equal(fake.calls[0].method, 'get')
  assert.equal(fake.calls[0].url, '/api/consumer/simulations/sim-3/branches/branch-c/status')
  assert.strictEqual(result, fake.fakeResponse)
})

test('listInterventions with branchId passes { params: { branch_id: branchId } }', async () => {
  const fake = makeFakeService()
  const api = createConsumerApi(fake)
  const result = await api.listInterventions('sim-4', 'branch-d')

  assert.equal(fake.calls.length, 1)
  assert.equal(fake.calls[0].method, 'get')
  assert.equal(fake.calls[0].url, '/api/consumer/simulations/sim-4/interventions')
  assert.deepStrictEqual(fake.calls[0].config, { params: { branch_id: 'branch-d' } })
  assert.strictEqual(result, fake.fakeResponse)
})

test('listInterventions without branchId passes { params: {} }', async () => {
  const fake = makeFakeService()
  const api = createConsumerApi(fake)
  const result = await api.listInterventions('sim-4')

  assert.equal(fake.calls.length, 1)
  assert.equal(fake.calls[0].method, 'get')
  assert.equal(fake.calls[0].url, '/api/consumer/simulations/sim-4/interventions')
  assert.deepStrictEqual(fake.calls[0].config, { params: {} })
  assert.strictEqual(result, fake.fakeResponse)
})

test('addIntervention posts to branch interventions route', async () => {
  const fake = makeFakeService()
  const api = createConsumerApi(fake)
  const payload = { intervention_type: 'boost', payload: {} }
  const result = await api.addIntervention('sim-5', 'branch-e', payload)

  assert.equal(fake.calls.length, 1)
  assert.equal(fake.calls[0].method, 'post')
  assert.equal(fake.calls[0].url, '/api/consumer/simulations/sim-5/branches/branch-e/interventions')
  assert.deepStrictEqual(fake.calls[0].data, payload)
  assert.strictEqual(result, fake.fakeResponse)
})

test('exportResearchAsset posts payload to /api/consumer/research-assets/export', async () => {
  const fake = makeFakeService()
  const api = createConsumerApi(fake)
  const payload = { project_id: 'proj-1', name: 'asset' }
  const result = await api.exportResearchAsset(payload)

  assert.equal(fake.calls.length, 1)
  assert.equal(fake.calls[0].method, 'post')
  assert.equal(fake.calls[0].url, '/api/consumer/research-assets/export')
  assert.deepStrictEqual(fake.calls[0].data, payload)
  assert.strictEqual(result, fake.fakeResponse)
})

test('listResearchAssets uses params { project_id: projectId }', async () => {
  const fake = makeFakeService()
  const api = createConsumerApi(fake)
  const result = await api.listResearchAssets('proj-2')

  assert.equal(fake.calls.length, 1)
  assert.equal(fake.calls[0].method, 'get')
  assert.equal(fake.calls[0].url, '/api/consumer/research-assets')
  assert.deepStrictEqual(fake.calls[0].config, { params: { project_id: 'proj-2' } })
  assert.strictEqual(result, fake.fakeResponse)
})

test('getResearchAsset uses GET /api/consumer/research-assets/{id}', async () => {
  const fake = makeFakeService()
  const api = createConsumerApi(fake)
  const result = await api.getResearchAsset('asset-1')

  assert.equal(fake.calls.length, 1)
  assert.equal(fake.calls[0].method, 'get')
  assert.equal(fake.calls[0].url, '/api/consumer/research-assets/asset-1')
  assert.strictEqual(result, fake.fakeResponse)
})

test('compareResearchSnapshots posts payload to /api/consumer/comparisons', async () => {
  const fake = makeFakeService()
  const api = createConsumerApi(fake)
  const payload = { mode: 'run_vs_run', left_simulation_id: 's1', right_simulation_id: 's2' }
  const result = await api.compareResearchSnapshots(payload)

  assert.equal(fake.calls.length, 1)
  assert.equal(fake.calls[0].method, 'post')
  assert.equal(fake.calls[0].url, '/api/consumer/comparisons')
  assert.deepStrictEqual(fake.calls[0].data, payload)
  assert.strictEqual(result, fake.fakeResponse)
})

test('listComparisons uses params { project_id: projectId }', async () => {
  const fake = makeFakeService()
  const api = createConsumerApi(fake)
  const result = await api.listComparisons('proj-3')

  assert.equal(fake.calls.length, 1)
  assert.equal(fake.calls[0].method, 'get')
  assert.equal(fake.calls[0].url, '/api/consumer/comparisons')
  assert.deepStrictEqual(fake.calls[0].config, { params: { project_id: 'proj-3' } })
  assert.strictEqual(result, fake.fakeResponse)
})

test('getComparison uses GET /api/consumer/comparisons/{id}', async () => {
  const fake = makeFakeService()
  const api = createConsumerApi(fake)
  const result = await api.getComparison('cmp-1')

  assert.equal(fake.calls.length, 1)
  assert.equal(fake.calls[0].method, 'get')
  assert.equal(fake.calls[0].url, '/api/consumer/comparisons/cmp-1')
  assert.strictEqual(result, fake.fakeResponse)
})

test('runConsumerResearchAction posts to /api/consumer/simulations/{id}/research-actions', async () => {
  const fake = makeFakeService()
  const api = createConsumerApi(fake)
  const payload = { action_type: 'deep_dive_conclusion', target: { kind: 'section', id: 'section_1' } }
  const result = await api.runConsumerResearchAction('sim-7', payload)

  assert.equal(fake.calls.length, 1)
  assert.equal(fake.calls[0].method, 'post')
  assert.equal(fake.calls[0].url, '/api/consumer/simulations/sim-7/research-actions')
  assert.deepStrictEqual(fake.calls[0].data, payload)
  assert.strictEqual(result, fake.fakeResponse)
})

test('fake service return value is returned to caller without mutation', async () => {
  const fake = makeFakeService()
  fake.fakeResponse = { custom: 'value', nested: { arr: [1, 2, 3] } }
  const api = createConsumerApi(fake)

  const r1 = await api.getConsumerSummary('s')
  assert.deepStrictEqual(r1, fake.fakeResponse)

  const r2 = await api.createBranch('s', {})
  assert.deepStrictEqual(r2, fake.fakeResponse)
})
