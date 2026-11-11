import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Button } from '../../components/ui/button'
import { Disclosure } from '../../components/ui/disclosure'
import { boundedRead } from '../../lib/boundedRead'
import type { Schemas } from '../../lib/api'
import { matchingPdfPages } from './matchingPdfPages'

type Props = {
  uploadId: string
  versionId: string
  passage?: string
  selectPassage?: (text: string) => void
  notes?: string
}

export function UploadedPdfPages({ uploadId, versionId, passage, selectPassage, notes }: Props) {
  const [index, setIndex] = useState(0)
  const [preview, setPreview] = useState('')
  const [failed, setFailed] = useState(false)
  const [zoom, setZoom] = useState(false)
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
  const src = page && '/api/knowledge-material/uploads/' + encodeURIComponent(uploadId) + '/versions/' + encodeURIComponent(versionId) + '/pages/' + page.page + '/preview'
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
            <select className="block border rounded p-2" value={index} onChange={event => { setIndex(Number(event.target.value)); setPreview('') }}>
              {pages.map((item, i) => <option key={item.page} value={i}>Page {item.page}{item.ocr ? ' · OCR used' : ''}</option>)}
            </select>
          </label>
          {page.text.trim() ? <blockquote aria-label={`Extracted text from PDF page ${page.page}`} className="mt-2 whitespace-pre-wrap break-words border-l-2 pl-3">{page.text}</blockquote> : <p>No text was extracted from this page.</p>}
          {src && <>
            <Button variant="secondary" aria-expanded={preview === src} onClick={()=>{
              setPreview(preview === src ? '' : src); setFailed(false); setZoom(false)
            }}>{preview === src ? 'Hide original page' : 'Inspect original page ' + page.page}</Button>
            {preview === src && (failed ? <p role="alert">The original page image could not be loaded. Hide and reopen it to retry.</p>
              : <figure>
                <figcaption>Original PDF page {page.page}. Compare the scan with the extracted text above.</figcaption>
                <Button variant="secondary" aria-pressed={zoom} onClick={()=>setZoom(!zoom)}>Enlarge page image</Button>
                <div tabIndex={zoom ? 0 : undefined} role="region" aria-label="Original PDF page image" className="max-h-[70vh] overflow-auto">
                  <img src={src} alt={'Original uploaded PDF page ' + page.page} className={zoom ? 'max-w-none' : 'max-w-full h-auto'} onError={()=>setFailed(true)} />
                </div>
              </figure>)}
          </>}
          {selectPassage && !!page.text.trim() && (page.text.length <= 6000 && notes?.includes(page.text)
            ? <Button variant="secondary" onClick={() => selectPassage(page.text)}>Use page {page.page} as passage</Button>
            : <p className="text-sm">Copy a passage of up to 6,000 characters that also appears in your source notes.</p>)}
        </Disclosure>
      </>}
  </div>
}
