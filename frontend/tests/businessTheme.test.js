import { describe, expect, test } from 'vitest'
import { existsSync, readFileSync } from 'node:fs'
import { join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { dirname } from 'node:path'

const root = join(dirname(fileURLToPath(import.meta.url)), '..')

function source(path) {
  return readFileSync(join(root, path), 'utf-8')
}

describe('precision research workbench theme', () => {
  test('global business theme is imported by the app entry', () => {
    const themePath = join(root, 'src/styles/businessTheme.css')

    expect(existsSync(themePath)).toBe(true)
    expect(source('src/main.ts')).toContain("import './styles/businessTheme.css'")
  })

  test('business theme defines shared workbench tokens and utilities', () => {
    const theme = source('src/styles/businessTheme.css')

    for (const token of [
      '--mc-bg-canvas',
      '--mc-surface',
      '--mc-text-primary',
      '--mc-text-secondary',
      '--mc-accent',
      '--mc-status-success',
      '--mc-radius-card',
      '--mc-shadow-card',
    ]) {
      expect(theme).toContain(token)
    }

    expect(theme).toContain('.business-card')
    expect(theme).toContain('.business-button')
    expect(theme).toContain('.technical-panel')
    expect(theme).toContain('.mono')
  })

  test('home workbench uses theme tokens and packaging material tray', () => {
    const home = source('src/views/Home.vue')

    expect(home).toContain('packaging-tray')
    expect(home).toContain('var(--mc-bg-canvas)')
    expect(home).toContain('var(--mc-surface)')
    expect(home).toContain('var(--mc-accent)')
  })

  test('flow header uses shared theme tokens instead of hard-coded console palette', () => {
    const header = source('src/components/BusinessFlowHeader.vue')

    expect(header).toContain('var(--mc-surface)')
    expect(header).toContain('var(--mc-border)')
    expect(header).toContain('var(--mc-status-success)')
    expect(header).toContain('var(--mc-accent)')
  })

  test('technical detail surfaces are covered by the shared theme layer', () => {
    const theme = source('src/styles/businessTheme.css')

    for (const selector of [
      '.graph-panel',
      '.history-database',
      '.evidence-graph-panel',
      '.path-graph',
      '.interview-workspace',
      '.focus-group-panel',
      '.consumer-research-workspace',
      '.consumer-branch-panel',
    ]) {
      expect(theme).toContain(selector)
    }

    expect(theme).toContain('--mc-technical-bg')
    expect(theme).toContain('--mc-technical-border')
    expect(theme).toContain('.technical-open')
  })
})
