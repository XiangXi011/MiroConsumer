import { describe, expect, test } from 'vitest'
import { readFileSync } from 'node:fs'
import { join, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = join(dirname(fileURLToPath(import.meta.url)), '..')

function source(path) {
  return readFileSync(join(root, path), 'utf-8')
}

describe('flow route shell theme', () => {
  const flowViews = [
    'src/views/MainView.vue',
    'src/views/SimulationView.vue',
    'src/views/SimulationRunView.vue',
    'src/views/ReportView.vue',
    'src/views/InteractionView.vue',
  ]

  test('all flow routes use the shared business header and technical toggle', () => {
    for (const viewPath of flowViews) {
      const view = source(viewPath)

      expect(view).toContain('<BusinessFlowHeader')
      expect(view).toContain(':show-technical="showTechnical"')
      expect(view).toContain("@toggle-technical=\"showTechnical = !showTechnical\"")
      expect(view).toContain("v-if=\"showTechnical\"")
      expect(view).toContain("class=\"panel-wrapper left\"")
    }
  })

  test('global theme owns route shell and mobile technical-open layout', () => {
    const theme = source('src/styles/businessTheme.css')

    expect(theme).toContain('#app .content-area.technical-open')
    expect(theme).toContain('#app .panel-wrapper.left')
    expect(theme).toContain('max-height: 46vh')
  })

  test('simulation run summary uses props for configured round count', () => {
    const component = source('src/components/Step3Simulation.vue')

    expect(component).toContain("runStatus.value.total_rounds || props.maxRounds || '-'")
    expect(component).not.toContain('maxRounds.value')
  })
})
