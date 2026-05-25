import { describe, expect, test } from 'vitest'
import { readFileSync } from 'node:fs'
import { join, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = join(dirname(fileURLToPath(import.meta.url)), '..')

describe('router route resolution', () => {
  test('direct simulation run links have a dedicated run workspace route', () => {
    const routerSource = readFileSync(join(root, 'src/router/index.ts'), 'utf-8')
    const runRouteIndex = routerSource.indexOf("path: '/simulation/:simulationId/start'")
    const setupRouteIndex = routerSource.indexOf("path: '/simulation/:simulationId'")

    expect(runRouteIndex).toBeGreaterThan(-1)
    expect(routerSource).toContain("name: 'SimulationRun'")
    expect(routerSource).toContain("component: () => import('../views/SimulationRunView.vue')")
    expect(runRouteIndex).toBeGreaterThan(setupRouteIndex)
  })
})
