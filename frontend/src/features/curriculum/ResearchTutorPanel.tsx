import { useId } from 'react'
import type { Schemas } from '../../lib/api'
import { Button } from '../../components/ui/button'
import { Disclosure } from '../../components/ui/disclosure'
import { Markdown } from '../../components/Markdown'

type Research = Schemas['KnowledgeResearch']
type Question = Schemas['ResearchQuestion']

export function ResearchTutorPanel({ research, question, disabled, sourceChanged, sourceChangedDescription, onChange, onTutor, onUseDraft, hosted = false }: {
  hosted?: boolean; sourceChangedDescription?: string;
  research: Research; question: Question; disabled: boolean; sourceChanged: boolean
  onUseDraft?: () => void; onChange: (question: Question) => void; onTutor?: (action: 'discuss' | 'draft-section', refresh?: boolean) => void
}) {
  const headingId = useId()
  const requirementsId = useId()
  const history = question.tutor_exchanges ?? []
  const latest = history.at(-1)
  const basis = JSON.stringify({ passage: research.passage, topic: research.topic, question: question.prompt,
    findings: question.findings, evidence: question.evidence, unresolved: question.unresolved, section: question.section })
  let textChanged = question.tutor_basis !== basis
  if (latest?.answer.section && question.section === latest.answer.section) {
    try {
      const saved = JSON.parse(question.tutor_basis ?? '')
      if (saved && typeof saved === 'object' && !Array.isArray(saved)) textChanged = JSON.stringify({ ...saved, section: question.section }) !== basis
    } catch { /* An unknown basis remains changed. */ }
  }
  const changed = !!latest && (textChanged || JSON.stringify(question.memory_ids ?? []) !== JSON.stringify((latest.memories ?? []).map(m => m.id)))
  function reply(exchange: Schemas['ResearchTutorExchange']) {
    return <div className="space-y-2">
      {exchange.reference && <p className="text-sm text-muted">Saved reference-based reply — provenance not verified. <a className="underline" href="https://docs.python.org/3.12/reference/datamodel.html#objects-values-and-types" target="_blank" rel="noreferrer">Python language reference</a>. A saved reference label does not establish how this reply was produced or verify its claims.</p>}
      {exchange.calculation && <p className="text-sm text-muted">Saved {exchange.calculation.startsWith('vector.') ? 'vector' : 'Python'} calculation — provenance not verified. History labels can be imported; they do not certify the result or how it was produced.</p>}
      {exchange.request && <p className="whitespace-pre-wrap">Your request: {exchange.request}</p>}
      {!!exchange.memories?.length && <Disclosure label="Earlier notes used for this reply">{exchange.memories.map(m => <div key={m.id}><p>{m.title} · saved version {m.version} · personal writing</p><blockquote className="whitespace-pre-wrap border-l-2 pl-3">{m.text}</blockquote></div>)}</Disclosure>}
      {!exchange.answer.source_quotes?.length && <p className="text-warn">Source support unavailable — this reply needs checking.</p>}
      {exchange.answer.discussion && <Markdown text={exchange.answer.discussion} />}
      <Disclosure label={`Sources (${exchange.answer.source_quotes?.length ?? 0})`}>
        {(exchange.answer.source_quotes ?? []).map((quote, i) => <blockquote key={i} className="whitespace-pre-wrap border-l-2 pl-3">{quote}</blockquote>)}
        {!exchange.answer.source_quotes?.length && <p className="text-warn">No source passages were supplied with this reply. Check its claims against your materials before using it.</p>}
        {!!exchange.answer.source_quotes?.length && <p className="text-sm text-muted">Quoted source content is evidence to inspect, not independent verification of every claim.</p>}
      </Disclosure>
      {exchange.answer.needs_check && <div><p className="font-semibold">Needs checking</p><Markdown text={exchange.answer.needs_check} /></div>}
      {exchange.answer.next_question && <div><p className="font-semibold">One possible next step</p><Markdown text={exchange.answer.next_question} /></div>}
      {exchange.answer.section && <div><p className="font-semibold">Proposed section — review before using</p><Markdown text={exchange.answer.section} /></div>}
    </div>
  }
  return <section aria-labelledby={headingId} className="space-y-3 rounded border border-line p-3">
    <h4 id={headingId} className="font-semibold">Discuss and build with your {hosted ? 'OpenAI authoring' : 'local'} tutor</h4>
    <p>Write your findings first. Ask about one point, or request one editable paragraph. The tutor uses this passage and your notes; saved links are not opened or independently verified.</p>
    <label>What I want help with<textarea className="block w-full rounded border border-line bg-card p-2" rows={2} maxLength={2000} value={question.tutor_request ?? ''} disabled={disabled} onChange={e => onChange({ ...question, tutor_request: e.target.value })} /></label>
    {!question.prompt.trim() && <p>Complete the research question before asking the tutor. Earlier replies are kept.</p>}
    {!question.findings.trim() && <p id={requirementsId}>Add My findings in Research before asking the tutor. Your current section and earlier replies are kept.</p>}
    {onTutor && <div className="flex flex-wrap gap-2">
      <Button aria-describedby={sourceChanged ? sourceChangedDescription : !question.findings.trim() ? requirementsId : undefined} disabled={disabled || sourceChanged || !question.prompt.trim() || !question.findings.trim() || history.length >= 12} onClick={() => onTutor('discuss')}>{hosted ? 'Discuss my findings with OpenAI' : 'Discuss my findings locally'}</Button>
      <Button variant="secondary" aria-describedby={sourceChanged ? sourceChangedDescription : !question.findings.trim() ? requirementsId : undefined} disabled={disabled || sourceChanged || !question.prompt.trim() || !question.findings.trim() || history.length >= 12} onClick={() => onTutor('draft-section')}>{hosted ? 'Draft one section with OpenAI' : 'Draft one section locally'}</Button>
      {latest && !latest.calculation && !latest.reference && <Button variant="secondary" aria-describedby={sourceChanged ? sourceChangedDescription : !question.findings.trim() ? requirementsId : undefined} disabled={disabled || sourceChanged || !question.prompt.trim() || !question.findings.trim() || history.length >= 12} onClick={() => onTutor(latest.action === 'draft' ? 'draft-section' : 'discuss', true)}>Ask for another reply</Button>}
    </div>}
    <p className="text-sm text-muted">{latest?.reference ? 'This saved reply is labelled as reference-based. Add a different request above to discuss a broader question with the tutor.' : latest?.calculation ? 'This saved reply is labelled as a calculation. Add a request above to discuss a broader question with the tutor.' : 'An unchanged request can reuse its saved reply. Choose Ask for another reply to generate a fresh alternative.'}</p>
    {history.length >= 12 && latest?.cache_token && !changed && question.tutor_basis === basis && latest.request === (question.tutor_request ?? '') && onTutor && <Button disabled={disabled || sourceChanged || !question.prompt.trim() || !question.findings.trim()} aria-describedby={sourceChanged ? sourceChangedDescription : undefined} onClick={() => onTutor(latest.action === 'draft' ? 'draft-section' : 'discuss')}>Reuse saved reply</Button>}
    {history.length >= 12 && <p>This question has 12 saved tutor replies. You can read them below or reuse an eligible unchanged reply. Add another research question for a new reply.</p>}
    {history.length > 1 && <Disclosure label={`Earlier tutor replies (${history.length - 1})`}>
      {history.slice(0, -1).map((exchange, i) => <div className="my-3 border-b border-line pb-3" key={i}><p className="font-semibold">Reply {i + 1}</p>{reply(exchange)}</div>)}
    </Disclosure>}
    {latest && <div className="space-y-3">
      <h5 className="font-semibold">Latest tutor reply</h5>
      {!latest.calculation && !latest.reference && <p className="text-sm text-muted">Saved AI suggestion; source quotations locate its evidence and do not verify every claim.</p>}
      {changed && <p role="status">The research text has changed since this reply. Your current writing is kept; ask again if you want an updated suggestion.</p>}
      {reply(latest)}
      {latest.answer.section && <Button aria-describedby={sourceChanged ? sourceChangedDescription : undefined} disabled={disabled || sourceChanged || changed || question.section === latest.answer.section} onClick={() => { onChange({ ...question, section: latest.answer.section }); onUseDraft?.() }}>
        {question.section ? 'Replace my section with tutor draft' : 'Use tutor draft in my section'}
      </Button>}
      <p className="text-sm text-muted">In Write, edit My knowledge section, then choose Add section to explanation. Saving or using a draft does not activate a lesson or count as mastery.</p>
    </div>}
  </section>
}
