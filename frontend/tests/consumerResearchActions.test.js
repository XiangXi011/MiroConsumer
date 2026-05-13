import { test } from 'vitest'
import assert from 'node:assert/strict'
import {
  CONSUMER_RESEARCH_ACTIONS,
  buildConsumerResearchActionPayload,
  normalizeConsumerResearchActionResponse,
  isPhase6IInterviewHandoff,
  getConsumerInterviewHandoffStorageKey,
  saveConsumerInterviewHandoff,
  loadConsumerInterviewHandoff,
  clearConsumerInterviewHandoff,
} from '../src/utils/consumerResearchActions.ts'

test('CONSUMER_RESEARCH_ACTIONS contains all five expected values', () => {
  assert.equal(CONSUMER_RESEARCH_ACTIONS.DEEP_DIVE_CONCLUSION, 'deep_dive_conclusion')
  assert.equal(CONSUMER_RESEARCH_ACTIONS.EXPLAIN_PROPAGATION_PATH, 'explain_propagation_path')
  assert.equal(CONSUMER_RESEARCH_ACTIONS.VERIFY_EVIDENCE, 'verify_evidence')
  assert.equal(CONSUMER_RESEARCH_ACTIONS.INTERVIEW_CONSUMERS, 'interview_consumers')
  assert.equal(CONSUMER_RESEARCH_ACTIONS.COMPARE_BRANCH_DELTA, 'compare_branch_delta')
})

// --- deep_dive_conclusion ---
test('buildConsumerResearchActionPayload for deep_dive_conclusion', () => {
  const payload = buildConsumerResearchActionPayload(
    CONSUMER_RESEARCH_ACTIONS.DEEP_DIVE_CONCLUSION,
    {
      reportId: 'r1',
      sectionIndex: 2,
      sectionTitle: 'Findings',
      sectionContent: 'content',
      branchId: 'b1',
      claim: 'c1',
    }
  )
  assert.equal(payload.action_type, 'deep_dive_conclusion')
  assert.deepStrictEqual(payload.target, { kind: 'section', id: 'section_2', text: 'Findings' })
  assert.equal(payload.context.report_id, 'r1')
  assert.equal(payload.context.section_index, 2)
  assert.equal(payload.context.branch_id, 'b1')
  assert.equal(payload.context.claim, 'c1')
})

// --- explain_propagation_path ---
test('buildConsumerResearchActionPayload for explain_propagation_path', () => {
  const payload = buildConsumerResearchActionPayload(
    CONSUMER_RESEARCH_ACTIONS.EXPLAIN_PROPAGATION_PATH,
    {
      reportId: 'r2',
      sectionIndex: 3,
      sectionTitle: 'Propagation',
      sectionContent: 'content',
      branchId: '',
      claim: '',
    }
  )
  assert.equal(payload.action_type, 'explain_propagation_path')
  assert.deepStrictEqual(payload.target, { kind: 'section', id: 'section_3', text: 'Propagation' })
  assert.equal(payload.context.claim, 'Propagation')
})

// --- verify_evidence ---
test('buildConsumerResearchActionPayload for verify_evidence', () => {
  const payload = buildConsumerResearchActionPayload(
    CONSUMER_RESEARCH_ACTIONS.VERIFY_EVIDENCE,
    {
      reportId: 'r3',
      sectionIndex: 1,
      sectionTitle: 'Evidence',
      sectionContent: 'content',
      branchId: 'b3',
      claim: 'claim text',
    }
  )
  assert.equal(payload.action_type, 'verify_evidence')
  assert.deepStrictEqual(payload.target, { kind: 'section', id: 'section_1', text: 'Evidence' })
  assert.equal(payload.context.claim, 'claim text')
})

// --- interview_consumers without findingId ---
test('buildConsumerResearchActionPayload for interview_consumers without findingId targets section', () => {
  const payload = buildConsumerResearchActionPayload(
    CONSUMER_RESEARCH_ACTIONS.INTERVIEW_CONSUMERS,
    {
      reportId: 'r4',
      sectionIndex: 2,
      sectionTitle: 'Consumers',
      sectionContent: 'content',
      branchId: 'b4',
      claim: '',
    }
  )
  assert.equal(payload.action_type, 'interview_consumers')
  assert.deepStrictEqual(payload.target, { kind: 'section', id: 'section_2', text: 'Consumers' })
})

// --- interview_consumers with findingId ---
test('buildConsumerResearchActionPayload for interview_consumers with findingId targets finding', () => {
  const payload = buildConsumerResearchActionPayload(
    CONSUMER_RESEARCH_ACTIONS.INTERVIEW_CONSUMERS,
    {
      reportId: 'r5',
      sectionIndex: 3,
      sectionTitle: 'Findings',
      sectionContent: 'content',
      branchId: 'b5',
      claim: 'c5',
      findingId: 'f99',
    }
  )
  assert.equal(payload.action_type, 'interview_consumers')
  assert.deepStrictEqual(payload.target, { kind: 'finding', id: 'f99' })
})

