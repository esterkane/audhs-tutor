import { expect, it } from 'vitest'
import { readingMinutes } from './readingTime'

it('rounds a documented display heuristic, without estimating an empty text', () => {
  expect(readingMinutes('')).toBeNull()
  expect(readingMinutes('word '.repeat(200))).toBe(1)
  expect(readingMinutes('word '.repeat(201))).toBe(2)
  expect(readingMinutes('word '.repeat(401))).toBe(3)
})
it('counts German prose and link labels without charging URLs and code as prose', () => {
  expect(readingMinutes('Größen und Überprüfung. [Quelle](https://example.test/' + 'path/'.repeat(500) + ')')).toBe(1)
  expect(readingMinutes('## Example\n```python\ncode\n```')).toBeNull()
  expect(readingMinutes('```python\n' + 'value '.repeat(1000) + '\n```')).toBeNull()
  expect(readingMinutes('~~~~python\n```\n' + 'value '.repeat(1000) + '\n~~~~')).toBeNull()
  expect(readingMinutes('    ' + 'value '.repeat(1000))).toBeNull()
  expect(readingMinutes('`' + 'value '.repeat(1000) + '`')).toBeNull()
  expect(readingMinutes('$$' + 'value '.repeat(1000) + '$$')).toBeNull()
  expect(readingMinutes('```python\n' + 'value '.repeat(1000))).toBeNull()
})
it('does not invent a word-based estimate for unsegmented prose', () => {
  expect(readingMinutes('日本語の説明')).toBeNull()
})
