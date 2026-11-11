import type { Schemas } from '../lib/api'

type Draft = Schemas['DraftOut']
function object(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? (value as Record<string, unknown>) : {}
}
function list(value: unknown): unknown[] {
  return Array.isArray(value) ? value : []
}
function match(term: string, ...fields: unknown[]): boolean {
  return fields.some((value) => typeof value === 'string' && value.toLocaleLowerCase().includes(term))
}

export function matchesDraft(row: Draft, term: string) {
  const a = object(row.payload.authoring)
  const research = object(a.research)
  const pair = object(a.case_comparison)
  return (
    match(
      term,
      row.title,
      a.title,
      a.notes,
      a.objective,
      a.explanation,
      a.worked_example,
      a.question,
      ...list(a.criteria),
      a.explanation_prequestion,
      a.worked_example_prequestion,
      pair.case_a,
      pair.case_b,
      pair.rationale,
      research.topic,
      research.passage,
    ) ||
    list(research.questions).some((item) => {
      const q = object(item)
      return match(term, q.prompt, q.findings, q.evidence, q.unresolved, q.section, q.source_quote)
    })
  )
}