// --- compare_branch_delta ---
test('buildConsumerResearchActionPayload for compare_branch_delta includes branch_id in context', () => {
  const payload = buildConsumerResearchActionPayload(
    CONSUMER_RESEARCH_ACTIONS.COMPARE_BRANCH_DELTA,
    {
      reportId: 'r6',
      sectionIndex: 4,
      sectionTitle: 'Branch Comparison',
      sectionContent: 'content',
      branchId: 'branch-x',
      claim: '',
    }
  )
  assert.equal(payload.action_type, 'compare_branch_delta')
  assert.equal(payload.context.branch_id, 'branch-x')
})

// --- normalizeConsumerResearchActionResponse ---
test('normalizeConsumerResearchActionResponse unwraps {success,data} wrapper', () => {
  const wrapped = { success: true, data: { title: 'result' } }
  assert.deepStrictEqual(normalizeConsumerResearchActionResponse(wrapped), { title: 'result' })
})

test('normalizeConsumerResearchActionResponse returns object without success key as-is', () => {
  const raw = { title: 'result' }
  assert.deepStrictEqual(normalizeConsumerResearchActionResponse(raw), { title: 'result' })
})

test('normalizeConsumerResearchActionResponse returns non-object input as-is', () => {
  assert.equal(normalizeConsumerResearchActionResponse('hello'), 'hello')
})

// --- isPhase6IInterviewHandoff ---
test('isPhase6IInterviewHandoff true only for phase6i_interview handoff_type', () => {
  assert.equal(
    isPhase6IInterviewHandoff({ handoff: { handoff_type: 'phase6i_interview' } }),
    true
  )
  assert.equal(
    isPhase6IInterviewHandoff({ handoff: { handoff_type: 'other' } }),
    false
  )
  assert.equal(isPhase6IInterviewHandoff({ handoff: {} }), false)
  assert.equal(isPhase6IInterviewHandoff({}), false)
  assert.equal(isPhase6IInterviewHandoff(null), false)
})

// --- Storage helpers in node environment (window undefined) ---
test('getConsumerInterviewHandoffStorageKey returns expected key', () => {
  assert.equal(
    getConsumerInterviewHandoffStorageKey('sim-123'),
    'miroconsumer:consumer:interview-handoff:sim-123'
  )
})

test('saveConsumerInterviewHandoff does not throw when window is undefined', () => {
  assert.doesNotThrow(() => saveConsumerInterviewHandoff('sim-1', { foo: 'bar' }))
})

test('loadConsumerInterviewHandoff returns null when window is undefined', () => {
  assert.equal(loadConsumerInterviewHandoff('sim-1'), null)
})

test('clearConsumerInterviewHandoff does not throw when window is undefined', () => {
  assert.doesNotThrow(() => clearConsumerInterviewHandoff('sim-1'))
})

// --- Source-level assertions for Vue component labels ---
import { readFileSync } from 'fs'
import { fileURLToPath } from 'url'
import { dirname, join } from 'path'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

test('ConsumerResearchActionBar.vue contains all five action labels', () => {
  const path = join(__dirname, '../src/components/consumer/ConsumerResearchActionBar.vue')
  const content = readFileSync(path, 'utf-8')
  assert.ok(content.includes('深挖结论'), 'missing 深挖结论 label')
  assert.ok(content.includes('查看传播路径'), 'missing 查看传播路径 label')
  assert.ok(content.includes('查看证据'), 'missing 查看证据 label')
  assert.ok(content.includes('追问消费者'), 'missing 追问消费者 label')
  assert.ok(content.includes('比较分支差异'), 'missing 比较分支差异 label')
})

test('ConsumerInsightDrawer.vue contains handoff button label', () => {
  const path = join(__dirname, '../src/components/consumer/ConsumerInsightDrawer.vue')
  const content = readFileSync(path, 'utf-8')
  assert.ok(content.includes('进入消费者追问工作台'), 'missing handoff button label')
})

test('ConsumerInsightDrawer.vue reads audit fields from evidence object', () => {
  const path = join(__dirname, '../src/components/consumer/ConsumerInsightDrawer.vue')
  const content = readFileSync(path, 'utf-8')
  assert.ok(content.includes('result.evidence.source_count'), 'source_count must come from evidence')
  assert.ok(content.includes('result.evidence.simulation_quote_count'), 'simulation_quote_count must come from evidence')
  assert.ok(content.includes('result.evidence.gatekeeping_status'), 'gatekeeping_status must come from evidence')
  assert.ok(!content.includes('result.source_count'), 'drawer must not read source_count from top-level result')
  assert.ok(!content.includes('result.simulation_quote_count'), 'drawer must not read simulation_quote_count from top-level result')
  assert.ok(!content.includes('result.gatekeeping_status'), 'drawer must not read gatekeeping_status from top-level result')
})

test('ConsumerInsightDrawer.vue does not contain interview/focus group result rendering labels', () => {
  const path = join(__dirname, '../src/components/consumer/ConsumerInsightDrawer.vue')
  const content = readFileSync(path, 'utf-8')
  // Should not render interview results
  assert.ok(!content.includes('Interview Results'), 'should not contain Interview Results')
  assert.ok(!content.includes('interview_results'), 'should not contain interview_results')
  // Should not render focus group results
  assert.ok(!content.includes('Focus Group'), 'should not contain Focus Group')
  assert.ok(!content.includes('focus_group'), 'should not contain focus_group')
})
