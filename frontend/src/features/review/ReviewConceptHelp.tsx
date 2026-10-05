import { useState } from 'react'
import { QuestionHelp } from '../assess/QuestionHelp'

export function ReviewConceptHelp({ sessionId, skillId, question, active }: {
  sessionId: string
  skillId: string
  question: string
  active: boolean
}) {
  const [open, setOpen] = useState(false)
  const [opened, setOpened] = useState(false)
  return (
    <details className="mt-3" onToggle={event => {
      const next = event.currentTarget.open
      setOpen(next)
      if (next) setOpened(true)
    }}>
      <summary>Help understanding this card</summary>
      {opened && <QuestionHelp
        sessionId={sessionId}
        skillId={skillId}
        question={question}
        afterAnswer
        active={open && active}
        afterAnswerNote="This explanation does not record a review rating. Rate how you recalled the answer before revealing it."
      />}
    </details>
  )
}
