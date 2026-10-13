import { lazy, Suspense, useEffect, useRef, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Button } from '../../components/ui/button'
import { Disclosure } from '../../components/ui/disclosure'
import type { Schemas } from '../../lib/api'
import { boundedRead } from '../../lib/boundedRead'
import { RequestRecoveryControls } from '../playground/RequestRecoveryControls'
import { useVisualRequestRecovery, type PendingTutorRequest, type VisualGenerationBody } from '../playground/useRequestRecovery'
import { VisualFallback } from '../visual-learning/VisualFallback'

const RelationshipGraph = lazy(() => import('../visual-learning/RelationshipGraph'))
type Job = Schemas['VisualGenerationStatus']
const active = (job: Job) => job.state === 'pending' || job.state === 'running'
const messages: Record<Job['state'], string> = {
  pending: 'Waiting to generate locally.', running: 'Generating locally. You can stop or continue your conversation.',
  completed: 'Diagram saved in your local database. Reopening does not generate again.',
  cancelled: 'Generation stopped. No new diagram was saved.',
  interrupted: 'Generation was interrupted by a server restart. It will not restart automatically.',
  failed: 'A diagram could not be saved. Check local model readiness and whether the answer or sources changed.',
}

export function AnswerVisual({ answerId, learnerId }: { answerId: string; learnerId: string }) {
  const [opened, setOpened] = useState(false)
  const [selected, setSelected] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const request = useRef<AbortController | null>(null)
  const mounted = useRef(true)
  const cache = useQueryClient()
  const key = ['answer-visuals', learnerId, answerId]
  const recovery = useVisualRequestRecovery(`ask-visual:${learnerId}:${answerId}`)
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; request.current?.abort() } }, [])
  const history = useQuery({
    queryKey: key, enabled: opened, retry: false,
    queryFn: ({ signal }) => boundedRead<Job[]>(`/api/visual-generation?answer_id=${encodeURIComponent(answerId)}`, signal, 'Visual history'),
    refetchInterval: query => query.state.status !== 'error' && query.state.data?.some(active) ? 1500 : false,
  })
  const jobs = history.data ?? []
  const job = jobs.find(item => item.id === selected) ?? jobs[0]
  const working = jobs.some(active)
  const detail = useQuery({
    queryKey: ['answer-visual-version', learnerId, job?.document_id, job?.result_version_id],
    enabled: opened && !!job?.document_id && !!job.result_version_id, retry: false,
    queryFn: ({ signal }) => boundedRead<Schemas['VisualVersionDetail']>(`/api/authored-visuals/${encodeURIComponent(job!.document_id!)}/versions/${encodeURIComponent(job!.result_version_id!)}`, signal, 'Saved diagram'),
  })

  function remember(row: Job) {
    cache.setQueryData<Job[]>(key, old => [row, ...(old ?? []).filter(item => item.id !== row.id)])
    setSelected(row.id)
    void cache.invalidateQueries({ queryKey: key })
  }

  async function start(previous?: PendingTutorRequest<VisualGenerationBody>) {
    if (request.current || (!previous && (working || recovery.pending || recovery.needsDiscard))) return
    const controller = new AbortController()
    request.current = controller; setBusy(true); setError('')
    try {
      let intent = previous
      if (!intent) {
        const target = await boundedRead<Schemas['AnswerVisualTarget']>(`/api/authored-visuals/answer-target/${encodeURIComponent(answerId)}`, controller.signal, 'Visual target')
        if (!mounted.current || controller.signal.aborted) return
        if (target.grounding === 'unknown') throw new Error('This answer has missing or changed source history. Review its sources before generating a diagram.')
        intent = recovery.prepare({ binding: target.binding }, { display: 'Visual explanation of this saved answer', submitted: '', snapshot: '', mode: 'explicit' })
      }
      const row = await boundedRead<Job>('/api/visual-generation', controller.signal, 'Visual request', {
        method: 'POST', headers: { 'Idempotency-Key': intent.key }, body: JSON.stringify(intent.body),
      })
      if (!mounted.current || controller.signal.aborted) return
      recovery.accept(intent.key); remember(row)
    } catch (reason) {
      if (mounted.current) {
        setError(reason instanceof Error ? reason.message : 'Visual request unavailable.')
        void cache.invalidateQueries({ queryKey: key })
      }
    } finally {
      if (mounted.current) { request.current = null; setBusy(false) }
    }
  }

  async function stop(row: Job) {
    if (request.current) return
    const controller = new AbortController(); request.current = controller; setBusy(true); setError('')
    try {
      const stopped = await boundedRead<Job>(`/api/visual-generation/${encodeURIComponent(row.id)}/cancel`, controller.signal, 'Stop request', { method: 'POST' })
      if (mounted.current && !controller.signal.aborted) remember(stopped)
    } catch (reason) {
      if (mounted.current) setError(`Stop is not confirmed. ${reason instanceof Error ? reason.message : 'Refresh status and try again.'}`)
    } finally { if (mounted.current) { request.current = null; setBusy(false) } }
  }

  const spec = detail.data?.spec?.schema_version === 'visual.answer.v1' ? detail.data.spec : null
  return <Disclosure label="Visual explanation (optional)" className="my-3" onToggle={event => setOpened(event.currentTarget.open)}>
    <div className="space-y-3">
      <p className="text-sm text-muted">Create a relationship diagram from this answer using a local model. Saved drafts are not fact-checked. Your answer and follow-up chat stay available.</p>
      {history.isPending && opened && <p role="status">Loading saved diagrams…</p>}
      {history.isError && <p role="alert">Visual history is unavailable. <Button onClick={() => void history.refetch()}>Retry visual history</Button></p>}
      <RequestRecoveryControls recovery={recovery} busy={busy} retry={() => void start(recovery.pending ?? undefined)} originalContext="saved answer and source binding" />
      {error && <p role="alert">{error}</p>}
      {history.isSuccess && <Button disabled={busy || working || !!recovery.pending || recovery.needsDiscard} onClick={() => void start()}>{jobs.length ? 'Generate another diagram' : 'Generate local diagram'}</Button>}
      {busy && <Button variant="secondary" onClick={() => request.current?.abort()}>Stop waiting</Button>}
      {busy && <p role="status">Sending request… Stopping this wait does not confirm server cancellation; refresh status below.</p>}
      {jobs.length > 1 && <label className="block">Saved visual requests
        <select className="block w-full min-h-11 rounded border border-line bg-card px-3" value={job?.id ?? ''} onChange={event => setSelected(event.target.value)}>
          {jobs.map(item => <option key={item.id} value={item.id}>{new Date(item.created_at).toLocaleString()} · {item.state}</option>)}
        </select>
      </label>}
      {job && <p role="status">{messages[job.state]}</p>}
      {jobs.filter(active).map(item => <Button key={item.id} variant="secondary" disabled={busy} onClick={() => void stop(item)}>Stop generation</Button>)}
      {jobs.length > 0 && <Button variant="secondary" onClick={() => void history.refetch()}>Refresh visual status</Button>}
      {detail.isFetching && job?.result_version_id && <p role="status">Loading saved diagram…</p>}
      {detail.isError && <p role="alert">Saved diagram unavailable. <Button onClick={() => void detail.refetch()}>Retry saved diagram</Button></p>}
      {detail.data && !spec && <p role="alert">This saved diagram cannot be displayed. The original answer is still available above.</p>}
      {spec && <section aria-label="Saved visual draft" className="space-y-3 break-words">
        <h3 className="font-semibold">{spec.title}</h3>
        <p className="text-sm text-muted">Version {detail.data!.version} · Model-generated draft · No learning assessment.</p>
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
      </section>}
    </div>
  </Disclosure>
}
