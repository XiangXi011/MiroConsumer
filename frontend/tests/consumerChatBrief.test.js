import { test } from 'vitest'
import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

const step5Path = join(__dirname, '../src/components/Step5Interaction.vue')
const briefPath = join(__dirname, '../src/components/report/ConsumerChatBrief.vue')

const step5Content = readFileSync(step5Path, 'utf-8')

test('Step5Interaction delegates consumer chat brief rendering', () => {
  assert.ok(existsSync(briefPath), 'ConsumerChatBrief component must exist')
  assert.ok(step5Content.includes("import ConsumerChatBrief from './report/ConsumerChatBrief.vue'"), 'Step5 must import ConsumerChatBrief')
  assert.ok(step5Content.includes('<ConsumerChatBrief'), 'Step5 must render ConsumerChatBrief')
  assert.ok(step5Content.includes(':quick-prompts="consumerQuickPrompts"'), 'Step5 must pass quick prompts')
  assert.ok(step5Content.includes(':voc-highlights="consumerVocHighlights"'), 'Step5 must pass VOC highlights')
  assert.ok(step5Content.includes(':source-catalog="consumerSourceCatalog"'), 'Step5 must pass source catalog')
  assert.ok(step5Content.includes(':enriched-findings="consumerEnrichedFindings"'), 'Step5 must pass enriched findings')
  assert.ok(step5Content.includes('@apply-prompt="applyQuickPrompt"'), 'Step5 must keep quick prompt handling')
  assert.ok(!step5Content.includes('class="consumer-chat-brief"'), 'consumer brief markup should live outside Step5Interaction')
})

test('ConsumerChatBrief owns prompts, VOC highlights, and source strip rendering', () => {
  const briefContent = readFileSync(briefPath, 'utf-8')
  for (const token of [
    'class="consumer-chat-brief"',
    'quickPrompts.length > 0',
    'vocHighlights.length > 0',
    'sourceCatalog.slice(0, 4)',
    'enrichedFindings.length',
    "emit('apply-prompt', prompt)",
    "t('consumer.recommendedFollowUps')",
    "t('consumer.vocHighlights')",
    "t('consumer.sourcesUsed')",
    "t('consumer.evidenceItems')",
  ]) {
    assert.ok(briefContent.includes(token), `missing consumer chat brief token: ${token}`)
  }
})
