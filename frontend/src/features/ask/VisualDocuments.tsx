import { lazy, Suspense, useEffect, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Button } from '../../components/ui/button'
import { Disclosure } from '../../components/ui/disclosure'
import type { Schemas } from '../../lib/api'
import { boundedRead } from '../../lib/boundedRead'
import { VisualReview } from './VisualReview'
import { VisualFallback } from '../visual-learning/VisualFallback'

const RelationshipGraph = lazy(() => import('../visual-learning/RelationshipGraph'))

type Document = Schemas['VisualDocumentSummary']
const pageSize = 20

export function VisualDocuments({ answerId, learnerId, refresh }: { answerId: string; learnerId: string; refresh: string }) {
  const [archived, setArchived] = useState(false)
  const [offset, setOffset] = useState(0)
  const [selected, setSelected] = useState('')
  const cache = useQueryClient()
  useEffect(() => { void cache.invalidateQueries({ queryKey: ['visual-documents', learnerId, answerId] }) }, [cache, learnerId, answerId, refresh])
  const documents = useQuery({ queryKey: ['visual-documents', learnerId, answerId, archived, offset], retry: false,
    queryFn: ({ signal }) => boundedRead<Document[]>(`/api/authored-visuals?answer_id=${encodeURIComponent(answerId)}&archived=${archived}&offset=${offset}&limit=${pageSize}`, signal, 'Saved diagrams'),
  })
  const rows = documents.data ?? []
  const document = selected ? rows.find(row => row.id === selected) : rows[0]
  if (!selected && document) setSelected(document.id)
  function page(next: number) { setOffset(next); setSelected('') }
  return <section aria-label="Saved diagrams" className="space-y-3">
    <h3 className="font-semibold">Saved diagrams</h3>
    <label className="flex items-center gap-2"><input type="checkbox" checked={archived} onChange={event => { setArchived(event.target.checked); page(0) }} />Show archived diagrams</label>
    {documents.isPending && <p role="status">Loading diagram library…</p>}
    {documents.isError && <p role="alert">Diagram library unavailable. <Button onClick={() => void documents.refetch()}>Retry diagram library</Button></p>}
    {documents.isSuccess && !rows.length && <p>{archived ? 'No archived diagrams on this page.' : 'No saved diagrams on this page.'}</p>}
    {rows.length > 0 && <label className="block">Choose saved diagram<select className="block w-full min-h-11 rounded border border-line bg-card px-3" value={document?.id ?? ''} onChange={event => setSelected(event.target.value)}>{!document && <option value="">Choose a diagram</option>}{rows.map(row => <option key={row.id} value={row.id}>{row.title}</option>)}</select></label>}
    {(offset > 0 || rows.length === pageSize) && <div className="flex flex-wrap gap-2"><Button disabled={offset === 0 || documents.isFetching} onClick={() => page(Math.max(0, offset - pageSize))}>Previous diagrams</Button><Button disabled={rows.length < pageSize || documents.isFetching} onClick={() => page(offset + pageSize)}>More diagrams</Button></div>}
    {documents.isSuccess && selected && !document && <p role="status">The selected diagram is no longer on this page. Choose another diagram or check archived diagrams.</p>}
    {document && <VisualDocument key={document.id} document={document} learnerId={learnerId} />}
  </section>
}

