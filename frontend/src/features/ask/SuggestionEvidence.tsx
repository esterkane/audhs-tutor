import type { Schemas } from '../../lib/api'

export function SuggestionEvidence({ answer, matching }: {
  answer: Schemas['AnswerSummary']
  matching: boolean
}) {
  const check = answer.source_check
  const reasons = check ? [
    check.omitted > 0 && 'some sources were not checked',
    check.sources.some(s => s.status === 'missing') && 'source text is missing',
    check.sources.some(s => s.status === 'changed') && 'source text changed',
    check.sources.some(s => s.status === 'unverifiable') && 'source hashes are unavailable',
    check.sources.some(s => s.newer_version) && 'a newer local source version exists',
  ].filter(Boolean) : []
  const sourceLabel = !check
    ? 'Source status unavailable'
    : reasons.length
      ? `Source review needed: ${reasons.join('; ')}`
      : check.sources.length
        ? 'Recorded source text unchanged locally'
        : 'No recorded sources to check'
  return (
    <div className="basis-full text-sm text-muted space-y-1">
      <p>{matching ? 'Local question match' : 'Recent saved question'} · Saved {new Date(answer.created_at).toLocaleDateString()}</p>
      <p>{sourceLabel}. Not fact-checked.</p>
      {answer.context_dependent && <p>Uses earlier conversation. Read it in context before reusing.</p>}
    </div>
  )
}
