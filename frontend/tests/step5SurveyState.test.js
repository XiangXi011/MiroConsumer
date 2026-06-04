import { test } from 'vitest'
import assert from 'node:assert/strict'
import { computed, ref } from 'vue'
import { existsSync, readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

import { useStep5SurveyState } from '../src/composables/useStep5SurveyState.ts'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

const step5Path = join(__dirname, '../src/components/Step5Interaction.vue')
const composablePath = join(__dirname, '../src/composables/useStep5SurveyState.ts')

test('useStep5SurveyState manages selected agents and survey state', () => {
  assert.ok(existsSync(composablePath), 'useStep5SurveyState composable must exist')

  const profiles = ref([{ username: 'Ava' }, { username: 'Bo' }, { username: 'Cy' }])
  const state = useStep5SurveyState({ profiles })

  assert.equal(state.selectedAgents.value.size, 0)
  assert.equal(state.surveyQuestion.value, '')
  assert.deepEqual(state.surveyResults.value, [])
  assert.equal(state.isSurveying.value, false)

  state.toggleAgentSelection(1)
  assert.deepEqual(Array.from(state.selectedAgents.value), [1])

  state.toggleAgentSelection(1)
  assert.deepEqual(Array.from(state.selectedAgents.value), [])

  state.selectAllAgents()
  assert.deepEqual(Array.from(state.selectedAgents.value), [0, 1, 2])

  profiles.value = [{ username: 'Only' }]
  state.selectAllAgents()
  assert.deepEqual(Array.from(state.selectedAgents.value), [0])

  state.clearAgentSelection()
  assert.equal(state.selectedAgents.value.size, 0)

  state.surveyQuestion.value = 'What proof matters?'
  state.surveyResults.value = [{ answer: 'Trust repair' }]
  state.isSurveying.value = true
  assert.equal(state.surveyQuestion.value, 'What proof matters?')
  assert.equal(state.surveyResults.value.length, 1)
  assert.equal(state.isSurveying.value, true)
})

test('useStep5SurveyState accepts computed profiles', () => {
  const sourceProfiles = ref([{ id: 1 }, { id: 2 }])
  const profiles = computed(() => sourceProfiles.value)
  const state = useStep5SurveyState({ profiles })
  state.selectAllAgents()
  assert.deepEqual(Array.from(state.selectedAgents.value), [0, 1])
})

test('Step5Interaction delegates survey state to useStep5SurveyState', () => {
  const step5Content = readFileSync(step5Path, 'utf-8')
  assert.ok(step5Content.includes("import { useStep5SurveyState } from '../composables/useStep5SurveyState'"), 'Step5 must import useStep5SurveyState')
  assert.ok(step5Content.includes('useStep5SurveyState({'), 'Step5 must initialize survey state via composable')
  for (const token of [
    'const selectedAgents = ref(new Set())',
    "const surveyQuestion = ref('')",
    'const surveyResults = ref([])',
    'const isSurveying = ref(false)',
    'const toggleAgentSelection = (idx)',
    'const selectAllAgents = ()',
    'const clearAgentSelection = ()',
  ]) {
    assert.ok(!step5Content.includes(token), `Step5 should not inline survey state token: ${token}`)
  }
})
