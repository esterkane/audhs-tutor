import { Disclosure } from '../../components/ui/disclosure'

function record(value: unknown): Record<string, unknown> | null {
  return value !== null && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : null
}

export function ConversationContext({ metadata }: { metadata: Record<string, unknown> }) {
  const window = record(metadata.context_window)
  const opening = record(metadata.opening_context)
  if (!window || window.version !== 1) return null
  return <Disclosure label="Context used for this answer" className="my-3">
    {opening && typeof opening.question === 'string' && <>
      <p className="font-medium">Conversation’s opening question</p>
      <p className="whitespace-pre-wrap break-words">{opening.question}</p>
      <p className="text-sm text-muted">Historical learner input, not verified source evidence. You can change direction in your next question.</p>
    </>}
    {window.opening_unavailable === true && <p>The opening question was unavailable. It was not reconstructed.</p>}
    {window.older_exchanges_omitted === true && <p className="mt-2">Older intervening exchanges were omitted. The tutor received up to three recent exchanges; restate an earlier detail if it matters now.</p>}
    <p className="text-sm text-muted mt-2">Source passages must be selected for each reply. Earlier answers and their citations are conversation history, not newly checked evidence.</p>
  </Disclosure>
}
