import { expect, test } from 'vitest'
import { guideCitationHref } from './guideCitationHref'

const guide = 'https://supabase.com/docs/guides/self-hosting/self-hosted-oauth'
test('opens the HTML heading for a saved Markdown guide citation', () => {
  expect(guideCitationHref(guide + '.md#environment-variable-reference')).toBe(
    guide + '#environment-variable-reference',
  )
})

test.each([
  guide + '.md',
  guide + '#heading',
  guide + '.md?edition=1#heading',
  'https://example.org/docs/guides/sample.md#heading',
  'https://supabase.com/docs/reference/example.md#heading',
  'https://www.postgresql.org/docs/17/sql-update.html',
])('preserves the cited resource %s', url => {
  expect(guideCitationHref(url)).toBe(url)
})
