import { useEffect, useId, useRef, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Button } from '../../components/ui/button'
import { Card, CardTitle } from '../../components/ui/card'
import { boundedRead } from '../../lib/boundedRead'

import type { components } from '../../lib/api-types'

type Cue = components['schemas']['DuePrediction']
type Completed = components['schemas']['CompletedRecall']
const base = '/api/reading-predictions'

export function PassageRecall() {
  const cache = useQueryClient()
  const due = useQuery({
    queryKey: ['passage-recall-due'],
    retry: false,
    refetchOnWindowFocus: false,
    queryFn: ({ signal }) => boundedRead<Cue | null>(base + '/due', signal, 'Due passage recall'),
  })
  const [receipt, setReceipt] = useState<Completed | null>(null)
  const [historyOpen, setHistoryOpen] = useState(false)
  const history = useQuery({
    queryKey: ['latest-passage-recall'],
    retry: false,
    enabled: historyOpen,
    queryFn: ({ signal }) =>
      boundedRead<Completed | null>(base + '/latest-recall', signal, 'Last saved recall'),
  })
  const completed = receipt ?? (historyOpen ? history.data : null)
  const completedId = completed?.id
  const resultHeading = useRef<HTMLHeadingElement>(null)
  useEffect(() => {
    if (completedId) resultHeading.current?.focus()
  }, [completedId])
  async function next() {
    await due.refetch()
    setReceipt(null)
    setHistoryOpen(false)
  }
  return (
    <Card className="space-y-3">
      <CardTitle as="h1">Passage recall</CardTitle>
      {completed ? (
        <>
          <h2 ref={resultHeading} tabIndex={-1} className="font-semibold">
            {completed.title}
          </h2>
          <p>{completed.question}</p>
          <h3 className="font-semibold">Your saved recall</h3>
          <p className="whitespace-pre-wrap">{completed.answer}</p>
          <h3 className="font-semibold">Your original prediction</h3>
          <p className="whitespace-pre-wrap">{completed.prediction}</p>
          <h3 className="font-semibold">Accepted passage at the time</h3>
          <p className="whitespace-pre-wrap">{completed.passage}</p>
          <p>Compare your answers in your own words. This recall is ungraded.</p>
          <Button disabled={due.isFetching} onClick={() => void next()}>
            Check for another passage
          </Button>
        </>
      ) : historyOpen ? (
        <>
          {history.isPending ? (
            <p role="status">Loading saved recall…</p>
          ) : history.isError ? (
            <Button onClick={() => void history.refetch()}>Retry saved recall</Button>
          ) : (
            <p>No completed passage recall yet.</p>
          )}
          <Button onClick={() => setHistoryOpen(false)}>Back to due passages</Button>
        </>
      ) : due.isPending ? (
        <p role="status">Checking due passages…</p>
      ) : due.isError ? (
        <p role="alert">
          Could not load due passages. <Button onClick={() => void due.refetch()}>Retry due passages</Button>
        </p>
      ) : due.data ? (
        <RecallAttempt
          key={due.data.id}
          cue={due.data}
          onRefresh={() => void due.refetch()}
          onComplete={(result) => {
            setReceipt(result)
            cache.setQueryData(['latest-passage-recall'], result)
            void cache.invalidateQueries({ queryKey: ['passage-recall-due'] })
          }}
        />
      ) : (
        <>
          <p>No passage recall is due. Saved predictions become available for recall after a day.</p>
          <Button disabled={due.isFetching} onClick={() => void due.refetch()}>
            Check due passages
          </Button>
        </>
      )}
      {!completed && !historyOpen && (
        <Button onClick={() => setHistoryOpen(true)}>View last saved recall</Button>
      )}
      <Link className="block underline" to="/review">
        Back to review cards
      </Link>
    </Card>
  )
}

function RecallAttempt({
  cue,
  onComplete,
  onRefresh,
}: {
  cue: Cue
  onRefresh: () => void
  onComplete: (result: Completed) => void
}) {
  const questionId = useId()
  const key = 'passage-recall-draft:v1:' + cue.id
  const [answer, setAnswer] = useState(() => {
    try {
      return sessionStorage.getItem(key) ?? ''
    } catch {
      return ''
    }
  })
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  async function submit() {
    setSaving(true)
    setError('')
    try {
      const result = await boundedRead<Completed>(
        base + '/' + encodeURIComponent(cue.id) + '/recall',
        new AbortController().signal,
        'Saving recall',
        {
          method: 'POST',
          body: JSON.stringify({ answer }),
        },
      )
      try {
        sessionStorage.removeItem(key)
      } catch {
        /* The server has confirmed the saved answer. */
      }
      onComplete(result)
    } catch (cause) {
      setError(
        cause instanceof Error ? cause.message : 'Could not confirm your recall. Retry the same answer.',
      )
    } finally {
      setSaving(false)
    }
  }
  return (
    <div className="space-y-3">
      <h2 className="font-semibold">Recall from memory</h2>
      <p id={questionId}>{cue.question}</p>
      <label className="block">
        Your recall answer
        <textarea
          className="block w-full rounded border border-line p-2"
          aria-describedby={questionId}
          rows={4}
          value={answer}
          disabled={saving}
          maxLength={4000}
          onChange={(event) => {
            const text = event.target.value
            setAnswer(text)
            try {
              sessionStorage.setItem(key, text)
            } catch {
              setError('Your draft is available on this page. Keep it open until you save.')
            }
          }}
        />
      </label>
      <Button disabled={saving || !answer.trim()} onClick={() => void submit()}>
        {saving ? 'Saving recall…' : 'Save recall and compare'}
      </Button>
      {error && (
        <>
          <p role="alert">{error}</p>
          <Button onClick={onRefresh}>Refresh due passages</Button>
        </>
      )}
    </div>
  )
}
