import type { Schemas } from '../../lib/api'

type PdfPage = Schemas['PdfPageSource']

export function matchingPdfPages(pages: PdfPage[], passage: string): number[] {
  if (!passage.trim()) return []
  const extracted = pages.map(page => page.text).join('\n\n')
  const found = new Set<number>()
  let offset = 0
  let match = extracted.indexOf(passage)
  for (const page of pages) {
    const end = offset + page.text.length
    // Matches are in document order. A single match may cross page separators.
    while (match >= 0 && match + passage.length <= offset) match = extracted.indexOf(passage, match + 1)
    if (match >= 0 && match < end && end > offset) found.add(page.page)
    offset = end + 2
  }
  return [...found]
}
