import { useQuery } from '@tanstack/react-query'
import { useEffect, useLayoutEffect, useRef, useState, type ReactNode } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { Button } from '../../components/ui/button'
import { Textarea } from '../../components/ui/textarea'
import type { Schemas } from '../../lib/api'
import { boundedRead } from '../../lib/boundedRead'
import { useDraftRecovery } from '../curriculum/useDraftRecovery'
import { useCorrectionCommand } from './useCorrectionCommand'
import { CorrectionComparison } from './CorrectionComparison'
import { CorrectionImpact } from './CorrectionImpact'

type Candidate = Schemas['SaveCorrectionDraft']['candidate']
type View = Schemas['CorrectionDraftView']
function object(value: unknown): Record<string, unknown> { return value && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : {} }
function strings(value: unknown): string[] { return Array.isArray(value) ? value.map(String) : [] }
function Field({ label, children }: { label: string; children: ReactNode }) { return <label className="grid gap-1"><span className="font-medium">{label}</span>{children}</label> }
function Retry({ command }: { command: ReturnType<typeof useCorrectionCommand> }) {
  return <>
    {command.error && <p role="alert">{command.error}</p>}
    {command.pending && <div className="flex flex-wrap gap-2">
      <Button disabled={command.busy} onClick={() => void command.check()}>Check save status</Button>
      <Button disabled={command.busy} onClick={() => void command.retry()}>Retry same command</Button>
    </div>}
  </>
}

