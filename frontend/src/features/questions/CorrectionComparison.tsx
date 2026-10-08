import type { Schemas } from '../../lib/api'

type Candidate = Schemas['SaveCorrectionDraft']['candidate']
function record(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : {}
}
function display(value: unknown): string {
  if (value === undefined) return 'Not present'
  if (typeof value === 'string') return value || '(empty text)'
  return JSON.stringify(value, null, 2)
}
function canonical(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(canonical)
  if (value && typeof value === 'object') return Object.fromEntries(Object.entries(value).sort(([a], [b]) => a.localeCompare(b)).map(([key, child]) => [key, canonical(child)]))
  return value
}
const labels: Record<string, string> = { question: 'Question wording', prompt: 'Question wording', text: 'Question wording', options: 'Answer options', answer: 'Correct answer index (starts at 0)', answers: 'Accepted answers', explanation: 'Answer explanation', hidden_key: 'Reference answer', criteria: 'Question criteria' }

export function CorrectionComparison({ before, after, beforeLabel, afterLabel }: {
  before: Candidate; after: Candidate; beforeLabel: string; afterLabel: string
}) {
  const left = record(before.item); const right = record(after.item)
  const structured = before.item === left && after.item === right
  const fields = [
    ...(!structured ? [{ key: 'item', label: 'Question payload (incomplete or unstructured)', before: before.item, after: after.item }] : []),
    ...Array.from(new Set([...Object.keys(left), ...Object.keys(right)])).map(key => ({ key: `item.${key}`, label: labels[key] ?? `Question metadata: ${key}`, before: left[key], after: right[key] })),
    ...Array.from(new Set([...Object.keys(before), ...Object.keys(after)])).filter(key => key !== 'item').map(key => ({ key, label: key === 'rubric' ? 'Grading rubric' : `Draft metadata: ${key}`, before: before[key], after: after[key] })),
  ].filter(field => JSON.stringify(canonical(field.before)) !== JSON.stringify(canonical(field.after)))
  return <div className="grid gap-3 min-w-0">
    {fields.length === 0 ? <p>No question or rubric changes compared with {beforeLabel.toLowerCase()}.</p> : <>
      <p>{fields.length} changed field(s). Review both versions; this comparison does not check correctness or publish anything.</p>
      {fields.map(field => <section key={field.key} className="grid gap-2 min-w-0 border border-line rounded p-3">
        <h4 className="font-semibold">{field.label}</h4>
        <div className="grid gap-3 min-w-0 md:grid-cols-2">
          {[{ label: beforeLabel, value: field.before }, { label: afterLabel, value: field.after }].map(({ label, value }) => <div key={label} className="min-w-0">
            <p className="font-medium">{label}</p><pre className="whitespace-pre-wrap break-words text-sm">{display(value)}</pre>
          </div>)}
        </div>
      </section>)}
    </>}
  </div>
}
