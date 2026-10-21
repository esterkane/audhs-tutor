import { useEffect, useRef, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Button } from '../../components/ui/button'
import { Card, CardTitle } from '../../components/ui/card'
import { Disclosure } from '../../components/ui/disclosure'
import { apiFetch, type Schemas } from '../../lib/api'
import { ResearchWorkspace } from './ResearchWorkspace'
import { validResearch, sameKnowledgeMaterial } from './researchRecovery'
import { useLessonDraft } from '../tutor/useLessonDraft'

type Form = Schemas['KnowledgeMaterialInput']
type Draft = Schemas['DraftOut']
type Step = NonNullable<Form['workflow_step']>
const steps: Step[] = ['source', 'research', 'write', 'review']
const empty = (): Form => ({ title: '', domain: 'ai_ml', notes: '', upload_id: null,
  objective: '', explanation: '', worked_example: '', question: '', criteria: [], research: null, workflow_step: 'source' })
const field = 'block w-full rounded border border-line bg-card p-2'
function fromDraft(draft?: Draft): Form {
  const data = draft?.payload.authoring as Form | undefined
  if (!data) return empty()
  return Object.fromEntries(Object.keys(empty()).map(key => [key, data[key as keyof Form] ?? empty()[key as keyof Form]])) as Form
}

export function KnowledgeAuthoring({ draft, onOpen, onSaved, onStepChange, review }: { draft?: Draft; onOpen: (id: string | null) => void; onSaved?: (draft: Draft) => void; onStepChange?: (step: Step) => void; review?: React.ReactNode }) {
  const learner = useQuery({ queryKey: ['learner'], queryFn: () => apiFetch<Schemas['LearnerOut']>('/api/learner/me') })
  if (!learner.data) return <p role="status">{learner.error ? 'Knowledge editor could not load. Reload to retry.' : 'Loading knowledge editor…'}</p>
  return <Editor key={`${learner.data.id}:${draft?.id ?? 'new'}`} learnerId={learner.data.id} draft={draft} onOpen={onOpen} onSaved={onSaved} onStepChange={onStepChange} review={review} />
}

