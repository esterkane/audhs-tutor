import { useId, useState, type ReactNode } from 'react'
import { Button } from '../../components/ui/button'

type Reflection = '' | 'confirmed' | 'partly' | 'changed'
type Attempt = { prediction: string; revealed: boolean; reflection: Reflection; correction: string; prompt?: string }
const fresh: Attempt = { prediction: '', revealed: false, reflection: '', correction: '' }
function valid(value: unknown): value is Attempt {
  const v = value as Attempt
  return !!v && typeof v.prediction === 'string' && typeof v.revealed === 'boolean' &&
    ['', 'confirmed', 'partly', 'changed'].includes(v.reflection) && typeof v.correction === 'string' && (v.prompt === undefined || typeof v.prompt === 'string')
}

/** A local, ungraded attempt; never writes mastery, assessment or tutor history. */
export function PredictionReading(props: { identity: string; title: string; resumeKeyPrefix?: string; question?: string; resumeReading?: boolean; children: ReactNode }) {
  return <Prediction key={props.identity} {...props} />
}
function Prediction({ identity, title, resumeKeyPrefix, question, resumeReading, children }: { identity: string; title: string; resumeKeyPrefix?: string; question?: string; resumeReading?: boolean; children: ReactNode }) {
  const key = `reading-prediction:v1:${identity}`
  const id = useId()
  const [initial] = useState(() => {
    try {
      const raw = localStorage.getItem(key)
      if (raw === null) {
        const resuming = resumeReading || (!!resumeKeyPrefix && Array.from({ length: localStorage.length }, (_, i) => localStorage.key(i))
          .some(savedKey => savedKey?.startsWith(resumeKeyPrefix)))
        return { attempt: { ...fresh, revealed: resuming }, status: resuming
          ? 'Continuing your saved reading. Existing notes and position are unchanged.'
          : 'Your prediction stays in this browser, not in tutor history.' }
      }
      const value: unknown = JSON.parse(raw)
      if (!valid(value)) throw new Error('Invalid prediction')
      return { attempt: value, status: 'Saved prediction and comparison restored from this browser.' }
    } catch {
      // Never hide learning material behind unavailable or invalid storage.
      return { attempt: { ...fresh, revealed: true }, status: 'Could not restore the prediction. Reading is available; copy any new notes before leaving.' }
    }
  })
  const [attempt, setAttempt] = useState(initial.attempt)
  const [status, setStatus] = useState(initial.status)
  function save(next: Attempt) {
    next = { ...next, prompt: question ?? 'What do you expect this topic to explain?' }
    setAttempt(next)
    try {
      localStorage.setItem(key, JSON.stringify(next))
      setStatus('Prediction and comparison saved in this browser. These are not grades.')
    } catch {
      setStatus('Could not save the prediction. It is still here; copy it before leaving.')
    }
  }
  return <section aria-label="Predict, read and compare" className="space-y-3">
    {!attempt.revealed ? <>
      <h3 className="font-semibold">Before reading: {title}</h3>
      <p>{question ?? 'What do you expect this topic to explain? Name one term or mechanism.'} A guess is enough; it is not graded.</p>
      <label htmlFor={`${id}-prediction`} className="block">Your prediction (optional)</label>
      <textarea id={`${id}-prediction`} className="block w-full border border-line rounded p-2" value={attempt.prediction}
        onChange={e => save({ ...attempt, prediction: e.target.value })} />
      <div className="flex flex-wrap gap-2">
        <Button disabled={!attempt.prediction.trim()} onClick={() => save({ ...attempt, revealed: true })}>Save prediction and read</Button>
        <Button variant="secondary" onClick={() => save({ ...attempt, revealed: true })}>Read without predicting</Button>
      </div>
    </> : <>
      {children}
      {attempt.prediction.trim() && <fieldset className="space-y-2 border border-line rounded p-3">
        <legend>Compare after reading</legend>
        {question && <p className="font-medium">{attempt.prompt ?? question}</p>}
        <p className="text-sm">Your original prediction (kept unchanged):</p>
        <p className="whitespace-pre-wrap">{attempt.prediction}</p>
        <p>Compare it with the explanation above. This is your reflection, not an accuracy check or mastery score.</p>
        <label htmlFor={`${id}-reflection`}>How did your prediction compare?</label>
        <select id={`${id}-reflection`} className="block w-full" value={attempt.reflection}
          onChange={e => save({ ...attempt, reflection: e.target.value as Reflection })}>
          <option value="">Not compared yet</option>
          <option value="confirmed">Confirmed by the explanation</option>
          <option value="partly">Partly confirmed</option>
          <option value="changed">My explanation changed</option>
        </select>
        <label htmlFor={`${id}-correction`} className="block">What changed, and which passage helped? (optional)</label>
        <textarea id={`${id}-correction`} className="block w-full border border-line rounded p-2" value={attempt.correction}
          onChange={e => save({ ...attempt, correction: e.target.value })} />
      </fieldset>}
    </>}
    <p role="status" className="text-sm">{status}</p>
  </section>
}
