import { useEffect, useId, useRef, useState } from 'react'
import type { Schemas } from '../../lib/api'
import { Button } from '../../components/ui/button'
import { Disclosure } from '../../components/ui/disclosure'

type Pair = NonNullable<Schemas['KnowledgeMaterialInput']['case_comparison']>
type Attempt = {
  choice: '' | 'a' | 'b'
  reasoning: string
  revealed: boolean
  detail_a?: string
  detail_b?: string
}
const empty: Attempt = { choice: '', reasoning: '', revealed: false }

export function CaseAuthoring({
  pair,
  onChange,
  disabled,
}: {
  pair: Pair | null
  onChange: (value: Pair | null) => void
  disabled: boolean
}) {
  return (
    <Disclosure label="Compare two cases (optional)">
      <fieldset disabled={disabled} className="space-y-3">
        <legend className="sr-only">Case comparison</legend>
        <label>
          <input
            type="checkbox"
            checked={!!pair}
            onChange={(event) =>
              onChange(
                event.target.checked
                  ? { case_a: '', case_b: '', failing_case: null, rationale: '', comparison_focus: '' }
                  : null,
              )
            }
          />{' '}
          Include a case comparison
        </label>
        {pair && (
          <>
            {(['case_a', 'case_b'] as const).map((key, index) => (
              <label className="block" key={key}>
                Case {index ? 'B' : 'A'}
                <textarea
                  className="block w-full border rounded p-2"
                  rows={3}
                  maxLength={4000}
                  value={pair[key]}
                  onChange={(e) => onChange({ ...pair, [key]: e.target.value })}
                />
              </label>
            ))}
            <label className="block">
              What should the learner compare? (optional)
              <textarea
                className="block w-full border rounded p-2"
                rows={2}
                maxLength={300}
                placeholder="Name a detail to look for in both cases. Leave the outcome for the explanation."
                value={pair.comparison_focus ?? ''}
                onChange={(e) => onChange({ ...pair, comparison_focus: e.target.value })}
              />
            </label>
            <label className="block">
              Which case fails?
              <select
                className="block"
                value={pair.failing_case ?? ''}
                onChange={(e) =>
                  onChange({
                    ...pair,
                    failing_case: e.target.value === 'a' ? 'a' : e.target.value === 'b' ? 'b' : null,
                  })
                }
              >
                <option value="">Choose a case</option>
                <option value="a">Case A</option>
                <option value="b">Case B</option>
              </select>
            </label>
            <label className="block">
              Why does that case fail?
              <textarea
                className="block w-full border rounded p-2"
                rows={3}
                maxLength={4000}
                value={pair.rationale}
                onChange={(e) => onChange({ ...pair, rationale: e.target.value })}
              />
            </label>
          </>
        )}
      </fieldset>
    </Disclosure>
  )
}

