import { useId, useMemo, useState } from 'react'
import { Button } from '../../components/ui/button'
import { Disclosure } from '../../components/ui/disclosure'
import { useUploadedPdfPages } from './useUploadedPdfPages'
import { matchingPdfPages } from './matchingPdfPages'

import type { Schemas } from '../../lib/api'
type Label = Schemas['DiagramLabel']
const positions = {'top left':'left-[15%] top-[15%]', 'top right':'left-[85%] top-[15%]', center:'left-1/2 top-1/2',
  'bottom left':'left-[15%] top-[85%]', 'bottom right':'left-[85%] top-[85%]'}
type Props = {
  diagramLabel?: Label | null
  editLabel?: (label: Label | null) => void
  uploadId: string
  versionId: string
  passage?: string
  selectPassage?: (text: string) => void
  notes?: string
}

export function UploadedPdfPages({ uploadId, versionId, passage, selectPassage, notes, diagramLabel, editLabel }: Props) {
  const [selectedIndex, setIndex] = useState<number | null>(null)
  const labelId = useId()
  const [preview, setPreview] = useState('')
  const [failed, setFailed] = useState(false)
  const [zoom, setZoom] = useState(false)
  const query = useUploadedPdfPages(uploadId, versionId)
  const pages = query.data?.pages
  const matches = useMemo(() => pages && passage ? matchingPdfPages(pages, passage) : [], [pages, passage])
  const index = selectedIndex ?? Math.max(0, pages?.findIndex(p => p.page === diagramLabel?.page) ?? 0)
  const page = pages?.[index]
  const label = diagramLabel?.page === page?.page ? diagramLabel : null
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
          {editLabel && (!diagramLabel || label) && <Disclosure label="Describe or label this page">
            <label className="block">Your diagram label or description
              <textarea className="block w-full rounded border p-2" maxLength={600}
                value={label?.text ?? ''} onChange={e => editLabel(e.target.value.trim()
                  ? { page: page.page, text: e.target.value, position: label?.position ?? null } : null)} />
            </label>
            {label && <label className="block">Label position on page
              <select className="block rounded border p-2" value={label.position ?? ''}
                onChange={e => editLabel({...label, position: (e.target.value || null) as Label['position']})}>
                <option value="">Whole page</option>
                {Object.keys(positions).map(p => <option key={p}>{p}</option>)}
              </select>
            </label>}
          </Disclosure>}
          {editLabel && diagramLabel && !label && <p>Your diagram label is on page {diagramLabel.page}.</p>}
          {label && <p id={labelId} className="whitespace-pre-wrap break-words">
            <strong>Your diagram label · page {label.page}{label.position ? ', ' + label.position : ''}: </strong>{label.text}
          </p>}
          {src && <>
            <Button variant="secondary" aria-expanded={preview === src} onClick={()=>{
              setPreview(preview === src && !failed ? '' : src); setFailed(false); setZoom(false)
            }}>{preview !== src ? 'Inspect original page ' + page.page : failed ? 'Retry original page ' + page.page : 'Hide original page'}</Button>
            {preview === src && (failed ? <p role="alert">The original page image could not be loaded.</p>
              : <figure>
                <figcaption>Original PDF page {page.page}. {page.text.trim() && 'Compare the original with the extracted text above.'}</figcaption>
                <Button variant="secondary" aria-pressed={zoom} onClick={()=>setZoom(!zoom)}>Enlarge page image</Button>
                <div tabIndex={zoom ? 0 : undefined} role="region" aria-label="Original PDF page image" className="max-h-[70vh] overflow-auto">
                  <div className={zoom ? 'relative w-max' : 'relative w-fit max-w-full'}>
                  <img aria-describedby={label ? labelId : undefined} src={src} alt={'Original uploaded PDF page ' + page.page} className={zoom ? 'max-w-none' : 'max-w-full h-auto'} onError={()=>setFailed(true)} />
                  {label?.position && <span aria-hidden="true" className={'pointer-events-none absolute -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-white bg-black px-2 text-white '+positions[label.position]}>1</span>}
                  </div>
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
