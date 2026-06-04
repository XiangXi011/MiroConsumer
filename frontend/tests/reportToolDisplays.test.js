import { createSSRApp, h } from 'vue'
import { renderToString } from '@vue/server-renderer'
import { createI18n } from 'vue-i18n'
import { test } from 'vitest'
import assert from 'node:assert/strict'

import {
  InterviewDisplay,
  QuickSearchDisplay,
} from '../src/components/report/ReportToolDisplays.ts'

function makeI18n() {
  return createI18n({
    legacy: false,
    locale: 'en',
    messages: {
      en: {
        step4: {
          searchLabel: 'Query',
          tabFacts: 'Facts ({count})',
          tabEdges: 'Edges ({count})',
          tabNodes: 'Nodes ({count})',
          panelSearchResults: 'Search Results',
          totalCount: 'Total {count}',
          panelRelatedEdges: 'Related Edges',
          panelRelatedNodes: 'Related Nodes',
          totalEntityCount: 'Total {count}',
          emptySearchResults: 'No results',
          collapse: 'Collapse',
          expandAll: 'Expand all ({count})',
          world1: 'World 1',
          world2: 'World 2',
        },
      },
    },
  })
}

test('QuickSearchDisplay renders quick search facts and graph context', async () => {
  const app = createSSRApp({
    render() {
      return h(QuickSearchDisplay, {
        resultLength: 1530,
        result: {
          query: 'buyer hesitation',
          count: 2,
          facts: ['Proof detail matters.', 'Price pressure is high.'],
          edges: [{ source: 'Buyer', relation: 'cares_about', target: 'Evidence' }],
          nodes: [{ name: 'Buyer', type: 'Persona' }],
        },
      })
    },
  })

  app.use(makeI18n())

  const html = await renderToString(app)

  assert.match(html, /Quick Search/)
  assert.match(html, /buyer hesitation/)
  assert.match(html, /1\.5k chars/)
  assert.match(html, /Facts \(2\)/)
  assert.match(html, /Edges \(1\)/)
  assert.match(html, /Nodes \(1\)/)
  assert.match(html, /Proof detail matters\./)
})

test('InterviewDisplay renders dual platform answers after extraction', async () => {
  const app = createSSRApp({
    render() {
      return h(InterviewDisplay, {
        resultLength: 2200,
        result: {
          topic: 'purchase decision',
          successCount: 1,
          totalCount: 2,
          interviews: [{
            name: 'AgentA',
            role: 'Parent',
            title: 'Primary buyer',
            bio: 'Shops weekly',
            selectionReason: 'High category involvement.',
            questions: ['What matters?'],
            twitterAnswer: 'Short answer.',
            redditAnswer: 'Long answer.',
            quotes: ['1. **Evidence beats slogans**'],
          }],
          summary: '**Summary** line.',
        },
      })
    },
  })

  app.use(makeI18n())

  const html = await renderToString(app)

  assert.match(html, /Agent Interview/)
  assert.match(html, /purchase decision/)
  assert.match(html, /AgentA/)
  assert.match(html, /World 1/)
  assert.match(html, /World 2/)
  assert.match(html, /Evidence beats slogans/)
})
