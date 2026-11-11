import { expect, it } from 'vitest'
import { matchingPdfPages } from './UploadedPdfPages'

const pages = [
  {page: 1, text: 'Opening. Repeated text.', ocr: false},
  {page: 3, text: 'Repeated text. Scanned ending.', ocr: true},
]

it('matches the immutable page texts with their original page numbers', () => {
  expect(matchingPdfPages(pages, 'Scanned ending.')).toEqual([3])
  expect(matchingPdfPages(pages, 'Repeated text.')).toEqual([1, 3])
  expect(matchingPdfPages(pages, 'text.\n\nRepeated')).toEqual([1, 3])
  expect(matchingPdfPages(pages, 'My own edited conclusion.')).toEqual([])
  expect(matchingPdfPages(pages, '  ')).toEqual([])
})
