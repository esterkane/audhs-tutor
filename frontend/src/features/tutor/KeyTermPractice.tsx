import { useEffect, useId, useRef, useState, type ReactNode } from 'react'
import { Button } from '../../components/ui/button'

type Stage = 'reading' | 'choose' | 'recall' | 'compare'

export function KeyTermPractice({ passage, playback }: { passage: ReactNode; playback: ReactNode }) {
  const [stage, setStage] = useState<Stage>('reading')
  const [selection, setSelection] = useState('')
  const [answer, setAnswer] = useState('')
  const [error, setError] = useState('')
  const source = useRef<HTMLDivElement>(null)
  const heading = useRef<HTMLHeadingElement>(null)
  const focusRequested = useRef(false)
  const id = useId()
  const terms = selection
    .split('\n')
    .map((term) => term.trim())
    .filter(Boolean)
  useEffect(() => {
    if (focusRequested.current)
      (stage === 'reading' ? document.getElementById(id + '-start') : heading.current)?.focus()
  }, [stage, id])
  function move(next: Stage) {
    focusRequested.current = true
    setError('')
    setStage(next)
  }
  function beginRecall() {
    const text = source.current?.innerText ?? ''
    if (
      terms.length < 3 ||
      terms.length > 5 ||
      new Set(terms).size !== terms.length ||
      terms.some((term) => term.length > 80 || !text.includes(term))
    ) {
      setError(
        'Choose three to five different short terms or steps. Copy each exactly from the passage, one per line.',
      )
      return
    }
    setAnswer('')
    move('recall')
  }
  return (
    <>
      {stage !== 'recall' && (
        <>
          <div ref={source}>{passage}</div>
          {playback}
        </>
      )}
      {stage === 'reading' ? (
        <Button id={id + '-start'} variant="secondary" onClick={() => move('choose')}>
          Practise key terms
        </Button>
      ) : (
        <section aria-labelledby={id} className="my-3 space-y-3">
          <h4 id={id} ref={heading} tabIndex={-1} className="font-semibold">
            {stage === 'choose'
              ? 'Choose terms from this passage'
              : stage === 'recall'
                ? 'Recall your terms'
                : 'Compare with your terms'}
          </h4>
          {stage === 'choose' && (
            <>
              <p>
                Choose three to five terms or short steps. Say them aloud if you like, or read them silently.
              </p>
              <label className="block">
                Terms to practise (one per line)
                <textarea
                  className="block w-full rounded border p-2"
                  rows={5}
                  maxLength={404}
                  value={selection}
                  onChange={(e) => {
                    setSelection(e.target.value)
                    setError('')
                  }}
                />
              </label>
              {error && <p role="alert">{error}</p>}
              <Button onClick={beginRecall}>Hide passage and recall</Button>
            </>
          )}
          {stage === 'recall' && (
            <>
              <p>Which terms do you remember? Speak to yourself or type below.</p>
              <label className="block">
                What I recall (optional)
                <textarea
                  className="block w-full rounded border p-2"
                  rows={3}
                  value={answer}
                  onChange={(e) => setAnswer(e.target.value)}
                />
              </label>
              <Button onClick={() => move('compare')}>Show my terms</Button>
            </>
          )}
          {stage === 'compare' && (
            <>
              <ul className="list-disc pl-5">
                {terms.map((term) => (
                  <li key={term}>{term}</li>
                ))}
              </ul>
              {answer && <p className="whitespace-pre-wrap">Your recall: {answer}</p>}
              <Button
                variant="secondary"
                onClick={() => {
                  setAnswer('')
                  move('recall')
                }}
              >
                Recall again
              </Button>
            </>
          )}
          <Button
            variant="secondary"
            onClick={() => {
              setSelection('')
              setAnswer('')
              move('reading')
            }}
          >
            Finish practice
          </Button>
        </section>
      )}
    </>
  )
}
