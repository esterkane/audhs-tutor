import { useEffect, useRef } from 'react'
import { Button } from '../../components/ui/button'
import { Markdown } from '../../components/Markdown'
import { TutorSources } from '../tutor/TutorSources'
import { TutorResponseStatus } from '../tutor/TutorResponseStatus'
import { useTutorStream } from '../tutor/useTutorStream'
import { ReadAloud } from '../voice/ReadAloud'

export function QuestionHelp({
  active = true,
  sessionId,
  skillId,
  question,
  onHint,
  afterAnswer = false,
  afterAnswerNote,
}: {
  sessionId: string
  skillId: string | null
  question: string
  onHint?: () => void
  afterAnswer?: boolean
  afterAnswerNote?: string
  active?: boolean
}) {
  const tutor = useTutorStream()
  const { stop } = tutor
  useEffect(() => {
    if (!active) stop()
  }, [active, stop])
  const counted = useRef<string | null>(null)
  useEffect(() => {
    if (tutor.text && tutor.meta && counted.current !== tutor.meta.turn_id) {
      counted.current = tutor.meta.turn_id
      if (!afterAnswer) onHint?.()
    }
  }, [tutor.text, tutor.meta, onHint, afterAnswer])
  return (
    <div className="border border-line rounded-md p-3 my-3">
      <p className="text-sm mb-2">
        {afterAnswer
          ? afterAnswerNote ?? 'Still unclear? Review the idea here. Your recorded feedback stays unchanged.'
          : 'You can learn before answering. Help keeps your answer in place.'}
      </p>
      <div className="flex gap-2 flex-wrap">
        {!afterAnswer && (
          <Button
            disabled={tutor.busy || !active}
            onClick={() => {
              void tutor.run({
                session_id: sessionId,
                skill_id: skillId,
                action: 'hint',
                text: `Give one small hint for this question, without revealing the answer: ${question}`,
              })
            }}
          >
            Give me a hint
          </Button>
        )}
        <Button
          disabled={tutor.busy || !active}
          onClick={() => {
            void tutor.run({
              session_id: sessionId,
              skill_id: skillId,
              action: 'explain',
              text: `Explain the concept needed for this question, why it matters, and one similar example. Do not solve the question itself: ${question}`,
            })
          }}
        >
          {afterAnswer ? "I don't understand yet — explain the idea" : 'Explain the idea first'}
        </Button>
        {tutor.busy && <Button onClick={tutor.stop}>Stop explanation</Button>}
      </div>
      <TutorResponseStatus status={tutor.status} startedAt={tutor.startedAt} />
      {tutor.text && (
        <div className="mt-3">
          <Markdown text={tutor.text} />
          {active && !tutor.busy && <ReadAloud key={tutor.text} text={tutor.text} />}
        </div>
      )}
      {tutor.done && <TutorSources turn={tutor.done} />}
      {tutor.error && <p role="alert">{tutor.error}</p>}
    </div>
  )
}
