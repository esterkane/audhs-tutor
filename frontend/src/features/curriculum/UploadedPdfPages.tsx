import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Button } from '../../components/ui/button'
import { Disclosure } from '../../components/ui/disclosure'
import { boundedRead } from '../../lib/boundedRead'
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

type Props = {
  uploadId: string
  versionId: string
  passage?: string
  selectPassage?: (text: string) => void
  notes?: string
}

export function UploadedPdfPages({ uploadId, versionId, passage, selectPassage, notes }: Props) {
  const [index, setIndex] = useState(0)
  const query = useQuery({
    queryKey: ['uploaded-pdf-pages', uploadId, versionId],
    queryFn: ({ signal }) => boundedRead<Schemas['PdfPageSources']>(
      `/api/knowledge-material/uploads/${encodeURIComponent(uploadId)}/versions/${encodeURIComponent(versionId)}/pages`,
      signal, 'PDF page text',
    ),
    staleTime: Infinity,
    retry: false,
  })
  const pages = query.data?.pages
  const matches = useMemo(() => pages && passage ? matchingPdfPages(pages, passage) : [], [pages, passage])
  const page = pages?.[index]
  return <div className="space-y-2">
    {query.isError ? <p role="status">PDF page references could not be loaded. <Button onClick={() => void query.refetch()}>Retry page references</Button></p>
      : query.isPending ? <p role="status">Loading PDF page references…</p>
      : !page ? <p>Page references are unavailable for this saved extraction.</p>
      : <>
        {passage?.trim() && <p className="text-sm">{matches.length
          ? `Exact passage matches PDF ${matches.length === 1 ? 'page' : 'pages'} ${matches.join(', ')}.`
          : 'No exact page match in this PDF extraction.'}</p>}
        <Disclosure label="Browse PDF pages">
          <label className="block">PDF page
            <select className="block border rounded p-2" value={index} onChange={event => setIndex(Number(event.target.value))}>
              {pages.map((item, i) => <option key={item.page} value={i}>Page {item.page}{item.ocr ? ' · OCR used' : ''}</option>)}
            </select>
          </label>
          <blockquote aria-label={`Extracted text from PDF page ${page.page}`} className="mt-2 whitespace-pre-wrap break-words border-l-2 pl-3">{page.text}</blockquote>
          {selectPassage && (page.text.length <= 6000 && notes?.includes(page.text)
            ? <Button variant="secondary" onClick={() => selectPassage(page.text)}>Use page {page.page} as passage</Button>
            : <p className="text-sm">Copy a passage of up to 6,000 characters that also appears in your source notes.</p>)}
        </Disclosure>
      </>}
  </div>
}
