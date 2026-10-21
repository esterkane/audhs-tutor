import { useRef, useState } from 'react'
import type { Schemas } from '../../lib/api'
import { Button } from '../../components/ui/button'
import { Disclosure } from '../../components/ui/disclosure'
import { PersonalMemoryPanel } from './PersonalMemoryPanel'
import { ResearchTutorPanel } from './ResearchTutorPanel'

type Form = Schemas['KnowledgeMaterialInput']
type Research = Schemas['KnowledgeResearch']
const field = 'block w-full rounded border border-line bg-card p-2'


export function ResearchWorkspace({ form, disabled, onChange, onTutor, phase, onMemorySearch }: {
  phase?: 'research' | 'write'; onMemorySearch?: (query: string) => Promise<Schemas['PersonalMemory'][]>
  form: Form; disabled: boolean; onChange: (next: Form) => void
  onTutor?: (action: 'discuss' | 'draft-section', refresh?: boolean) => void
}) {
  const [tutorOpen, setTutorOpen] = useState(false)
  const tutorContainer = useRef<HTMLDivElement>(null)
  const [passage, setPassage] = useState('')
  const [topic, setTopic] = useState('')
  const [notice, setNotice] = useState('')
  const [viewIndex, setViewIndex] = useState<number | null>(null)
  const r = form.research
  const index = disabled ? viewIndex ?? r?.current ?? 0 : r?.current ?? 0
  const q = r?.questions[index]
  const stale = !!r && !form.notes.includes(r.passage)
  function update(next: Research) { onChange({ ...form, research: next }); setNotice('') }
  function prepare() {
    if (!passage.trim() || !topic.trim() || !form.notes.includes(passage)) return
    const subject = topic.trim()
    update({ passage, topic: subject, current: 0, questions: [
      `What does the selected passage say about ${subject}? Explain it in your own words and identify the supporting sentence.`,
      `Which part of ${subject} needs more evidence or clarification? Research that point and distinguish the passage's claim from your own inference.`,
      `What concrete example would help you explain ${subject}? Work through it and check which details are supported by your sources.`,
    ].map(prompt => ({ id: crypto.randomUUID(), prompt, findings: '', evidence: '', unresolved: '', section: '', tutor_request: '', tutor_basis: '', tutor_exchanges: [] })) })
  }
  return <section aria-label="Source questions and research" className="space-y-3 rounded border border-line p-3">
    <h3 className="font-semibold">Build knowledge step by step</h3>
    <p>Choose a short passage from your notes or upload. Prepare editable research questions, investigate one at a time, then write your own knowledge section. Research does not count as assessment.</p>
    {!r && <>
      <label>Topic to investigate<input className={field} maxLength={300} value={topic} disabled={disabled} onChange={e => setTopic(e.target.value)} /></label>
      <label>Exact source passage<textarea className={field} rows={4} maxLength={6000} value={passage} disabled={disabled} onChange={e => setPassage(e.target.value)} /></label>
      <Button variant="secondary" disabled={disabled || !form.notes || form.notes.length > 6000} onClick={() => setPassage(form.notes)}>Use notes as passage</Button>
      {passage && !form.notes.includes(passage) && <p role="alert">Copy an exact passage from your source notes so the questions stay linked to their source.</p>}
      <Button disabled={disabled || !topic.trim() || !passage.trim() || !form.notes.includes(passage)} onClick={prepare}>Prepare research questions</Button>
      <p className="text-sm text-muted">Instant starter questions use your topic and selected passage; no AI answer is generated. Edit each question to make it specific to what you want to learn.</p>
    </>}
    {r && q && <>
      <p>Question {index + 1} of {r.questions.length} · {r.topic}</p>
      <Disclosure label="Read linked source passage"><blockquote className="whitespace-pre-wrap border-l-2 pl-3">{r.passage}</blockquote></Disclosure>
      {q.source_quote && <div><p className="text-sm text-muted">Question source focus</p><blockquote className="whitespace-pre-wrap border-l-2 pl-3">{q.source_quote}</blockquote></div>}
      {stale && <p role="alert">Your source notes changed. This research keeps its original passage. Review the difference before using your section.</p>}
      <label>Research question<textarea className={field} rows={3} maxLength={2000} value={q.prompt} disabled={disabled} onChange={e => {
        const prompt = e.target.value
        if (prompt.length) update({ ...r, questions: r.questions.map((v, i) => i === index ? { ...v, prompt } : v) })
      }} /></label>
      {([
        ['findings', 'My findings', 'Write your answer in your own words.'],
        ['evidence', 'Evidence and references', 'Paste supporting quotations, source titles, page numbers or URLs. Links are saved as text.'],
        ['unresolved', 'Still uncertain', 'Separate unanswered questions and your own inferences from supported claims.'],
        ['section', 'My knowledge section', 'Develop one paragraph from your findings. Review its accuracy before adding it to your lesson.'],
      ] as const).map(([key, label, help]) => <label hidden={!!phase && (phase === 'research' ? key === 'section' : key !== 'section')} className={phase && (phase === 'research' ? key === 'section' : key !== 'section') ? undefined : 'block'} key={key}>{label}<textarea aria-label={label} className={field} rows={3} maxLength={key === 'unresolved' || key === 'section' ? 4000 : 8000} value={q[key] ?? ''} disabled={disabled} onChange={e => update({ ...r, questions: r.questions.map((v, i) => i === index ? { ...v, [key]: e.target.value } : v) })} /><span className="text-sm text-muted">{help}</span></label>)}
      <div className="flex flex-wrap gap-2">
        <Button variant="secondary" disabled={disabled || r.questions.length >= 12} onClick={() => update({ ...r, current: r.questions.length, questions: [...r.questions, { id: crypto.randomUUID(), prompt: `What else do I need to investigate about ${r.topic}?`, findings: '', evidence: '', unresolved: '', section: '', tutor_request: '', tutor_basis: '', tutor_exchanges: [] }] })}>Add my own research question</Button>
        <Button variant="secondary" disabled={index === 0} onClick={() => disabled ? setViewIndex(index - 1) : update({ ...r, current: index - 1 })}>Previous research question</Button>
        <Button variant="secondary" disabled={index === r.questions.length - 1} onClick={() => disabled ? setViewIndex(index + 1) : update({ ...r, current: index + 1 })}>Next research question</Button>
        <Button disabled={disabled || !q.section?.trim() || stale || `${form.explanation}\n\n${q.section}`.trim().length > 4000 || form.explanation.includes(q.section)} onClick={() => {
          onChange({ ...form, explanation: [form.explanation, q.section].filter(Boolean).join('\n\n') })
          setNotice('Section added to your editable explanation. Review and save your knowledge material; activation remains separate.')
        }}>Add section to explanation</Button>
      </div>
      <p className="text-sm text-muted">Use Save knowledge material below to keep all questions, findings and your current place in the library. You may move on with unresolved questions. Shape a lesson when ready.</p>
      {onMemorySearch && <Disclosure label="Find earlier personal notes"><PersonalMemoryPanel ids={q.memory_ids ?? []} disabled={disabled} onSearch={onMemorySearch} onChange={ids => update({ ...r, questions: r.questions.map((v, i) => i === index ? { ...v, memory_ids: ids } : v) })} /></Disclosure>}
      <div ref={tutorContainer}><Disclosure label="Ask the local tutor (optional)" open={tutorOpen} onToggle={e => setTutorOpen(e.currentTarget.open)}><ResearchTutorPanel onUseDraft={() => { setNotice('Draft copied to your editable section. Review it in Write.'); setTutorOpen(false); tutorContainer.current?.querySelector('summary')?.focus() }} research={r} question={q} disabled={disabled} sourceChanged={stale} onTutor={onTutor} onChange={next => update({ ...r, questions: r.questions.map((v, i) => i === index ? next : v) })} /></Disclosure></div>
    </>}
    {notice && <p role="status">{notice}</p>}
  </section>
}
