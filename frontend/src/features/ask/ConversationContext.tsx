import { briefFields, useSavedBrief } from './conversationBrief'
import { Disclosure } from '../../components/ui/disclosure'

function record(value: unknown): Record<string, unknown> | null {
  return value !== null && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : null
}

export function ConversationContext({ metadata }: { metadata: Record<string, unknown> }) {
  const window = record(metadata.context_window)
  const retained = useSavedBrief(metadata)
  const brief = retained.value
  const briefEnvelope = record(metadata.conversation_brief)
  const opening = record(metadata.opening_context)
  if (!window || window.version !== 1) return null
  return <Disclosure label="Context used for this answer" className="my-3">
    {briefEnvelope?.mode === 'cleared' && <p>Retained notes were cleared for this answer. Earlier exchanges remain history.</p>}
    {(briefEnvelope?.mode === 'unavailable' || (retained.ready && !!briefEnvelope?.value && !brief)) && <p>Retained notes were unavailable and were not reconstructed.</p>}
    {brief && briefEnvelope?.mode !== 'cleared' && <section aria-label="Retained notes used for this answer" className="mb-3">
      <p className="text-sm text-muted">Learner-provided context, not verified evidence.</p>
      {briefFields.map(([key, label]) => brief[key] && <div key={key} className="mt-2">
        <p className="font-medium">{label}</p><p className="whitespace-pre-wrap break-words">{brief[key]}</p>
      </div>)}
    </section>}
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
