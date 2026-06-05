import { test } from 'vitest'
import assert from 'node:assert/strict'

import { deriveReportRenderState } from '../src/utils/reportContent.ts'

test('deriveReportRenderState renders completed markdown report without agent logs', () => {
  const state = deriveReportRenderState({
    status: 'completed',
    report_context: {
      test_type_profile: {
        report_strategy: {
          report_title: 'Fallback strategy title',
        },
      },
    },
    markdown_content: [
      '# Consumer propagation report',
      '',
      'Executive summary line one.',
      'Executive summary line two.',
      '',
      '## Path diagnosis',
      '',
      '| Path | Entry | Breakpoint |',
      '| --- | --- | --- |',
      '| Social post -> comments -> product detail | Campaign story | Evidence handoff is weak |',
      '',
      '## Channel actions',
      '',
      'Pinned comments should connect claim, audience, and safety evidence.',
    ].join('\n'),
  })

  assert.equal(state.isComplete, true)
  assert.equal(state.outline.title, 'Consumer propagation report')
  assert.equal(
    state.outline.summary,
    'Executive summary line one.\nExecutive summary line two.'
  )
  assert.deepEqual(state.outline.sections.map(section => section.title), [
    'Path diagnosis',
    'Channel actions',
  ])
  assert.match(state.generatedSections[1], /Path diagnosis/)
  assert.match(state.generatedSections[1], /Social post/)
  assert.match(state.generatedSections[2], /Pinned comments/)
})

test('deriveReportRenderState falls back to report strategy title without h1', () => {
  const state = deriveReportRenderState({
    status: 'ready',
    report_context: {
      test_type_profile: {
        report_strategy: {
          report_title: 'Strategy title',
        },
      },
    },
    markdown_content: [
      'Summary only report.',
      '',
      '## Evidence',
      'The source evidence is sufficient.',
    ].join('\n'),
  })

  assert.equal(state.isComplete, true)
  assert.equal(state.outline.title, 'Strategy title')
  assert.equal(state.outline.sections[0].title, 'Evidence')
})

test('deriveReportRenderState returns empty state for pending report detail', () => {
  const state = deriveReportRenderState({
    status: 'pending',
    markdown_content: '# Waiting',
  })

  assert.equal(state.isComplete, false)
  assert.equal(state.outline, null)
  assert.deepEqual(state.generatedSections, {})
})
