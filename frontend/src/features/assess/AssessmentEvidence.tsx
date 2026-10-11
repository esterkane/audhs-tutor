import type { AttemptResult } from '../../lib/api'

/** Present recorded grader evidence without inferring additional success or failure. */
export function AssessmentEvidence({ result }: { result: Pick<AttemptResult, 'criterion_results' | 'feedback' | 'misconception' | 'next_step'> }) {
  return (
    <div className="grid gap-3 mt-3">
      {result.criterion_results.length === 0 && (
        <p className="text-sm text-muted">This check did not provide a criterion-by-criterion breakdown.</p>
      )}
      {[true, false].map(passed => {
        const criteria = result.criterion_results.filter(c => c.passed === passed)
        if (!criteria.length) return null
        return <section key={String(passed)} aria-label={passed ? 'What was right' : 'What to reconsider'}>
          <h4 className="font-medium">{passed ? 'What was right' : 'What to reconsider'}</h4>
          <ul className="list-disc ml-5 mt-1">
            {criteria.map((c, index) => <li key={index}>{c.criterion}{c.evidence ? ` — ${c.evidence}` : ''}</li>)}
          </ul>
        </section>
      })}
      <section aria-label="Why">
        <h4 className="font-medium">Why</h4>
        <p className="mt-1">{result.feedback}</p>
        {result.misconception && <p className="mt-1 text-sm text-warn">Possible misconception: {result.misconception}</p>}
      </section>
      {result.next_step && <p>{result.next_step}</p>}
    </div>
  )
}