function Editor({ learnerId, draft, onOpen, onSaved, onStepChange, review }: { learnerId: string; draft?: Draft; onOpen: (id: string | null) => void; onSaved?: (draft: Draft) => void; onStepChange?: (step: Step) => void; review?: React.ReactNode }) {
  const stored = useLessonDraft(`knowledge:${learnerId}:${draft?.id ?? 'new'}`, 'knowledge material', 1_000_000)
  const [initial] = useState(() => {
    try {
      const saved = stored.input ? JSON.parse(stored.input) : null
      const uuid = (value: unknown) => typeof value === 'string' && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value)
      if (saved && saved.form && typeof saved.form.notes === 'string' && typeof saved.form.title === 'string'
        && ['objective','explanation','worked_example','question'].every(k => typeof saved.form[k] === 'string')
        && Array.isArray(saved.form.criteria) && saved.form.criteria.every((c: unknown) => typeof c === 'string')
        && (saved.form.research == null || validResearch(saved.form.research))
        && (saved.form.workflow_step === undefined || steps.includes(saved.form.workflow_step))
        && uuid(saved.requestId)
        && (saved.revisionRequestId === undefined || uuid(saved.revisionRequestId))
        && (saved.baseVersion === undefined || (Number.isInteger(saved.baseVersion) && saved.baseVersion > 0))
        && ['ai_ml','programming','language','guitar','movement','meta'].includes(saved.form.domain)
        && (saved.form.upload_id === null || typeof saved.form.upload_id === 'string')) return {
          ...saved, damaged: false,
          baseVersion: draft?.status === 'draft' && sameKnowledgeMaterial(saved.form, fromDraft(draft)) ? draft.version : saved.baseVersion,
        } as { form: Form; requestId: string; damaged: boolean; baseVersion?: number; revisionRequestId?: string }
    } catch { /* The recovery text is shown below; never submit it implicitly. */ }
    return { form: fromDraft(draft), requestId: crypto.randomUUID(), damaged: !!stored.input, baseVersion: draft?.version }
  })
  const [revisionRequestId] = useState(initial.revisionRequestId ?? crypto.randomUUID())
  const [form, setForm] = useState(initial.form)
  const [damaged, setDamaged] = useState(initial.damaged)
  const [current, setCurrent] = useState(draft)
  const [editVersion, setEditVersion] = useState(initial.baseVersion ?? draft?.version)
  const step = form.workflow_step ?? 'source'
  const stepHeading = useRef<HTMLHeadingElement | null>(null)
  useEffect(() => { onStepChange?.(step) }, [step, onStepChange])
  function go(next: Step) { change({ ...form, workflow_step: next }, editVersion, false); requestAnimationFrame(() => stepHeading.current?.focus()) }
  const [busy, setBusy] = useState('')
  const [error, setError] = useState('')
  const [status, setStatus] = useState('')
  const active = useRef<AbortController | null>(null)
  const mounted = useRef(true)
  const cache = useQueryClient()
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; active.current?.abort() } }, [])
  const readOnly = damaged || draft?.status === 'published' || draft?.status === 'rejected' || current?.status === 'published' || current?.status === 'rejected'
  useEffect(() => {
    if (readOnly || !current?.id || (step !== 'research' && step !== 'write')) return
    const controller = new AbortController()
    const timer = setTimeout(() => {
      void apiFetch(`/api/knowledge-material/drafts/${current.id}/prepare-tutor`, { method: 'POST', signal: controller.signal }).catch(() => { /* Optional readiness never blocks writing or real tutor error handling. */ })
    }, 800)
    return () => { clearTimeout(timer); controller.abort() }
  }, [current?.id, readOnly, step])

  const [needsSave, setNeedsSave] = useState(!!stored.input && !sameKnowledgeMaterial(initial.form, fromDraft(draft)))
  function change(next: Form, version = editVersion, contentChanged = true) {
    if (contentChanged) setNeedsSave(true)
    setForm(next)
    stored.setInput(JSON.stringify({ form: next, requestId: initial.requestId, revisionRequestId, baseVersion: version }))
    setStatus('Changes kept in this browser tab. Save to keep them in your knowledge library.')
  }
  async function rememberDraft(result: Draft) {
    onSaved?.(result)
    await cache.cancelQueries({ queryKey: ['curriculum', 'drafts'], exact: true })
    cache.setQueryData<Schemas['DraftList']>(['curriculum', 'drafts'], previous => {
      const existing = previous?.drafts.find(item => item.id === result.id)
      if (existing && (existing.version > result.version || (existing.version === result.version && existing.status !== 'draft'))) return previous
      return { drafts: existing ? previous!.drafts.map(item => item.id === result.id ? result : item) : [result, ...(previous?.drafts ?? [])] }
    })
  }
  async function save(signal: AbortSignal): Promise<Draft> {
    const result = await apiFetch<Draft>(current ? `/api/knowledge-material/drafts/${current.id}` : '/api/knowledge-material/drafts', {
      method: current ? 'PUT' : 'POST', signal,
      headers: { 'Idempotency-Key': initial.requestId },
      body: JSON.stringify(current ? { ...form, criteria: form.criteria?.map(c => c.trim()).filter(Boolean), expected_version: editVersion ?? current.version } : { ...form, criteria: form.criteria?.map(c => c.trim()).filter(Boolean) }),
    })
    if (mounted.current) {
      setCurrent(result)
      setNeedsSave(false)
      setEditVersion(result.version)
      stored.setInput(JSON.stringify({ form, requestId: initial.requestId, revisionRequestId, baseVersion: result.version }))
      await rememberDraft(result)
    }
    return result
  }
  async function run(kind: 'save' | 'suggest' | 'research' | 'discuss' | 'draft-section', file?: File, refresh = false) {
    if (active.current || readOnly) return
    const controller = new AbortController(); active.current = controller
    setBusy(file ? 'Reading upload…' : kind === 'discuss' || kind === 'draft-section' ? 'Asking your local research tutor…' : kind === 'research' ? 'Preparing source-specific questions locally…' : kind === 'suggest' ? 'Preparing local proposal…' : 'Saving material…')
    setError(''); setStatus('')
    const timer = setTimeout(() => controller.abort(), 180_000)
    try {
      if (file) {
        if (file.size > 10 * 1024 * 1024) throw new Error('Upload limit is 10 MiB.')
        const upload = await apiFetch<Schemas['KnowledgeUploadOut']>('/api/knowledge-material/uploads', {
          method: 'POST', headers: { 'Content-Type': 'application/octet-stream', 'X-Filename': encodeURIComponent(file.name) },
          body: file, signal: controller.signal,
        })
        if (!mounted.current || controller.signal.aborted) return
        const notes = form.notes ? `${form.notes}\n\n${upload.text}` : upload.text
        if (notes.length > 120000) throw new Error('Your notes and this upload exceed 120,000 characters together. Your notes are unchanged. Shorten them or start another material, then upload the file again.')
        change({ ...form, title: form.title || upload.filename, upload_id: upload.document_id, notes })
        setStatus(`Uploaded ${upload.filename}. Review the extracted content, then save your material. Original source is retained.`)
      } else {
        const saved = await save(controller.signal)
        if (!mounted.current || controller.signal.aborted) return
        if (kind !== 'save') {
          const tutor = kind === 'discuss' || kind === 'draft-section'
          const questionId = form.research?.questions[form.research.current]?.id
          const result = await apiFetch<Draft | Schemas['ResearchTutorOut']>(`/api/knowledge-material/drafts/${saved.id}/${tutor ? 'research-tutor' : kind === 'research' ? 'research-questions' : 'suggest'}`, {
            method: 'POST', body: JSON.stringify(tutor ? { expected_version: saved.version, question_id: questionId, action: kind === 'discuss' ? 'discuss' : 'draft', ...(refresh ? { refresh: true } : {}) } : { expected_version: saved.version }), signal: controller.signal,
          })
          if (!mounted.current || controller.signal.aborted) return
          setCurrent(result); setEditVersion(result.version); change(fromDraft(result), result.version)
          await rememberDraft(result)
          setNeedsSave(false)
          setStatus('reused' in result && result.reused ? 'Showing your saved reply for unchanged research and request. No model call was needed.' : tutor ? 'Tutor reply saved separately. Review it before changing your knowledge section.' : kind === 'research' ? 'Source-specific candidate questions saved. Review and edit them before researching; quotation checks do not verify their premises.' : 'Proposal saved as an inactive draft. Review and edit it before activation.')
        } else setStatus('Knowledge material saved. You can return later or shape it into a lesson.')
        if (!draft) { stored.setInput(''); onOpen(saved.id) }
      }
    } catch (reason) {
      if (mounted.current) setError(controller.signal.aborted
        ? 'Waiting stopped. Your local text is kept. Check the saved draft before generating or saving again.'
        : reason instanceof Error ? reason.message : 'Could not confirm the operation. Check your saved drafts.')
    } finally {
      clearTimeout(timer); active.current = null
      if (mounted.current) setBusy('')
    }
  }
  async function lookupMemories(query: string): Promise<Schemas['PersonalMemory'][]> {
    if (active.current || readOnly) return []
    const controller = new AbortController(); active.current = controller
    const timer = setTimeout(() => controller.abort(), 180_000)
    setBusy('Saving and searching earlier notes locally…'); setError('')
    try {
      const saved = await save(controller.signal)
      const result = await apiFetch<Schemas['MemorySearchOut']>(`/api/knowledge-material/drafts/${saved.id}/memories/search`, { method: 'POST', body: JSON.stringify({ query }), signal: controller.signal })
      return result.memories
    } finally { clearTimeout(timer); active.current = null; if (mounted.current) setBusy('') }
  }
  async function revise() {
    if (!draft || active.current) return
    const controller = new AbortController(); active.current = controller
    setBusy('Preparing editable revision…'); setError('')
    const timer = setTimeout(() => controller.abort(), 180_000)
    stored.setInput(JSON.stringify({ form, requestId: initial.requestId, revisionRequestId, baseVersion: editVersion }))
    try {
      const result = await apiFetch<Draft>(`/api/knowledge-material/drafts/${draft.id}/revise`, {
        method: 'POST', signal: controller.signal, headers: { 'Idempotency-Key': revisionRequestId },
        body: JSON.stringify({ expected_version: draft.version }),
      })
      if (!mounted.current || controller.signal.aborted) return
      await cache.invalidateQueries({ queryKey: ['curriculum', 'drafts'] })
      onOpen(result.id)
    } catch (reason) { if (mounted.current) setError(controller.signal.aborted
      ? 'Waiting stopped. Check saved drafts for the revision before trying again. The current active lesson is unchanged.'
      : reason instanceof Error ? reason.message : 'Check saved drafts before retrying.') }
    finally { clearTimeout(timer); active.current = null; if (mounted.current) setBusy('') }
  }
  return <Card>
    <nav aria-label="Knowledge material steps" className="flex flex-wrap gap-2 mb-4">{steps.map((value, i) => <Button key={value} variant={step === value ? 'primary' : 'secondary'} aria-current={step === value ? 'step' : undefined} disabled={!!busy} onClick={() => go(value)}>{i + 1}. {value[0].toUpperCase() + value.slice(1)}</Button>)}</nav>
    <CardTitle as="h2">{readOnly ? 'Your knowledge material' : current ? 'Edit your knowledge material' : 'Create knowledge material'}</CardTitle>
    <h3 ref={stepHeading} tabIndex={-1} className="text-lg font-semibold my-3">{step === 'source' ? 'Choose your source' : step === 'research' ? 'Investigate one question' : step === 'write' ? 'Write your knowledge section' : 'Review your material'}</h3>
    <p hidden={step !== 'source'} className="my-2">Start with your own notes, or upload content and develop it while learning. Saving keeps an editable draft; activation is a separate step.</p>
    <div className="space-y-4 max-w-[75ch] leading-relaxed">
      {damaged && <div><p role="alert">Saved browser data could not be restored. Copy it before starting a new draft.</p><textarea className={field} aria-label="Recover knowledge material data" readOnly value={stored.input} /><Button onClick={() => { stored.setInput(''); setDamaged(false) }}>Discard unreadable browser draft</Button></div>}
      {draft && <div hidden={step !== 'source'}><Button variant="secondary" disabled={!!busy} onClick={() => onOpen(null)}>Start another knowledge material</Button></div>}

      <div hidden={step !== 'source'} className="space-y-4">
      <label className="block">Material title<input className={field} maxLength={300} value={form.title} disabled={!!busy || readOnly} onChange={e => change({ ...form, title: e.target.value })} /></label>
      <label className="block">Subject<select className={field} value={form.domain} disabled={!!busy || readOnly} onChange={e => change({ ...form, domain: e.target.value as Form['domain'] })}>
        {Object.entries({ ai_ml: 'AI and machine learning', programming: 'Programming', language: 'Language', guitar: 'Guitar', movement: 'Movement', meta: 'Other topics' }).map(([key, label]) => <option key={key} value={key}>{label}</option>)}
      </select></label>
      {!form.upload_id && <><label>Upload reference content (optional)<input className={field} type="file" accept=".txt,.md,.pdf,.docx" disabled={!!busy || readOnly || !!form.upload_id} onChange={e => { const file = e.target.files?.[0]; e.target.value = ''; if (file) void run('save', file) }} /></label>
      <p className="text-sm text-muted">TXT, Markdown, PDF or DOCX; up to 10 MiB. One upload per material. Text-only extraction; scanned PDFs require OCR. Uploads are not executed.</p></>}
      {form.upload_id && <p>Uploaded source linked. Its passages remain attached to the lesson.</p>}
      <label>Your notes and selected source content<textarea className={field} rows={8} maxLength={120000} value={form.notes} disabled={!!busy || readOnly} onChange={e => change({ ...form, notes: e.target.value })} /></label>
      <p className="text-sm text-muted">Keep questions, examples and corrections here. For a local proposal, select or shorten this to 16,000 characters. Longer material can still be saved.</p>
      </div>
      <div hidden={step !== 'research' && step !== 'write'}>
      <ResearchWorkspace phase={step === 'write' ? 'write' : 'research'} onMemorySearch={lookupMemories} form={form} disabled={!!busy || readOnly} onChange={change} onTutor={(action, refresh) => void run(action, undefined, refresh)} />
      {form.research && !readOnly && <Button variant="secondary" disabled={!!busy || !form.title.trim() || form.research.questions.some(q => q.findings || q.evidence || q.unresolved || q.section || q.tutor_exchanges?.length)} onClick={() => void run('research')}>Prepare source-specific questions locally</Button>}
      </div>
      <div hidden={step !== 'review'} className="space-y-4">
      <article aria-label="Knowledge material preview" className="space-y-3"><h3 className="font-semibold">{form.title || 'Untitled material'}</h3><p className="whitespace-pre-wrap">{form.explanation || form.research?.questions.map(q => q.section).filter(Boolean).join('\n\n') || form.notes}</p></article>
      <Disclosure label="Shape a lesson (optional)">
        <p className="mb-2">Write these yourself or generate an editable local proposal. Include a distinct worked example and an application question. Neither generation nor activation verifies factual accuracy.</p>
        {([['objective', 'Learning objective'], ['explanation', 'Explanation'], ['worked_example', 'Worked example'], ['question', 'Application question']] as const).map(([key, label]) => <label className="block my-2" key={key}>{label}<textarea className={field} rows={3} maxLength={key === 'objective' ? 1000 : 4000} value={form[key]} disabled={!!busy || readOnly} onChange={e => change({ ...form, [key]: e.target.value })} /></label>)}
        <label>Success criteria — one per line<textarea className={field} rows={3} value={form.criteria?.join('\n') ?? ''} disabled={!!busy || readOnly} onChange={e => change({ ...form, criteria: e.target.value.split('\n') })} /></label>
      </Disclosure>
      {needsSave ? <p role="status">Save your latest writing before activating the lesson.</p> : review}
      {!readOnly && <Disclosure label="Prepare a local lesson proposal (optional)"><Button disabled={!!busy || !form.title.trim() || !form.notes.trim() || form.notes.length > 16000} onClick={() => void run('suggest')}>Prepare local lesson proposal</Button></Disclosure>}
      {current && <Link className="underline text-sm" to={`/curriculum?draft=${current.id}`}>Saved draft link</Link>}

      </div>
      {draft?.status === 'published' && <div><p>This version is active. Create a revision to keep developing it; the current lesson stays available until you activate the revision.</p><Button disabled={!!busy} onClick={() => void revise()}>Create editable revision</Button></div>}
      <div className="sticky bottom-0 border-t border-line bg-card py-2 space-y-1" aria-label="Save and navigate">
        <div className="flex flex-wrap gap-2">
          {!readOnly && <Button disabled={!!busy || !form.title.trim() || !form.notes.trim()} onClick={() => void run('save')}>Save knowledge material</Button>}
          <Button variant="secondary" disabled={!!busy || step === 'source'} onClick={() => go(steps[steps.indexOf(step) - 1])}>Back</Button>
          <Button variant="secondary" disabled={!!busy || step === 'review'} onClick={() => go(steps[steps.indexOf(step) + 1])}>Next</Button>
        </div>
        {status && <p className="text-sm" role="status">{status}</p>}
        {error && <p role="alert">{error}</p>}
      {stored.error && <p role="alert">{stored.error}</p>}
      {busy && <div><p role="status">{busy}</p><Button variant="secondary" onClick={() => active.current?.abort()}>Stop waiting</Button></div>}
      </div>
    </div>
  </Card>
}