function VisualDocument({ document, learnerId }: { document: Document; learnerId: string }) {
  const [selected, setSelected] = useState('')
  const [offset, setOffset] = useState(0)
  const versions = useQuery({ queryKey: ['visual-versions', learnerId, document.id, document.revision, offset], retry: false,
    queryFn: ({ signal }) => boundedRead<Schemas['VisualVersionSummary'][]>(`/api/authored-visuals/${encodeURIComponent(document.id)}/versions?offset=${offset}&limit=${pageSize}`, signal, 'Diagram versions'),
  })
  const rows = versions.data ?? []
  const versionId = selected || rows[0]?.id
  if (!selected && versionId) setSelected(versionId)
  const detail = useQuery({ queryKey: ['answer-visual-version', learnerId, document.id, versionId], enabled: !!versionId, retry: false,
    queryFn: ({ signal }) => boundedRead<Schemas['VisualVersionDetail']>(`/api/authored-visuals/${encodeURIComponent(document.id)}/versions/${encodeURIComponent(versionId!)}`, signal, 'Saved diagram'),
  })
  const spec = detail.data?.spec?.schema_version === 'visual.answer.v1' ? detail.data.spec : null
  return <div className="space-y-3">
    {document.archived && <p role="status">Archived diagram · history retained. Restore controls are not available here yet.</p>}
    {versions.isPending && <p role="status">Loading diagram versions…</p>}
    {versions.isError && <p role="alert">Version history unavailable. <Button onClick={() => void versions.refetch()}>Retry version history</Button></p>}
    {!!rows.length && <label className="block">Diagram version<select className="block w-full min-h-11 rounded border border-line bg-card px-3" value={versionId ?? ''} onChange={event => setSelected(event.target.value)}>{selected && !rows.some(row => row.id === selected) && <option value={selected}>Selected version {detail.data?.version ?? ""} · Historical</option>}{rows.map((row, index) => <option key={row.id} value={row.id}>Version {row.version}{offset === 0 && index === 0 ? ' · Latest' : ' · Historical'}</option>)}</select></label>}
    {(offset > 0 || rows.length === pageSize) && <div className="flex flex-wrap gap-2"><Button disabled={offset === 0 || versions.isFetching} onClick={() => { setOffset(Math.max(0, offset - pageSize)); setSelected('') }}>Newer versions</Button><Button disabled={rows.length < pageSize || versions.isFetching} onClick={() => { setOffset(offset + pageSize); setSelected('') }}>Older versions</Button></div>}
    {versionId && (offset > 0 || versionId !== rows[0]?.id) && <p>Historical version · reviews apply only to this exact version.</p>}
      {detail.isFetching && versionId && <p role="status">Loading saved diagram…</p>}
      {detail.isError && <p role="alert">Saved diagram unavailable. <Button onClick={() => void detail.refetch()}>Retry saved diagram</Button></p>}
      {detail.data && !spec && <p role="alert">This saved diagram cannot be displayed. The original answer is still available above.</p>}
      {spec && <section aria-label="Saved visual draft" className="space-y-3 break-words">
        <h3 className="font-semibold">{spec.title}</h3>
        <p className="text-sm text-muted">Version {detail.data!.version} · {detail.data!.origin?.kind === 'model' ? 'Model-generated draft' : detail.data!.origin?.kind === 'learner' ? 'Learner-edited draft' : 'Origin unknown'} · No learning assessment.</p>
        <p>{detail.data!.grounding_now === 'sources_recorded' ? 'Source references are recorded; this does not verify the diagram.' : detail.data!.grounding_now === 'ungrounded' ? 'Ungrounded: no source passages support this draft.' : 'Grounding is unavailable or changed. Review the original answer and sources before relying on this draft.'}</p>
        <p>{spec.text_equivalent}</p>
        <VisualFallback key={detail.data!.id}><Suspense fallback={<p role="status">Loading diagram renderer…</p>}>
          <RelationshipGraph graph={{ title: spec.title, textEquivalent: spec.text_equivalent, directed: spec.directed, nodes: spec.nodes, edges: spec.edges }} showTextEquivalent={false} />
        </Suspense></VisualFallback>
        <Disclosure label="Read all concepts and relationships">
          <ul className="list-disc pl-5 space-y-2">{spec.nodes.map(node => <li key={node.id}><strong>{node.label}:</strong> {node.explanation}</li>)}</ul>
          <ul className="list-disc pl-5 space-y-2 mt-3">{spec.edges.map(edge => <li key={edge.id}>{spec.nodes.find(node => node.id === edge.source)?.label} {spec.directed ? '→' : '—'} {spec.nodes.find(node => node.id === edge.target)?.label}: {edge.label}</li>)}</ul>
        </Disclosure>
        <p className="text-sm text-muted">Source passages, when available, are in the answer above.</p>
        {<VisualReview readOnly={document.archived || versionId !== versions.data?.[0]?.id || offset !== 0} key={`review:${detail.data!.id}`} documentId={document.id} learnerId={learnerId} version={detail.data!} />}
      </section>}
  </div>
}
