import { describe, test } from 'vitest'
import assert from 'node:assert/strict'

import { renderReportMarkdown } from '../src/utils/reportMarkdown.ts'

describe('report markdown rendering', () => {
  test('renders headings, inline formatting, quotes, lists, and code blocks', () => {
    const html = renderReportMarkdown([
      '## Outer title',
      '',
      '### Inner heading',
      '**Bold claim** and `inline code`.',
      '> Quoted signal',
      '',
      '- First bullet',
      '  - Nested bullet',
      '1. First ordered',
      '',
      '```json',
      '{"ok": true}',
      '```',
    ].join('\n'))

    assert.doesNotMatch(html, /Outer title/)
    assert.match(html, /<h4 class="md-h4">Inner heading<\/h4>/)
    assert.match(html, /<strong>Bold claim<\/strong>/)
    assert.match(html, /<code class="inline-code">inline code<\/code>/)
    assert.match(html, /<blockquote class="md-quote">Quoted signal<\/blockquote>/)
    assert.match(html, /<ul class="md-ul">/)
    assert.match(html, /data-level="1"/)
    assert.match(html, /<ol class="md-ol">/)
    assert.match(html, /<pre class="code-block"><code>{"ok": true}<br><\/code><\/pre>/)
  })

  test('preserves numbering for separated single ordered items', () => {
    const html = renderReportMarkdown([
      '1. First',
      '',
      'Paragraph between.',
      '',
      '2. Second',
    ].join('\n'))

    assert.match(html, /<ol class="md-ol">/)
    assert.match(html, /<ol class="md-ol" start="2">/)
  })
})
