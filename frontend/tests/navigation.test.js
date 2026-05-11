import { describe, expect, test } from 'vitest'
import { existsSync, readFileSync } from 'node:fs'
import { join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { dirname } from 'node:path'

const root = join(dirname(fileURLToPath(import.meta.url)), '..')

function source(path) {
  return readFileSync(join(root, path), 'utf-8')
}

describe('process navigation', () => {
  test('router uses MainView for process route and does not reference stale Process view', () => {
    const router = source('src/router/index.js')
    const staleProcessPath = join(root, 'src/views/Process.vue')

    expect(router).toContain("import('../views/MainView.vue')")
    expect(router).not.toContain('Process.vue')
    expect(existsSync(staleProcessPath)).toBe(false)
  })

  test('Step1 creates simulation and navigates without alert-based errors', () => {
    const step1 = source('src/components/Step1GraphBuild.vue')

    expect(step1).toContain('createSimulation({')
    expect(step1).toContain("name: 'Simulation'")
    expect(step1).toContain('params: { simulationId: res.data.simulation_id }')
    expect(step1).not.toContain('alert(')
    expect(step1).toContain('createError')
  })
})
