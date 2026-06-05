import { test } from 'vitest'
import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { ref } from 'vue'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

const step5Path = join(__dirname, '../src/components/Step5Interaction.vue')
const composablePath = join(__dirname, '../src/composables/useStep5ReportLoaders.ts')

function createHarness(overrides = {}) {
  const logs = []
  const appliedLogs = []
  const setProfilesCalls = []
  const reportId = ref('report-1')
  const simulationId = ref('sim-1')
  const profiles = ref([])

  const t = (key, params = {}) => `${key}:${JSON.stringify(params)}`

  const api = {
    getReport: async id => ({ success: true, data: { id } }),
    getAgentLog: async id => ({ success: true, data: { logs: [{ action: 'section_complete', report_id: id }] } }),
    getSimulationProfilesRealtime: async id => ({ success: true, data: { profiles: [{ username: `profile-${id}` }] } }),
    ...overrides.api,
  }

  return {
    reportId,
    simulationId,
    profiles,
    logs,
    appliedLogs,
    setProfilesCalls,
    t,
    api,
    addLog: message => logs.push(message),
    applyReportLogs: logs => appliedLogs.push(...logs),
    setProfiles: nextProfiles => {
      profiles.value = nextProfiles
      setProfilesCalls.push(nextProfiles)
    },
  }
}

test('useStep5ReportLoaders loads report logs and simulation profiles', async () => {
  assert.ok(existsSync(composablePath), 'useStep5ReportLoaders composable must exist')

  const { useStep5ReportLoaders } = await import('../src/composables/useStep5ReportLoaders.ts')
  const harness = createHarness()
  const loaders = useStep5ReportLoaders(harness)

  await loaders.loadReportData()
  assert.equal(harness.appliedLogs.length, 1)
  assert.equal(harness.appliedLogs[0].report_id, 'report-1')
  assert.deepEqual(harness.logs, [
    'log.loadReportData:{"id":"report-1"}',
    'log.reportDataLoaded:{}',
  ])

  await loaders.loadProfiles()
  assert.deepEqual(harness.profiles.value, [{ username: 'profile-sim-1' }])
  assert.deepEqual(harness.setProfilesCalls, [[{ username: 'profile-sim-1' }]])
  assert.equal(harness.logs.at(-1), 'log.loadedProfiles:{"count":1}')
})

test('useStep5ReportLoaders skips missing ids and records failures', async () => {
  const { useStep5ReportLoaders } = await import('../src/composables/useStep5ReportLoaders.ts')
  let reportCalls = 0
  let profileCalls = 0
  const harness = createHarness({
    api: {
      getReport: async () => {
        reportCalls += 1
        throw new Error('report down')
      },
      getAgentLog: async () => ({ success: true, data: { logs: [] } }),
      getSimulationProfilesRealtime: async () => {
        profileCalls += 1
        throw new Error('profiles down')
      },
    },
  })
  const loaders = useStep5ReportLoaders(harness)

  harness.reportId.value = ''
  harness.simulationId.value = ''
  await loaders.loadReportData()
  await loaders.loadAgentLogs()
  await loaders.loadProfiles()
  assert.equal(reportCalls, 0)
  assert.equal(profileCalls, 0)
  assert.deepEqual(harness.logs, [])

  harness.reportId.value = 'report-2'
  harness.simulationId.value = 'sim-2'
  await loaders.loadReportData()
  await loaders.loadProfiles()
  assert.equal(reportCalls, 1)
  assert.equal(profileCalls, 1)
  assert.deepEqual(harness.logs, [
    'log.loadReportData:{"id":"report-2"}',
    'log.loadReportFailed:{"error":"report down"}',
    'log.loadProfilesFailed:{"error":"profiles down"}',
  ])
})

test('Step5Interaction delegates report loaders to useStep5ReportLoaders', () => {
  const step5Content = readFileSync(step5Path, 'utf-8')
  assert.ok(step5Content.includes("import { useStep5ReportLoaders } from '../composables/useStep5ReportLoaders'"), 'Step5 must import useStep5ReportLoaders')
  assert.ok(step5Content.includes('useStep5ReportLoaders({'), 'Step5 must initialize report loaders via composable')

  for (const token of [
    'getReport, getAgentLog',
    'getSimulationProfilesRealtime',
    'const loadReportData = async ()',
    'const loadAgentLogs = async ()',
    'const loadProfiles = async ()',
  ]) {
    assert.ok(!step5Content.includes(token), `Step5 should not inline report loader token: ${token}`)
  }
})
