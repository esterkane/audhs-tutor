function record(value: unknown): Record<string, unknown> {
  return value != null && typeof value === 'object' && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {}
}

export function AssessmentHistoryDetails({ metadata }: { metadata: Record<string, unknown> }) {
  const question = record(metadata.assessment_question)
  const result = record(metadata.assessment_result)
  const options = Array.isArray(question.options)
    ? question.options.filter((v): v is string => typeof v === 'string')
    : []
  const criteria = Array.isArray(result.criterion_results) ? result.criterion_results.map(record) : []
  return (
    <section className="grid gap-2">
      <h2 className="font-semibold">Feedback on your past attempt</h2>
      <p>
        These results belong to the answer you submitted then. Reopening does not grade again, update your
        current mastery or schedule another review. Personal assessment feedback is excluded from suggested
        answers.
      </p>
      <details>
        <summary>Question and grading details at the time</summary>
        {typeof question.question === 'string' && <p className="whitespace-pre-wrap">{question.question}</p>}
        {options.length > 0 && (
          <ol className="list-decimal ml-5">
            {options.map((option, index) => (
              <li key={index}>{option}</li>
            ))}
          </ol>
        )}
        {typeof result.score === 'number' && <p>Score on this attempt: {Math.round(result.score * 100)}%</p>}
        {typeof result.grader_level === 'string' && <p>Grading method: {result.grader_level}</p>}
        <ul>
          {criteria.map((criterion, index) => (
            <li key={index}>
              {criterion.passed === true ? 'Met' : criterion.passed === false ? 'Not met' : 'Unknown'}:{' '}
              {typeof criterion.criterion === 'string' ? criterion.criterion : 'Criterion unavailable'}
              {typeof criterion.evidence === 'string' && criterion.evidence && <p>{criterion.evidence}</p>}
            </li>
          ))}
        </ul>
        <p>
          Source passages were not captured with this grading result. A recorded grade is not proof that every
          claim is correct.
        </p>
      </details>
    </section>
  )
}
