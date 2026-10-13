import { AnswerSaveStatus } from './AnswerSaveStatus'
import { isProvisional, type AttemptResult, type AssessedResult } from '../../lib/api'

export function AssessmentSaveStatus({ result, onSaved }: {
  result: AttemptResult
  onSaved?: (answerId: string) => void
}) {
  if (isProvisional(result)) return <p className="text-sm">Model feedback saved locally; no assessed result was recorded.</p>
  return (
    <>
    <AssessmentPracticeNotice result={result} />
    <AnswerSaveStatus
      answerId={result.answer_id}
      error={result.save_error}
      receipt={result.save_receipt}
      text={`${result.feedback}\n\n${result.next_step}`}
      linkLabel="Open saved feedback"
      onSaved={onSaved}
    />
    </>
  )
}

export function AssessmentPracticeNotice({ result }: { result: Pick<AssessedResult, 'revision_of_attempt_id'> }) {
  return result.revision_of_attempt_id ? <p className="mt-2 text-sm">Repeated practice on a previously checked question. This does not add independent learning evidence or change your review schedule.</p> : null
}
