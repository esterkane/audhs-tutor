import { useEffect, useRef } from 'react'
import { Button } from '../../components/ui/button'
import { Disclosure } from '../../components/ui/disclosure'
import type { Schemas } from '../../lib/api'
import { useDraftRecovery } from './useDraftRecovery'
type Trace = Schemas['StateTrace']
const field = 'block w-full rounded border p-2'
const blankStep = () => ({ action: '', value: '' })
export function TraceAuthoring({
  value,
  disabled,
  onChange,
}: {
  value: Trace | null
  disabled: boolean
  onChange: (v: Trace | null) => void
}) {
  const steps = value?.steps ?? []
  function updateStep(i: number, key: 'action' | 'value', text: string) {
    if (value)
      onChange({
        ...value,
        steps: steps.map((step, index) => (index === i ? { ...step, [key]: text } : step)),
      })
  }
  return (
    <Disclosure label="Variable walkthrough (optional)">
      <label>
        <input
          type="checkbox"
          disabled={disabled}
          checked={!!value}
          onChange={(e) =>
            onChange(
              e.target.checked
                ? {
                    variable: '',
                    initial: '',
                    steps: [blankStep(), blankStep()],
                    transfer_question: '',
                    transfer_answer: '',
                  }
                : null,
            )
          }
        />{' '}
        Add a variable walkthrough
      </label>
      {value && (
        <fieldset disabled={disabled} className="space-y-2">
          <legend>Track one value through the example</legend>
          <label className="block">
            Variable name
            <input
              className={field}
              maxLength={100}
              value={value.variable ?? ''}
              onChange={(e) => onChange({ ...value, variable: e.target.value })}
            />
          </label>
          <label className="block">
            Starting value
            <input
              className={field}
              maxLength={300}
              value={value.initial ?? ''}
              onChange={(e) => onChange({ ...value, initial: e.target.value })}
            />
          </label>
          {steps.map((s, i) => (
            <fieldset key={i}>
              <legend>Step {i + 1}</legend>
              <label className="block">
                Action at step {i + 1}
                <input
                  className={field}
                  maxLength={500}
                  value={s.action ?? ''}
                  onChange={(e) => updateStep(i, 'action', e.target.value)}
                />
              </label>
              <label className="block">
                Value after step {i + 1}
                <input
                  className={field}
                  maxLength={300}
                  value={s.value ?? ''}
                  onChange={(e) => updateStep(i, 'value', e.target.value)}
                />
              </label>
            </fieldset>
          ))}
          <Button
            disabled={steps.length >= 8}
            onClick={() => onChange({ ...value, steps: [...steps, blankStep()] })}
          >
            Add a step
          </Button>
          {steps.length > 2 && (
            <Button onClick={() => onChange({ ...value, steps: steps.slice(0, -1) })}>
              Remove last step
            </Button>
          )}
          <label className="block">
            Transfer question with one changed condition
            <input
              className={field}
              maxLength={500}
              value={value.transfer_question ?? ''}
              onChange={(e) => onChange({ ...value, transfer_question: e.target.value })}
            />
          </label>
          <label className="block">
            Author’s answer to the transfer question
            <input
              className={field}
              maxLength={500}
              value={value.transfer_answer ?? ''}
              onChange={(e) => onChange({ ...value, transfer_answer: e.target.value })}
            />
          </label>
        </fieldset>
      )}
    </Disclosure>
  )
}
type Attempt = { step: number; revealed: number; predictions: string[] }
function readAttempt(raw: string, count: number): Attempt | null {
  try {
    const s = JSON.parse(raw)
    if (
      !Number.isInteger(s.step) ||
      s.step < 0 ||
      s.step >= count ||
      !Number.isInteger(s.revealed) ||
      s.revealed < s.step ||
      s.revealed > count ||
      !Array.isArray(s.predictions) ||
      s.predictions.length !== count ||
      !s.predictions.every((p: unknown) => typeof p === 'string' && p.length <= 500)
    )
      return null
    return s
  } catch {
    return null
  }
}
export function TracePractice({ value, identity }: { value: Trace; identity: string }) {
  const steps = value.steps ?? []
  const count = steps.length + 1
  const initial = JSON.stringify({ step: 0, revealed: 0, predictions: Array<string>(count).fill('') })
  const saved = useDraftRecovery('state-trace:' + identity, 1, initial)
  const state = readAttempt(saved.text, count)
  const heading = useRef<HTMLHeadingElement>(null)
  const focus = useRef(false)
  useEffect(() => {
    if (focus.current) {
      heading.current?.focus()
      focus.current = false
    }
  }, [state?.step, state?.revealed])
  function change(s: Attempt, move = false) {
    focus.current = move
    saved.edit(JSON.stringify(s))
  }
  const index = state?.step ?? 0
  const transfer = index === steps.length
  const before = index === 0 ? value.initial : steps[index - 1]?.value
  const after = steps[index]?.value
  const revealed = !!state && state.revealed > index
  return (
    <Disclosure label="Trace a changing value">
      {!state || saved.error?.startsWith('Earlier recovery') ? (
        <p role="alert">
          This saved walkthrough could not be read.{' '}
          <Button onClick={() => saved.reset(initial, 1)}>Restart walkthrough</Button>
        </p>
      ) : (
        <section className="space-y-2" aria-label="Variable walkthrough">
          <h3 tabIndex={-1} ref={heading}>
            {transfer
              ? 'Transfer: apply the idea'
              : `Step ${index + 1} of ${steps.length}: ${value.variable}`}
          </h3>
          {transfer ? (
            <p>{value.transfer_question}</p>
          ) : (
            <>
              <p>
                Previous value: <strong>{before}</strong>
              </p>
              <p>{steps[index]?.action}</p>
            </>
          )}
          {revealed ? (
            <>
              {state.predictions[index] && (
                <p className="whitespace-pre-wrap">Your original prediction: {state.predictions[index]}</p>
              )}
              {transfer ? (
                <p>Author’s answer: {value.transfer_answer}</p>
              ) : (
                <p>
                  {after === before ? 'Value stayed the same' : 'Value changed'}: {before} → {after}
                </p>
              )}
            </>
          ) : (
            <>
              <label className="block">
                Your prediction (optional)
                <input
                  className={field}
                  maxLength={500}
                  value={state.predictions[index]}
                  onChange={(e) =>
                    change({
                      ...state,
                      predictions: state.predictions.map((p, i) => (i === index ? e.target.value : p)),
                    })
                  }
                />
              </label>
              <Button onClick={() => change({ ...state, revealed: index + 1 }, true)}>
                {transfer ? 'Show author’s answer' : 'Reveal next value'}
              </Button>
            </>
          )}
          <div className="flex flex-wrap gap-2">
            {index > 0 && (
              <Button onClick={() => change({ ...state, step: index - 1 }, true)}>Previous step</Button>
            )}
            {revealed && !transfer && (
              <Button onClick={() => change({ ...state, step: index + 1 }, true)}>
                {index === steps.length - 1 ? 'Try the transfer question' : 'Next step'}
              </Button>
            )}
            {index > 0 && (
              <Button onClick={() => change({ ...state, step: 0 }, true)}>Replay from the start</Button>
            )}
          </div>
        </section>
      )}
      {saved.error && <p role="alert">{saved.error}</p>}
    </Disclosure>
  )
}
