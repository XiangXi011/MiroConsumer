import { test } from 'vitest'
import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

const step5Path = join(__dirname, '../src/components/Step5Interaction.vue')
const cardPath = join(__dirname, '../src/components/report/AgentProfileCard.vue')

const step5Content = readFileSync(step5Path, 'utf-8')

test('Step5Interaction delegates selected agent profile rendering', () => {
  assert.ok(existsSync(cardPath), 'AgentProfileCard component must exist')
  assert.ok(step5Content.includes("import AgentProfileCard from './report/AgentProfileCard.vue'"), 'Step5 must import AgentProfileCard')
  assert.ok(step5Content.includes('<AgentProfileCard'), 'Step5 must render AgentProfileCard')
  assert.ok(step5Content.includes(':agent="selectedAgent"'), 'Step5 must pass the selected agent')
  assert.ok(!step5Content.includes('class="agent-profile-card"'), 'profile card markup should live outside Step5Interaction')
  assert.ok(!step5Content.includes('showFullProfile'), 'profile expansion state should live inside AgentProfileCard')
})

test('AgentProfileCard owns selected agent profile rendering contract', () => {
  const cardContent = readFileSync(cardPath, 'utf-8')
  for (const token of [
    'class="agent-profile-card"',
    'showFullProfile',
    'agent.username',
    'agent.name',
    'agent.profession',
    'agent.bio',
    "t('step5.profileBio')",
    "t('step2.unknownProfession')",
  ]) {
    assert.ok(cardContent.includes(token), `missing agent profile card token: ${token}`)
  }
})
