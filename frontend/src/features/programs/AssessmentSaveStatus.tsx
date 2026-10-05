import { AnswerSaveStatus } from './AnswerSaveStatus'
import type { AttemptResult } from '../../lib/api'

export function AssessmentSaveStatus({ result, onSaved }: {
  result: AttemptResult
  onSaved?: (answerId: string) => void
}) {
  return (
    <AnswerSaveStatus
      answerId={result.answer_id}
      error={result.save_error}
      receipt={result.save_receipt}
      text={`${result.feedback}\n\n${result.next_step}`}
      linkLabel="Open saved feedback"
      onSaved={onSaved}
    />
  )
}