export function CasePractice({
  pair,
  identity,
  lowCapacity = false,
}: {
  pair: NonNullable<Schemas['KnowledgeReadingOut']['case_comparison']>
  identity: string
  lowCapacity?: boolean
}) {
  const key = 'case-comparison:v1:' + identity
  const [attempt, setAttempt] = useState<Attempt>(() => {
    try {
      const stored = JSON.parse(localStorage.getItem(key) ?? 'null')
      if (
        stored &&
        ['', 'a', 'b'].includes(stored.choice) &&
        typeof stored.reasoning === 'string' &&
        typeof stored.revealed === 'boolean'
      )
        return {
          choice: stored.choice,
          reasoning: stored.reasoning,
          revealed: stored.revealed,
          detail_a: typeof stored.detail_a === 'string' ? stored.detail_a : '',
          detail_b: typeof stored.detail_b === 'string' ? stored.detail_b : '',
        }
    } catch {
      /* Start a fresh attempt if storage is unavailable. */
    }
    return empty
  })
  const [detailed, setDetailed] = useState(false)
  const quick =
    lowCapacity &&
    !detailed &&
    !attempt.revealed &&
    !attempt.choice &&
    !attempt.reasoning &&
    !attempt.detail_a &&
    !attempt.detail_b
  const [error, setError] = useState('')
  const group = useId()
  const result = useRef<HTMLHeadingElement>(null)
  const focusAfterReveal = useRef(false)
  useEffect(() => {
    if (attempt.revealed && focusAfterReveal.current) result.current?.focus()
  }, [attempt.revealed])
  function save(value: Attempt) {
    setAttempt(value)
    try {
      localStorage.setItem(key, JSON.stringify(value))
      setError('')
    } catch {
      setError('Your attempt is available on this page. Copy it before leaving.')
    }
  }
  function reveal(choice = attempt.choice) {
    focusAfterReveal.current = true
    save({ ...attempt, choice, revealed: true })
  }
  return (
    <Disclosure label={lowCapacity ? 'Two-choice practice' : 'Compare two cases'}>
      <div className="space-y-3 min-w-0">
        {!quick &&
          (['case_a', 'case_b'] as const).map((key, index) => (
            <section key={key}>
              <h3 className="font-semibold">Case {index ? 'B' : 'A'}</h3>
              <p className="whitespace-pre-wrap break-words">{pair[key]}</p>
            </section>
          ))}
        {attempt.revealed ? (
          <>
            <h3 className="font-semibold" ref={result} tabIndex={-1}>
              Compare with the author’s explanation
            </h3>
            {attempt.choice && <p>Your choice: Case {attempt.choice.toUpperCase()}</p>}
            {attempt.reasoning && (
              <p className="whitespace-pre-wrap break-words">Your reasoning: {attempt.reasoning}</p>
            )}
            {(['detail_a', 'detail_b'] as const).map(
              (key, index) =>
                attempt[key] && (
                  <p key={key} className="whitespace-pre-wrap break-words">
                    Your detail from Case {index ? 'B' : 'A'}: {attempt[key]}
                  </p>
                ),
            )}
            <p>The author identifies Case {pair.failing_case.toUpperCase()} as the failing case.</p>
            <p className="whitespace-pre-wrap break-words">{pair.rationale}</p>
          </>
        ) : quick ? (
          <fieldset className="grid gap-2">
            <legend>Which case fails?</legend>
            <p className="text-sm">Choose one to see the author’s explanation. This practice is ungraded.</p>
            {(['a', 'b'] as const).map((choice) => (
              <Button
                key={choice}
                variant="secondary"
                className="whitespace-normal break-words text-left justify-start"
                onClick={() => reveal(choice)}
              >
                Case {choice.toUpperCase()}: {pair[choice === 'a' ? 'case_a' : 'case_b']}
              </Button>
            ))}
            <Button variant="ghost" onClick={() => setDetailed(true)}>
              Compare in detail
            </Button>
          </fieldset>
        ) : (
          <>
            <Disclosure label="Help me compare the cases">
              {pair.comparison_focus ? (
                <p className="whitespace-pre-wrap break-words">{pair.comparison_focus}</p>
              ) : (
                <p>
                  Look for a condition or action that differs between the cases. Note one detail from each,
                  then use the difference to explain your choice.
                </p>
              )}
              {(['detail_a', 'detail_b'] as const).map((key, index) => (
                <label key={key} className="block">
                  Relevant detail from Case {index ? 'B' : 'A'} (optional)
                  <textarea
                    className="block w-full border rounded p-2"
                    rows={2}
                    maxLength={1000}
                    value={attempt[key] ?? ''}
                    onChange={(e) => save({ ...attempt, [key]: e.target.value })}
                  />
                </label>
              ))}
            </Disclosure>
            <fieldset>
              <legend>Which case fails?</legend>
              {(['a', 'b'] as const).map((value) => (
                <label key={value} className="mr-3">
                  <input
                    type="radio"
                    name={group}
                    checked={attempt.choice === value}
                    onChange={() => save({ ...attempt, choice: value })}
                  />{' '}
                  Case {value.toUpperCase()}
                </label>
              ))}
            </fieldset>
            <label className="block">
              Why does it fail? (optional)
              <textarea
                className="block w-full border rounded p-2"
                rows={3}
                value={attempt.reasoning}
                onChange={(e) => save({ ...attempt, reasoning: e.target.value })}
              />
            </label>
            <p>This ungraded attempt is saved in this browser.</p>
            <Button disabled={!attempt.choice} onClick={() => reveal()}>
              Compare with explanation
            </Button>
            <Button variant="secondary" onClick={() => reveal()}>
              Skip to explanation
            </Button>
          </>
        )}
        {error && <p role="alert">{error}</p>}
      </div>
    </Disclosure>
  )
}
