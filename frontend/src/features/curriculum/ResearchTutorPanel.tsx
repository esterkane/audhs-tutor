import type { Schemas } from '../../lib/api'
import { Button } from '../../components/ui/button'
import { Disclosure } from '../../components/ui/disclosure'
import { Markdown } from '../../components/Markdown'

type Research = Schemas['KnowledgeResearch']
type Question = Schemas['ResearchQuestion']

export function ResearchTutorPanel({ research, question, disabled, sourceChanged, onChange, onTutor, onUseDraft }: {
  research: Research; question: Question; disabled: boolean; sourceChanged: boolean
  onUseDraft?: () => void; onChange: (question: Question) => void; onTutor?: (action: 'discuss' | 'draft-section', refresh?: boolean) => void
}) {
  const history = question.tutor_exchanges ?? []
  const latest = history.at(-1)
  const basis = JSON.stringify({ passage: research.passage, topic: research.topic, question: question.prompt,
    findings: question.findings, evidence: question.evidence, unresolved: question.unresolved, section: question.section })
  const changed = !!latest && (question.tutor_basis !== basis || JSON.stringify(question.memory_ids ?? []) !== JSON.stringify((latest.memories ?? []).map(m => m.id)))
  function reply(exchange: Schemas['ResearchTutorExchange']) {
    return <div className="space-y-2">
      {exchange.request && <p className="whitespace-pre-wrap">Your request: {exchange.request}</p>}
      {!!exchange.memories?.length && <Disclosure label="Earlier notes used for this reply">{exchange.memories.map(m => <div key={m.id}><p>{m.title} · saved version {m.version} · personal writing</p><blockquote className="whitespace-pre-wrap border-l-2 pl-3">{m.text}</blockquote></div>)}</Disclosure>}
      {exchange.answer.discussion && <Markdown text={exchange.answer.discussion} />}
      {!!exchange.answer.source_quotes?.length && <Disclosure label="Source evidence">
        {exchange.answer.source_quotes.map((quote, i) => <blockquote key={i} className="whitespace-pre-wrap border-l-2 pl-3">{quote}</blockquote>)}
      </Disclosure>}
      {exchange.answer.needs_check && <div><p className="font-semibold">Needs checking</p><Markdown text={exchange.answer.needs_check} /></div>}
      {exchange.answer.next_question && <div><p className="font-semibold">One possible next step</p><Markdown text={exchange.answer.next_question} /></div>}
      {exchange.answer.section && <div><p className="font-semibold">Proposed section — review before using</p><Markdown text={exchange.answer.section} /></div>}
    </div>
  }
  return <section aria-label="Local research tutor" className="space-y-3 rounded border border-line p-3">
    <h4 className="font-semibold">Discuss and build with your local tutor</h4>
    <p>Write your findings first. Ask about one point, or request one editable paragraph. The tutor uses this passage and your notes; saved links are not opened or independently verified.</p>
    <label>What I want help with<textarea className="block w-full rounded border border-line bg-card p-2" rows={2} maxLength={2000} value={question.tutor_request ?? ''} disabled={disabled} onChange={e => onChange({ ...question, tutor_request: e.target.value })} /></label>
    {onTutor && <div className="flex flex-wrap gap-2">
      <Button disabled={disabled || sourceChanged || !question.findings.trim() || history.length >= 12} onClick={() => onTutor('discuss')}>Discuss my findings locally</Button>
      <Button variant="secondary" disabled={disabled || sourceChanged || !question.findings.trim() || history.length >= 12} onClick={() => onTutor('draft-section')}>Draft one section locally</Button>
      {latest && <Button variant="secondary" disabled={disabled || sourceChanged || !question.findings.trim() || history.length >= 12} onClick={() => onTutor(latest.action === 'draft' ? 'draft-section' : 'discuss', true)}>Ask for another reply</Button>}
    </div>}
    <p className="text-sm text-muted">An unchanged request can reuse its saved reply. Choose Ask for another reply to generate a fresh alternative.</p>
    {history.length >= 12 && <p>This question has 12 saved tutor replies. Keep them and add another research question to continue.</p>}
    {history.length > 1 && <Disclosure label={`Earlier tutor replies (${history.length - 1})`}>
      {history.slice(0, -1).map((exchange, i) => <div className="my-3 border-b border-line pb-3" key={i}><p className="font-semibold">Reply {i + 1}</p>{reply(exchange)}</div>)}
    </Disclosure>}
    {latest && <div className="space-y-3">
      <h5 className="font-semibold">Latest tutor reply</h5>
      <p className="text-sm text-muted">Saved AI suggestion; source quotations locate its evidence and do not verify every claim.</p>
      {changed && <p role="status">The research text has changed since this reply. Your current writing is kept; ask again if you want an updated suggestion.</p>}
      {reply(latest)}
      {latest.answer.section && <Button disabled={disabled || sourceChanged || changed || question.section === latest.answer.section} onClick={() => { onChange({ ...question, section: latest.answer.section }); onUseDraft?.() }}>
        {question.section ? 'Replace my section with tutor draft' : 'Use tutor draft in my section'}
      </Button>}
      <p className="text-sm text-muted">Edit My knowledge section above, then choose Add section to explanation. Saving or using a draft does not activate a lesson or count as mastery.</p>
    </div>}
  </section>
}
