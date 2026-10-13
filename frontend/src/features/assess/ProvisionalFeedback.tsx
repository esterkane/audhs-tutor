import type { ProvisionalFeedbackResult } from '../../lib/api'
import { ReadAloud } from '../voice/ReadAloud'

export function ProvisionalFeedback({ result, active = true }: { result: ProvisionalFeedbackResult; active?: boolean }) {
  const spoken = ['Model feedback — not an assessed result.', result.feedback, ...result.criterion_feedback.map(c => `${c.criterion}: ${c.observation}`), result.next_step].join('\n\n')
  return <section aria-label="Provisional model feedback" className="grid gap-3">
    <h3 className="font-medium">Model feedback — not an assessed result</h3>
    <p>This feedback may be mistaken. It does not change mastery or your review schedule.</p>
    <p className="whitespace-pre-wrap">{result.feedback}</p>
    {result.criterion_feedback.length > 0 && <details><summary>Model observations against the rubric</summary>
      <ul className="list-disc ml-5">{result.criterion_feedback.map((c, i) => <li key={i}><strong>{c.criterion}</strong>: {c.observation}</li>)}</ul>
    </details>}
    <p className="whitespace-pre-wrap">{result.next_step}</p>
    <p className="text-sm text-muted">Feedback saved locally. You can continue without a pass.</p>
    {active && <ReadAloud text={spoken} label="Listen to feedback" />}
  </section>
}
