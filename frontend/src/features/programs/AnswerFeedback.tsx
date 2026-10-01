import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'
import { apiFetch, ApiError, type Schemas } from '../../lib/api'
import { Button } from '../../components/ui/button'
type State = Schemas['AnswerFeedbackState']

export function AnswerFeedback({ answerId }: { answerId: string }) {
  const query = useQuery({
    queryKey: ['answer-feedback', answerId],
    queryFn: ({ signal }) =>
      apiFetch<State>(`/api/answers/${encodeURIComponent(answerId)}/feedback`, { signal }),
  })
  return (
    <section className="border border-line rounded p-4 grid gap-2" aria-label="Your feedback on this answer">
      <h2 className="font-semibold">Your feedback on this answer</h2>
      <p className="text-sm text-muted">
        Your report does not verify the answer, train a model or change your learning score. Incorrect,
        outdated and hidden replies are excluded from contextual lists, but kept in history.
      </p>
      {query.isPending ? (
        <p role="status">Loading feedback…</p>
      ) : query.isError ? (
        <p role="alert">
          Could not load feedback. <Button onClick={() => void query.refetch()}>Retry feedback</Button>
        </p>
      ) : (
        <>
          {(query.data.verdict === 'incorrect' || query.data.verdict === 'outdated') && (
            <p role="alert">
              You marked this answer {query.data.verdict}. Treat it cautiously before continuing from it.
            </p>
          )}
          {query.data.hidden && <p>Hidden from contextual lists. You can restore it below.</p>}
          <Editor key={answerId} answerId={answerId} saved={query.data} />
        </>
      )}
    </section>
  )
}
function Editor({ answerId, saved }: { answerId: string; saved: State }) {
  const key = `answer-feedback-draft:v1:${answerId}`
  const [restored] = useState(() => {
    try {
      const value = JSON.parse(localStorage.getItem(key) ?? 'null')
      if (!value) return { value: saved, error: '' }
      if (
        !['helpful', 'confusing', 'incorrect', 'outdated', null].includes(value.verdict) ||
        typeof value.note !== 'string' ||
        value.note.length > 2000 ||
        typeof value.hidden !== 'boolean' ||
        !Number.isInteger(value.revision)
      )
        throw new Error('Invalid draft')
      return { value: value as State, error: '' }
    } catch {
      return { value: saved, error: 'Draft could not be restored. Keep a copy of your edits.' }
    }
  })
  const [draft, setDraft] = useState<State>(restored.value)
  const [storageError, setStorageError] = useState(restored.error)
  const [error, setError] = useState('')
  const [status, setStatus] = useState('')
  const [busy, setBusy] = useState(false)
  const alive = useRef(true)
  useEffect(() => {
    alive.current = true
    return () => {
      alive.current = false
    }
  }, [alive])
  const qc = useQueryClient()
  function edit(value: State) {
    setDraft(value)
    setStatus('')
    try {
      localStorage.setItem(key, JSON.stringify(value))
      setStorageError('')
    } catch {
      setStorageError('Draft could not be saved locally. Keep a copy before leaving.')
    }
  }
  async function save() {
    if (busy) return
    setBusy(true)
    setError('')
    setStatus('')
    try {
      const result = await apiFetch<State>(`/api/answers/${encodeURIComponent(answerId)}/feedback`, {
        method: 'PUT',
        body: JSON.stringify(draft),
      })
      if (!alive.current) return
      setDraft(result)
      try {
        localStorage.removeItem(key)
      } catch {
        setStorageError('Feedback saved, but the local draft could not be cleared.')
      }
      qc.setQueryData(['answer-feedback', answerId], result)
      void qc.invalidateQueries({ queryKey: ['answers'] })
      setStatus('Feedback saved.')
    } catch (cause) {
      if (alive.current)
        setError(
          cause instanceof ApiError && cause.status === 409
            ? 'Feedback changed in another tab. Your draft is kept. Review the latest saved version before trying again.'
            : 'Could not save feedback. Your draft is kept; retry when ready.',
        )
    } finally {
      if (alive.current) setBusy(false)
    }
  }
  return (
    <div className="grid gap-2">
      <label>
        How was this answer?
        <select
          className="block"
          value={draft.verdict ?? ''}
          disabled={busy}
          onChange={(event) => edit({ ...draft, verdict: (event.target.value || null) as State['verdict'] })}
        >
          <option value="">No label</option>
          <option value="helpful">Helpful</option>
          <option value="confusing">Confusing</option>
          <option value="incorrect">Incorrect</option>
          <option value="outdated">Outdated</option>
        </select>
      </label>
      <label>
        Why? (optional)
        <textarea
          className="block w-full border rounded bg-card p-2"
          maxLength={2000}
          rows={3}
          value={draft.note}
          disabled={busy}
          onChange={(event) => edit({ ...draft, note: event.target.value })}
        />
      </label>
      <label>
        <input
          type="checkbox"
          checked={draft.hidden}
          disabled={busy}
          onChange={(event) => edit({ ...draft, hidden: event.target.checked })}
        />{' '}
        Hide from contextual lists
      </label>
      <div className="flex gap-2 flex-wrap">
        <Button disabled={busy} onClick={() => void save()}>
          {busy ? 'Saving feedback…' : 'Save feedback'}
        </Button>
        <Button
          disabled={busy}
          onClick={async () => {
            setBusy(true)
            try {
              const latest = await apiFetch<State>(`/api/answers/${encodeURIComponent(answerId)}/feedback`)
              if (alive.current) {
                qc.setQueryData(['answer-feedback', answerId], latest)
                edit({ ...draft, revision: latest.revision })
                setStatus(
                  `Latest saved label: ${latest.verdict ?? 'none'}; hidden: ${latest.hidden ? 'yes' : 'no'}. Saved reason: ${latest.note || '(none)'}. Your draft is unchanged.`,
                )
              }
            } catch {
              if (alive.current) setError('Could not load the latest feedback.')
            } finally {
              if (alive.current) setBusy(false)
            }
          }}
        >
          Review latest saved feedback
        </Button>
      </div>
      {status && <p role="status">{status}</p>}
      {error && <p role="alert">{error}</p>}
      {storageError && <p role="alert">{storageError}</p>}
    </div>
  )
}
