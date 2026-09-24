import { useEffect, useRef } from 'react'
import { Button } from '../../components/ui/button'
import { Markdown } from '../../components/Markdown'
import { useTutorStream } from '../tutor/useTutorStream'
import { ReadAloud } from '../voice/ReadAloud'

export function QuestionHelp({
  sessionId,
  skillId,
  question,
  onHint,
}: {
  sessionId: string
  skillId: string | null
  question: string
  onHint: () => void
}) {
  const tutor = useTutorStream()
  const counted = useRef<string | null>(null)
  useEffect(() => {
    if (tutor.text && tutor.meta && counted.current !== tutor.meta.turn_id) {
      counted.current = tutor.meta.turn_id
      onHint()
    }
  }, [tutor.text, tutor.meta, onHint])
  return (
    <div className="border border-line rounded-md p-3 my-3">
      <p className="text-sm mb-2">You can learn before answering. Help keeps your answer in place.</p>
      <div className="flex gap-2 flex-wrap">
        <Button
          disabled={tutor.busy}
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
        <Button
          disabled={tutor.busy}
          onClick={() => {
            void tutor.run({
              session_id: sessionId,
              skill_id: skillId,
              action: 'explain',
              text: `Explain the concept needed for this question, why it matters, and one similar example. Do not solve the question itself: ${question}`,
            })
          }}
        >
          Explain the idea first
        </Button>
        {tutor.busy && <Button onClick={tutor.stop}>Stop explanation</Button>}
      </div>
      {tutor.text && (
        <div className="mt-3">
          <Markdown text={tutor.text} />
          {!tutor.busy && <ReadAloud key={tutor.text} text={tutor.text} />}
        </div>
      )}
      {tutor.done && (
        <p className="text-xs text-muted mt-2">
          {tutor.done.sources.length
            ? tutor.done.sources.map((s) => s.citation).join(' · ')
            : 'No course source for this explanation.'}
        </p>
      )}
      {tutor.error && <p role="alert">{tutor.error}</p>}
    </div>
  )
}
