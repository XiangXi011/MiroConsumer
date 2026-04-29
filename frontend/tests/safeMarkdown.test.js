import test from 'node:test'
import assert from 'node:assert/strict'

import { renderSafeMarkdown } from '../src/utils/safeMarkdown.js'

test('renderSafeMarkdown escapes raw HTML before applying markdown', () => {
  const rendered = renderSafeMarkdown('**safe** <img src=x onerror="alert(1)"> `code<script>`')

  assert.match(rendered, /<strong>safe<\/strong>/)
  assert.match(rendered, /&lt;img src=x/)
  assert.doesNotMatch(rendered, /<img/i)
  assert.doesNotMatch(rendered, /onerror=/i)
  assert.doesNotMatch(rendered, /<script/i)
})
