import { defineConfig, mergeConfig } from 'vitest/config'

import viteConfig from './vite.config.js'

export default mergeConfig(
  viteConfig,
  defineConfig({
    test: {
      environment: 'node',
      include: ['tests/**/*.test.js'],
      coverage: {
        provider: 'v8',
        reportsDirectory: './coverage',
        reporter: ['text', 'lcov', 'json-summary'],
        thresholds: {
          branches: 60,
          functions: 70,
          lines: 70,
          statements: 70,
        },
      },
    },
  })
)
