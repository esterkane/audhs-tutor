import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { Button } from '../../components/ui/button'
import { Disclosure } from '../../components/ui/disclosure'
import type { Schemas } from '../../lib/api'
import { boundedRead } from '../../lib/boundedRead'
import { useLessonDraft } from '../tutor/useLessonDraft'
import { RequestRecoveryControls } from '../playground/RequestRecoveryControls'
import { useLessonPromotionRecovery, type PendingTutorRequest } from '../playground/useRequestRecovery'
import { emptyLesson, lessonBody, lessonDomains, validLessonForm, type LessonBody, type LessonForm } from './lessonDraft'
const field = 'block w-full rounded border border-line bg-card p-2'
type Receipt = Schemas['LessonDraftReceipt']
export function AnswerLessonDraft({ answerId, learnerId, answerText }: { answerId: string; learnerId: string; answerText: string }) {
  const scope = `answer-lesson:${learnerId}:${answerId}`
  const stored = useLessonDraft(scope, 'lesson authoring')
  const recovery = useLessonPromotionRecovery(scope, answerId)
  const active = useRef<AbortController | null>(null)
  const mounted = useRef(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const cache = useQueryClient()
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; active.current?.abort() } }, [])
  let form = emptyLesson(); let receipt: Receipt | null = null; let invalid = false
  if (stored.input) {
    try {
      const saved = JSON.parse(stored.input)
      if (saved.schema !== 'lesson-authoring.v1' || !validLessonForm(saved.form)) throw new Error('Invalid draft')
      form = saved.form
      if (saved.receipt) {
        if (saved.receipt.action !== 'create_private_draft' || saved.receipt.created_version !== 1 || ![saved.receipt.draft_id, saved.receipt.promotion_id].every(v => typeof v === 'string' && /^[A-Za-z0-9_-]{1,128}$/.test(v))) throw new Error('Invalid receipt')
        receipt = saved.receipt
      }
    } catch { invalid = true }
  }
  function update(next: LessonForm, saved: Receipt | null = receipt) {
    stored.setInput(JSON.stringify({ schema: 'lesson-authoring.v1', form: next, receipt: saved }))
  }
  async function save(previous?: PendingTutorRequest<LessonBody>) {
    if (active.current || (!previous && (invalid || receipt || recovery.pending || recovery.needsDiscard))) return
    const controller = new AbortController(); active.current = controller; setBusy(true); setError('')
    try {
      let intent = previous
      if (!intent) {
        const preview = await boundedRead<Schemas['LessonDraftPreview']>(`/api/lesson-promotions/answers/${encodeURIComponent(answerId)}/preview`, controller.signal, 'Lesson source history')
        if (!mounted.current || controller.signal.aborted) return
        intent = recovery.prepare(lessonBody(form, preview.binding), { display: `Create private lesson draft: ${form.title}`, submitted: '', snapshot: '', mode: 'explicit' })
      }
      const result = await boundedRead<Receipt>('/api/lesson-promotions/drafts', controller.signal, 'Lesson draft save', { method: 'POST', headers: { 'Idempotency-Key': intent.key }, body: JSON.stringify(intent.body) })
      if (!mounted.current || controller.signal.aborted) return
      // Keep later edits in the form; a retry submits only the frozen earlier body.
      stored.setInput(current => {
        const saved = current ? JSON.parse(current) : { schema: 'lesson-authoring.v1', form }
        return JSON.stringify({ ...saved, receipt: result })
      })
      recovery.accept(intent.key)
      await cache.invalidateQueries({ queryKey: ['curriculum', 'drafts'] })
    } catch (reason) { if (mounted.current) setError(reason instanceof Error ? reason.message : 'Save could not be confirmed. Your draft is kept.') }
    finally { if (mounted.current) { active.current = null; setBusy(false) } }
  }
  return <Disclosure label="Create lesson draft (optional)" className="my-3">
    <div className="space-y-3">
      <p>Turn this saved answer into a private lesson draft. Supply an objective, worked example and question that checks application. This saves your text locally without a model call.</p>
      <p className="text-sm text-muted">Answer-derived lessons cannot be activated yet. Source history is retained, but saving is not an accuracy review or permission to share the material.</p>
      {stored.error && <p role="alert">{stored.error}</p>}
      {invalid ? <><p role="alert">Saved authoring data could not be read. Copy it before starting again.</p><textarea className={field} aria-label="Recover lesson draft data" readOnly value={stored.input} /><Button onClick={() => stored.setInput('')}>Discard unreadable draft</Button></> : <>
        <label className="block">Lesson title<input className={field} value={form.title} disabled={busy} maxLength={300} onChange={e => update({ ...form, title: e.target.value })} /></label>
        <label className="block">Subject<select className={field} value={form.domain} disabled={busy} onChange={e => update({ ...form, domain: e.target.value as LessonForm['domain'] })}>{Object.entries(lessonDomains).map(([id, label]) => <option key={id} value={id}>{label}</option>)}</select></label>
        {([['objective', 'What should the learner be able to do?', 1000], ['explanation', 'Explanation', 4000], ['worked_example', 'Worked example', 4000], ['question', 'Application question', 4000], ['criteria', 'Grading criteria — one per line', 49000]] as const).map(([key, label, max]) => <label key={key} className="block">{label}<textarea className={field} rows={3} disabled={busy} maxLength={max} value={form[key]} onChange={e => update({ ...form, [key]: e.target.value })} /></label>)}
        <Button variant="secondary" disabled={busy || !!form.explanation} onClick={() => update({ ...form, explanation: answerText.slice(0, 4000) })}>Use answer as explanation</Button>
        <p className="text-xs text-muted">Copies up to 4,000 characters for editing; review and shorten it as needed. Form changes stay in this browser tab and do not update an already saved lesson.</p>
        {receipt ? <div role="status"><p>Draft creation confirmed. Your form is kept; later edits may differ from the saved version.</p><Link className="underline" to={`/curriculum?draft=${encodeURIComponent(receipt.draft_id)}`}>Open saved lesson draft</Link></div> : <Button disabled={busy || !!recovery.pending || recovery.needsDiscard} onClick={() => void save()}>Save private lesson draft</Button>}
      </>}
      <RequestRecoveryControls saveOnly savedAction="create another draft" recovery={recovery} busy={busy} originalContext="answer binding and submitted lesson text" retry={() => { if (recovery.pending) void save(recovery.pending) }} />
      {error && <p role="alert">{error}</p>}
      {busy && <><p role="status">Saving… Stopping this wait does not cancel a server save.</p><Button variant="secondary" onClick={() => active.current?.abort()}>Stop waiting</Button></>}
    </div>
  </Disclosure>
}
