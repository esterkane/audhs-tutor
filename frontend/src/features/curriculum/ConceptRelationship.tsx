import { useId, useRef, useEffect } from 'react'
import { Button } from '../../components/ui/button'
import { Disclosure } from '../../components/ui/disclosure'
import type { Schemas } from '../../lib/api'
import { useDraftRecovery } from './useDraftRecovery'

type Relationship = Schemas['ConceptRelationship']
const field = 'block w-full rounded border border-line bg-card p-2'

export function RelationshipAuthoring({
  value,
  disabled,
  onChange,
}: {
  value: Relationship | null
  disabled: boolean
  onChange: (value: Relationship | null) => void
}) {
  return (
    <Disclosure label="Concept relationship (optional)">
      <label>
        <input
          type="checkbox"
          disabled={disabled}
          checked={!!value}
          onChange={(e) => onChange(e.target.checked ? { source: '', link: '', target: '' } : null)}
        />{' '}
        Add a relationship to practise
      </label>
      {value && (
        <fieldset className="grid gap-2">
          <legend>Build a statement in reading order</legend>
          <p>
            Choose two concepts from this lesson. At practice time, the learner can supply the linking phrase
            or complete the ending concept.
          </p>
          {(
            [
              ['source', 'Starting concept'],
              ['link', 'Linking phrase'],
              ['target', 'Ending concept'],
            ] as const
          ).map(([key, label]) => (
            <label key={key}>
              {label}
              <input
                className={field}
                disabled={disabled}
                maxLength={key === 'link' ? 1000 : 300}
                value={value[key] ?? ''}
                onChange={(e) => onChange({ ...value, [key]: e.target.value })}
              />
            </label>
          ))}
        </fieldset>
      )}
    </Disclosure>
  )
}

const empty = JSON.stringify({ answer: '', revealed: false })

export function RelationshipPractice({ value, identity }: { value: Relationship; identity: string }) {
  const choice = useDraftRecovery('concept-relationship-part:' + identity, 1, 'link')
  const label = choice.text === 'target'
  return (
    <Disclosure label="Connect two concepts">
      <label className="block">
        Part to complete
        <select
          className={field}
          value={label ? 'target' : 'link'}
          onChange={(e) => choice.edit(e.target.value)}
        >
          <option value="link">Linking phrase</option>
          <option value="target">Ending concept</option>
        </select>
      </label>
      <CompleteRelationship key={choice.text} value={value} identity={identity} label={label} />
      {choice.error && <p role="alert">{choice.error}</p>}
    </Disclosure>
  )
}

function CompleteRelationship({
  value,
  identity,
  label,
}: {
  value: Relationship
  identity: string
  label: boolean
}) {
  // The original linking-phrase storage key also restores attempts saved before label practice existed.
  const key = label ? 'concept-relationship-target:' : 'concept-relationship:'
  const saved = useDraftRecovery(key + identity, 1, empty)
  const promptId = useId()
  const feedback = useRef<HTMLHeadingElement>(null)
  const moveFocus = useRef(false)
  let answer = ''
  let revealed = false
  let valid = true
  try {
    const state = JSON.parse(saved.text)
    if (typeof state.answer !== 'string' || typeof state.revealed !== 'boolean') throw new Error()
    answer = state.answer
    revealed = state.revealed
  } catch {
    valid = false
  }
  useEffect(() => {
    if (revealed && moveFocus.current) {
      feedback.current?.focus()
      moveFocus.current = false
    }
  }, [revealed])
  function reveal() {
    moveFocus.current = true
    saved.edit(JSON.stringify({ answer, revealed: true }))
  }

  return (
    <section aria-label="Practise a concept relationship" className="grid gap-2">
      <p id={promptId}>
        {label ? (
          <>
            Complete the ending concept: <strong>{value.source}</strong> {value.link} …
          </>
        ) : (
          <>
            How does <strong>{value.source}</strong> connect to <strong>{value.target}</strong>? Write a
            linking phrase in that direction.
          </>
        )}
      </p>
      {!valid ? (
        <p role="alert">
          This tab’s saved attempt could not be read.{' '}
          <Button variant="secondary" onClick={() => saved.reset(empty, 1)}>
            Restart relationship practice
          </Button>
        </p>
      ) : revealed ? (
        <>
          <h3 tabIndex={-1} ref={feedback}>
            Compare the relationships
          </h3>
          {answer && (
            <p className="whitespace-pre-wrap">
              <strong>Your statement</strong>
              <br />
              {value.source} {label ? value.link : answer} {label ? answer : value.target}
            </p>
          )}
          <p className="whitespace-pre-wrap">
            <strong>Authored statement</strong>
            <br />
            {value.source} {value.link} {value.target}
          </p>
          <p>Different wording can express the same relationship. Compare the meaning.</p>
        </>
      ) : (
        <>
          <label>
            {label ? 'Your ending concept' : 'Your linking phrase'}
            <textarea
              className={field}
              maxLength={label ? 300 : 1000}
              aria-describedby={promptId}
              value={answer}
              onChange={(e) => saved.edit(JSON.stringify({ answer: e.target.value, revealed: false }))}
            />
          </label>
          <div className="flex flex-wrap gap-2">
            <Button disabled={!answer.trim()} onClick={reveal}>
              Compare my relationship
            </Button>
            {!answer.trim() && (
              <Button variant="secondary" onClick={reveal}>
                Show the authored relationship
              </Button>
            )}
          </div>
        </>
      )}
      {saved.error && <p role="alert">{saved.error}</p>}
    </section>
  )
}