export function CorrectionEditor() {
  const [params, setParams] = useSearchParams()
  const draft = params.get('draft')
  const assessment = params.get('assessment')
  const report = params.get('report')
  return <div className="grid gap-4 max-w-3xl min-w-0">
    <h1 className="text-2xl font-semibold">Question correction drafts</h1>
    <p>Drafts do not change practice questions or grades. Publication is not available yet.</p>
    <Link to="/preferences#question-reports">Back to reported questions</Link>
    {draft ? <LoadDraft key={draft} id={draft} /> : assessment
      ? <StartDraft key={`${assessment}:${report}`} assessment={assessment} report={report} onOpen={id => setParams({ draft: id })} />
      : <DraftList />}
    <Link to="/corrections">All correction drafts</Link>
  </div>
}
function StartDraft({ assessment, report, onOpen }: { assessment: string; report: string | null; onOpen: (id: string) => void }) {
  const [starting, setStarting] = useState(false)
  const [error, setError] = useState('')
  const loading = useRef<AbortController | null>(null)
  const command = useCorrectionCommand(`create:${assessment}:${report ?? ''}`, null, receipt => onOpen(receipt.draft_id))
  useEffect(() => () => loading.current?.abort(), [])
  async function start() {
    if (loading.current || command.pending) return
    const controller = new AbortController(); loading.current = controller; setStarting(true); setError('')
    try {
      const source = await boundedRead<Schemas['CorrectionSource']>(`/api/questions/${encodeURIComponent(assessment)}/correction-source`, controller.signal, 'Authoring source')
      if (controller.signal.aborted) return
      await command.send({ action: 'create', body: { request_id: crypto.randomUUID(), assessment_id: assessment,
        feedback_id: report, expected_question_revision: source.question_revision, expected_content_version: source.content_version } })
    } catch { if (!controller.signal.aborted) setError('Could not open this question. Retry; no correction draft was requested.') }
    finally { if (!controller.signal.aborted) setStarting(false); if (loading.current === controller) loading.current = null }
  }
  return <section className="grid gap-3 border border-line rounded p-4">
    <h2 className="text-lg font-semibold">Enter question authoring</h2>
    <p>This reveals the reference answers and grading criteria. Use this to correct a question, not to check your own understanding.</p>
    <Button disabled={starting || command.busy || !!command.pending || command.blocked} onClick={() => void start()}>Show reference answers and start a draft</Button>
    {(starting || command.busy) && <p role="status">Opening draft…</p>}
    {error && <p role="alert">{error}</p>}<Retry command={command} />
  </section>
}
function DraftList() {
  const [offset, setOffset] = useState(0)
  const query = useQuery({ queryKey: ['correction-drafts', offset], retry: false,
    queryFn: ({ signal }) => boundedRead<Schemas['CorrectionDraftList']>(`/api/questions/correction-drafts?offset=${offset}&limit=20`, signal, 'Correction drafts') })
  return <section className="grid gap-3">
    <h2 className="text-lg font-semibold">Saved drafts</h2>
    <Button disabled={query.isFetching} onClick={() => void query.refetch()}>Refresh saved drafts</Button>
    {query.isFetching && <p role="status">Loading drafts…</p>}
    {query.error && <p role="alert">Could not load saved drafts. Use Refresh to retry.</p>}
    {query.data && <><p>{query.data.total} saved draft(s).</p>{query.data.items.map(row => <article key={row.id} className="border border-line p-3 rounded">
      <p>{row.kind.replaceAll('_', ' ')} · version {row.revision} · {row.status}</p>
      <Link to={`/corrections?draft=${encodeURIComponent(row.id)}`}>Open draft — includes reference answers</Link>
    </article>)}<div className="flex gap-2 flex-wrap">
      {offset > 0 && <Button disabled={query.isFetching} onClick={() => setOffset(offset - 20)}>Previous drafts</Button>}
      {offset + query.data.items.length < query.data.total && <Button disabled={query.isFetching} onClick={() => setOffset(offset + 20)}>More drafts</Button>}
    </div></>}
  </section>
}
function LoadDraft({ id }: { id: string }) {
  const query = useQuery({ queryKey: ['correction-draft', id], retry: false, refetchOnWindowFocus: false,
    queryFn: ({ signal }) => boundedRead<View>(`/api/questions/correction-drafts/${encodeURIComponent(id)}`, signal, 'Correction draft') })
  return <>{!query.data && query.isFetching && <p role="status">Loading draft…</p>}
    {query.error && <p role="alert">Could not load the saved draft. Your tab recovery is kept.</p>}
    {!query.data && <Button disabled={query.isFetching} onClick={() => void query.refetch()}>Retry loading draft</Button>}
    {query.data && <Editor key={id} initial={query.data} />}</>
}
function Editor({ initial }: { initial: View }) {
  const [server, setServer] = useState(initial)
  const encode = (candidate: Candidate, rationale: string) => JSON.stringify({ candidate, rationale })
  const recovery = useDraftRecovery(`correction:${initial.id}`, server.revision, encode(server.candidate, server.rationale))
  const text = useRef(recovery.text)
  useLayoutEffect(() => { text.current = recovery.text }, [recovery.text])
  const [notice, setNotice] = useState('')
  const [readError, setReadError] = useState('')
  const [checksStale, setChecksStale] = useState(false)
  const reading = useRef<AbortController | null>(null)
  const [readingBusy, setReadingBusy] = useState(false)
  const heading = useRef<HTMLHeadingElement>(null)
  useEffect(() => { heading.current?.focus(); return () => reading.current?.abort() }, [])
  function edit(value: string) { text.current = value; recovery.edit(value) }
  async function refresh() {
    if (reading.current) return
    const controller = new AbortController(); reading.current = controller; setReadingBusy(true); setReadError('')
    try {
      const latest = await boundedRead<View>(`/api/questions/correction-drafts/${encodeURIComponent(initial.id)}`, controller.signal, 'Saved draft')
      if (!controller.signal.aborted) { setServer(latest); setChecksStale(false) }
    } catch { if (!controller.signal.aborted) setReadError('Could not read the saved version. Your edits are kept; try again.') }
    finally { if (!controller.signal.aborted) setReadingBusy(false); if (reading.current === controller) reading.current = null }
  }
  const command = useCorrectionCommand(`draft:${initial.id}`, initial.id, (receipt, sent) => {
    if (sent.action !== 'save') return
    const newer = text.current
    const saved = encode(sent.body.candidate, sent.body.rationale ?? '')
    recovery.reset(saved, receipt.revision)
    if (newer !== saved) recovery.edit(newer)
    setServer(current => current.revision <= receipt.revision ? { ...current, revision: receipt.revision,
      candidate: sent.body.candidate, rationale: sent.body.rationale ?? '' } : current)
    setChecksStale(true)
    setNotice(newer === saved ? `Draft version ${receipt.revision} saved. Practice is unchanged.` : 'Submitted version saved. Your newer edits are still unsaved.')
    void refresh()
    heading.current?.focus()
  })
  let candidate: Candidate = {}; let rationale = ''; let valid = false
  try { const parsed = JSON.parse(recovery.text); candidate = parsed.candidate; rationale = parsed.rationale;
    valid = !!candidate && typeof candidate === 'object' && !Array.isArray(candidate) && typeof rationale === 'string'
  } catch { /* invalid advanced JSON remains in recovery */ }
  const item = object(candidate?.item)
  const update = (field: string, value: unknown) => edit(encode({ ...candidate, item: { ...item, [field]: value } } as Candidate, rationale))
  const conflict = server.revision !== recovery.baseVersion
  const writable = server.status === 'draft'
  return <section className="grid gap-4 min-w-0">
    <h2 ref={heading} tabIndex={-1} className="text-xl font-semibold">Edit proposed question</h2>
    <p role="status">{recovery.dirty ? 'Unsaved edits in this tab.' : `Saved draft version ${recovery.baseVersion}.`} {recovery.restored ? 'Recovered your tab edits.' : ''}</p>
    {recovery.error && <p role="alert">{recovery.error}</p>}
    {notice && <p role="status">{notice}</p>}
    {!writable && <p role="status">{server.status === 'published' ? 'This correction was published. Its draft is retained for reference.' : 'This draft was discarded. Its content is retained for reference.'}</p>}
    <fieldset disabled={!writable} className="grid gap-3 min-w-0">
      {valid ? <>
        <Field label="Question wording"><Textarea value={String(item.question ?? item.text ?? item.prompt ?? '')} onChange={e => update(server.kind === 'mcq' ? 'question' : server.kind === 'cloze' ? 'text' : 'prompt', e.target.value)} /></Field>
        {server.kind === 'mcq' && <>
          <Field label="Options (one per line)"><Textarea value={strings(item.options).join('\n')} onChange={e => edit(encode({ ...candidate, item: { ...item, options: e.target.value.split('\n'), answer: null } } as Candidate, rationale))} /></Field>
          <Field label="Correct option"><select className="border border-control rounded p-2 bg-card" value={Number.isInteger(item.answer) ? String(item.answer) : ''} onChange={e => update('answer', e.target.value === '' ? null : Number(e.target.value))}>
            <option value="">Choose again after changing options</option>{strings(item.options).map((option, i) => <option key={i} value={i}>{i + 1}. {option}</option>)}
          </select></Field>
          <Field label="Why this answer is correct"><Textarea value={String(item.explanation ?? '')} onChange={e => update('explanation', e.target.value)} /></Field>
        </>}
        {server.kind === 'cloze' && <Field label="Accepted answers (one per line)"><Textarea value={strings(item.answers).join('\n')} onChange={e => update('answers', e.target.value.split('\n'))} /></Field>}
        {server.kind.startsWith('challenge_') && <Field label="Reference answer"><Textarea value={String(item.hidden_key ?? '')} onChange={e => update('hidden_key', e.target.value)} /></Field>}
        {(server.kind === 'explain_back' || server.kind === 'transfer' || server.kind.startsWith('challenge_')) && <div className="grid gap-2"><h3 className="font-semibold">Grading criteria</h3>{(Array.isArray(candidate.rubric) ? candidate.rubric : []).map((row, i) => <Field key={i} label={`Criterion ${i + 1}`}><Textarea value={String(object(row).criterion ?? '')} onChange={e => {
          const rubric = (candidate.rubric as unknown[]).map((value, index) => index === i ? { ...object(value), criterion: e.target.value } : value)
          const updatedItem = server.kind.startsWith('challenge_') ? { ...item, criteria: rubric.map(value => object(value).criterion) } : item
          edit(encode({ ...candidate, item: updatedItem, rubric } as Candidate, rationale))
        }} /></Field>)}
          <Button onClick={() => {
            const rubric = [...(Array.isArray(candidate.rubric) ? candidate.rubric : []), { criterion: '', keywords: [] }]
            const updatedItem = server.kind.startsWith('challenge_') ? { ...item, criteria: rubric.map(value => object(value).criterion) } : item
            edit(encode({ ...candidate, item: updatedItem, rubric } as Candidate, rationale))
          }}>Add criterion</Button>
        </div>}
        <Field label="Reason for the correction"><Textarea value={rationale} onChange={e => edit(encode(candidate, e.target.value))} /></Field>
      </> : <p role="alert">Advanced text is not valid draft JSON. Fix it below; your text is retained.</p>}
      <details><summary>Advanced draft JSON</summary><Textarea aria-label="Advanced draft JSON" value={recovery.text} onChange={e => edit(e.target.value)} /></details>
    </fieldset>
    <div className="flex gap-2 flex-wrap">
      <Button disabled={!writable || !valid || !recovery.dirty || conflict || command.busy || !!command.pending || command.blocked} onClick={() => void command.send({ action: 'save', body: { request_id: crypto.randomUUID(), expected_revision: recovery.baseVersion, candidate, rationale } })}>Save correction draft</Button>
      <Button disabled={readingBusy || command.busy} onClick={() => void refresh()}>Compare with saved version</Button>
    </div>
    {command.busy && <p role="status">Saving or checking the draft… Your current edits stay here.</p>}
    <Retry command={command} />{readError && <p role="alert">{readError}</p>}
    {conflict && <div className="grid gap-2 border border-line rounded p-3">
      <p role="alert">Your edits started from version {recovery.baseVersion}; the server has version {server.revision}. Compare before choosing what to keep.</p>
      {valid && <CorrectionComparison before={server.candidate} after={candidate} beforeLabel={`Saved version ${server.revision}`} afterLabel="Your current edits" />}
      <p>Saved reason: {server.rationale || '(none)'}</p>
      <p>Your reason: {rationale || '(none)'}</p>
      <Button disabled={!!command.pending || command.busy} onClick={() => { const kept = text.current; recovery.reset(encode(server.candidate, server.rationale), server.revision); recovery.edit(kept); setNotice('Your edits are kept against the displayed server version. Save explicitly to replace its draft content.') }}>Keep my edits against this saved version</Button>
    </div>}
    {valid && <details><summary>Preview changes from the original question</summary>
      <p>{recovery.dirty ? 'Preview includes your unsaved edits.' : `Preview of saved draft version ${recovery.baseVersion}.`} The original question and learning history remain unchanged.</p>
      <CorrectionComparison before={initial.original_candidate} after={candidate} beforeLabel="Original question" afterLabel="Proposed question" />
    </details>}
    <details><summary>Original question and reference answers</summary><pre className="whitespace-pre-wrap break-words text-sm">{JSON.stringify(initial.original_candidate, null, 2)}</pre></details>
    <CorrectionImpact key={initial.id} id={initial.id} revision={recovery.baseVersion} dirty={recovery.dirty} />
    <section className="grid gap-2"><h3 className="font-semibold">Checks on the saved draft</h3>
      {(recovery.dirty || checksStale) && <p>These checks apply to the last loaded saved version. Save edits and compare with the saved version to refresh them.</p>}
      <p>Source status: {server.review.source_status.replaceAll('_', ' ')}. This does not prove the question is correct.</p>
      {(server.review.content_changed || server.review.question_state_changed) && <p role="alert">The original question or its practice status changed. Your draft is kept for comparison.</p>}
      <ul>{server.review.problems.map((problem, i) => <li key={i}>{problem.field}: {problem.message}</li>)}</ul>
    </section>
  </section>
}
