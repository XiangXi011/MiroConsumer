import { describe, expect, test } from 'vitest'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import vitestConfig from '../vitest.config.js'

const frontendDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const packageJson = JSON.parse(
  fs.readFileSync(path.join(frontendDir, 'package.json'), 'utf8')
)

function resolveConfig(config) {
  return typeof config === 'function'
    ? config({ command: 'serve', mode: 'test' })
    : config
}

describe('Vitest frontend test runner configuration', () => {
  test('package scripts run Vitest and coverage', () => {
    expect(packageJson.scripts.test).toBe('vitest run')
    expect(packageJson.scripts['test:watch']).toBe('vitest')
    expect(packageJson.scripts['test:coverage']).toBe('vitest run --coverage')
    expect(packageJson.devDependencies.vitest).toBeDefined()
    expect(packageJson.devDependencies['@vitest/coverage-v8']).toBeDefined()
  })

  test('coverage output and thresholds are explicit', () => {
    const config = resolveConfig(vitestConfig)

    expect(config.test.environment).toBe('node')
    expect(config.test.include).toEqual(['tests/**/*.test.js'])
    expect(config.test.coverage.provider).toBe('v8')
    expect(config.test.coverage.reportsDirectory).toBe('./coverage')
    expect(config.test.coverage.reporter).toEqual(['text', 'lcov', 'json-summary'])
    expect(config.test.coverage.thresholds).toMatchObject({
      branches: 60,
      functions: 70,
      lines: 70,
      statements: 70,
    })
  })
})
