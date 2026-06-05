import { describe, test } from 'vitest'
import assert from 'node:assert/strict'

import {
  buildReportWorkflowSummary,
  formatElapsedTime,
  formatParams,
  formatResultSize,
  formatTime,
  getActionLabel,
  getConnectorClass,
  getLogLevelClass,
  getTimelineItemClass,
  truncateText,
} from '../src/utils/reportWorkflow.ts'

describe('report workflow helpers', () => {
  test('buildReportWorkflowSummary derives active section state', () => {
    const summary = buildReportWorkflowSummary({
      isComplete: false,
      reportOutline: {
        sections: [
          { title: 'Market evidence' },
          { title: 'Channel actions' },
        ],
      },
      generatedSections: { 1: 'done' },
      currentSectionIndex: null,
      agentLogs: [{ action: 'planning_complete' }, { action: 'tool_call' }],
    })

    assert.equal(summary.statusClass, 'processing')
    assert.equal(summary.statusText, 'Generating...')
    assert.equal(summary.totalSections, 2)
    assert.equal(summary.completedSections, 1)
    assert.equal(summary.progressPercent, 50)
    assert.equal(summary.totalToolCalls, 1)
    assert.equal(summary.activeSectionIndex, 2)
    assert.equal(summary.activeStep.key, 'section-2')
    assert.deepEqual(summary.workflowSteps.map(step => [step.key, step.status]), [
      ['planning', 'done'],
      ['section-1', 'done'],
      ['section-2', 'active'],
      ['complete', 'todo'],
    ])
  })

  test('buildReportWorkflowSummary marks finalizing and complete states', () => {
    const finalizing = buildReportWorkflowSummary({
      isComplete: false,
      reportOutline: { sections: [{ title: 'Only section' }] },
      generatedSections: { 1: 'done' },
      currentSectionIndex: null,
      agentLogs: [{ action: 'planning_complete' }],
    })

    assert.equal(finalizing.activeStep.key, 'complete')
    assert.equal(finalizing.activeStep.status, 'active')
    assert.equal(finalizing.activeStep.meta, 'FINALIZING')

    const complete = buildReportWorkflowSummary({
      isComplete: true,
      reportOutline: { sections: [{ title: 'Only section' }] },
      generatedSections: { 1: 'done' },
      currentSectionIndex: null,
      agentLogs: [],
    })

    assert.equal(complete.statusClass, 'completed')
    assert.equal(complete.statusText, 'Completed')
    assert.equal(complete.activeSectionIndex, null)
    assert.equal(complete.workflowSteps.at(-1).status, 'done')
  })

  test('formats timeline metadata and classes', () => {
    assert.equal(formatElapsedTime(null, []), '0s')
    assert.equal(formatElapsedTime(new Date('2026-01-01T00:00:00Z'), [{ elapsed_seconds: 75.4 }]), '1m 15s')
    assert.equal(formatResultSize(999), '999 chars')
    assert.equal(formatResultSize(1530), '1.5k chars')
    assert.equal(truncateText('abcdef', 3), 'abc...')
    assert.equal(formatParams({ a: 1 }), '{\n  "a": 1\n}')
    assert.equal(formatParams({ toJSON() { throw new Error('boom') } }), '[object Object]')
    assert.equal(getActionLabel('section_complete'), 'Section Done')
    assert.equal(getActionLabel('custom_action'), 'custom_action')
    assert.equal(getLogLevelClass('ERROR failed'), 'error')
    assert.equal(getLogLevelClass('警告 check'), 'warning')
    assert.equal(getLogLevelClass('INFO ok'), '')
    assert.equal(formatTime('bad-date'), '')

    assert.deepEqual(getTimelineItemClass({ action: 'tool_result' }, 1, 2, false), {
      'node--active': true,
      'node--done': false,
      'node--muted': false,
      'node--tool': true,
    })
    assert.equal(getConnectorClass({ action: 'section_complete' }, 0, 2, true), 'dot-done')
    assert.equal(getConnectorClass({ action: 'tool_call' }, 0, 2, false), 'dot-muted')
  })

})
