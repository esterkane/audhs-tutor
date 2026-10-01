import { useState } from 'react'
import { Button } from '../../components/ui/button'
import { Card, CardTitle } from '../../components/ui/card'
import { Choice } from '../../components/ui/choice'
import { useLogPractice } from '../practice/api'
import { VoicePanel } from './VoicePanel'

/**
 * Spoken conversation practice inside the language block (P9). Casual practice is logged as
 * `practiced` with a self-rating — it is exposure, never competency evidence. Assessment happens
 * elsewhere (the listening tasks and vocabulary cards keep their confidence-before-feedback path).
 */
export function ConversationBlock({
  sessionId,
  lang,
  onDone,
  makeSocket,
}: {
  sessionId: string
  lang: string
  onDone: () => void
  makeSocket?: (url: string) => WebSocket
}) {
  const log = useLogPractice()
  const [phase, setPhase] = useState<'talk' | 'rate'>('talk')
  const [rating, setRating] = useState<number | null>(null)
  const [startedAt] = useState(() => Date.now())
  if (phase === 'talk') {
    return (
      <div className="grid gap-3">
        <VoicePanel
          sessionId={sessionId}
          lang={lang}
          conversation
          title={`Conversation practice (${lang.toUpperCase()})`}
          makeSocket={makeSocket}
          onClose={() => setPhase('rate')}
        />
        <p className="text-xs text-muted">
          Practice only: nothing here is graded or counted as mastery. The tutor answers from general
          knowledge here, not from your course sources. Press “Stop voice” when you are done.
        </p>
      </div>
    )
  }
  return (
    <Card>
      <CardTitle>Conversation ended — how much of it could you do?</CardTitle>
      <Choice<number>
        label="Rate this block (1 = mostly could not answer, 5 = kept the conversation going)"
        options={[1, 2, 3, 4, 5].map((n) => ({ value: n, label: String(n) }))}
        value={rating ?? 0}
        onChange={setRating}
        columns={5}
      />
      <div className="flex gap-2 mt-3">
        <Button
          variant="primary"
          disabled={!rating || log.isPending}
          onClick={() =>
            void log
              .mutateAsync({
                session_id: sessionId,
                domain: 'language',
                activity: `conversation:${lang}`,
                duration_min: Math.max(0, Math.round(((Date.now() - startedAt) / 60_000) * 10) / 10),
                self_rating: rating!,
                notes: null,
              })
              .then(onDone)
          }
        >
          Log as practice and continue
        </Button>
        <Button variant="ghost" onClick={onDone}>
          Skip logging
        </Button>
      </div>
    </Card>
  )
}
