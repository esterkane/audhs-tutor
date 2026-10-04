import { expect, it } from 'vitest'
import { appendExample, pythonExamples } from './starterCode'

it('offers only complete bounded Python examples, not prose or shell commands', () => {
  expect(pythonExamples('```python\nprint(1)\n```')).toEqual(['print(1)'])
  expect(pythonExamples('```sh\nrm file\n```')).toEqual([])
  expect(pythonExamples('```python\nprint(1)')).toEqual([])
  expect(pythonExamples('```python\n' + 'x'.repeat(16001) + '\n```')).toEqual([])
})
it('preserves existing edits and rejects duplicate or oversized insertion', () => {
  expect(appendExample('my_code = 1\n', 'print(2)')).toBe('my_code = 1\n\n\nprint(2)')
  expect(appendExample('', 'print(2)')).toBe('print(2)')
  expect(appendExample('print(2)', 'print(2)')).toBeNull()
  expect(appendExample('x'.repeat(16000), 'print(2)')).toBeNull()
})
