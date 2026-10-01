import { AnswerFeedback } from '../features/programs/AnswerFeedback'
import { AnswerFollowup } from '../features/programs/AnswerFollowup'
import { useQuery } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { Markdown } from '../components/Markdown'
import { Button } from '../components/ui/button'
import { Card } from '../components/ui/card'
import { SourceViewer } from '../features/curriculum/SourceViewer'
import { withheldCount } from '../features/tutor/sourceFlags'
import { ReadAloud } from '../features/voice/ReadAloud'
import { ApiError, apiFetch, type Schemas } from '../lib/api'

export function Answers() {
  const { answerId } = useParams()
  return answerId ? <Answer key={answerId} id={answerId} /> : <History />
}

function History() {
  const [params, setParams] = useSearchParams()
  const appliedSearch = params.get('q') ?? ''
  const [search, setSearch] = useState(appliedSearch)
  const [previousSearch, setPreviousSearch] = useState(appliedSearch)
  if (previousSearch !== appliedSearch) {
    setPreviousSearch(appliedSearch)
    setSearch(appliedSearch)
  }
  const query = new URLSearchParams()
  for (const key of [
    'cursor',
    'skill_id',
    'area_id',
    'surface',
    'q',
    'course_id',
    'section_id',
    'target_id',
  ]) {
    const value = params.get(key)
    if (value) query.set(key, value)
  }
  query.set('limit', '20')
  const history = useQuery({
    queryKey: ['answers', query.toString()],
    queryFn: ({ signal }) => apiFetch<Schemas['AnswerPage']>(`/api/answers?${query}`, { signal }),
  })
  const update = (key: string, value: string) => {
    const next = new URLSearchParams(params)
    next.delete('cursor')
    if (value) next.set(key, value)
    else next.delete(key)
    setParams(next)
  }
  return (
    <div className="grid gap-4">
      <h1 className="text-2xl font-semibold">Saved answers</h1>
      <p>
        Reopen explanations you already received. Reopening them does not generate a new tutor response or
        change your progress. Listening is optional.
      </p>
      <p className="text-sm text-muted">
        Saved answers can be mistaken or outdated. Notebook advice belongs to the code and material supplied
        at the time. Suggested questions are coming next.
      </p>
      <form
        className="flex flex-wrap gap-2 items-end"
        onSubmit={(event) => {
          event.preventDefault()
          update('q', search.trim())
        }}
      >
        <label className="min-w-0">
          Search saved answers
          <input
            type="search"
            className="block mt-1 w-full"
            maxLength={200}
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            aria-describedby="answer-search-help"
          />
        </label>
        <Button type="submit">Search</Button>
        {params.get('q') && (
          <Button
            type="button"
            onClick={() => {
              setSearch('')
              update('q', '')
            }}
          >
            Clear search
          </Button>
        )}
      </form>
      <p id="answer-search-help" className="text-sm text-muted">
        Searches saved requests and answers on this device. All words must match; newest first. Code, output
        and earlier chat are not searched.
      </p>
      <label>
        Show
        <select
          className="block mt-1"
          value={params.get('surface') ?? ''}
          onChange={(e) => update('surface', e.target.value)}
        >
          <option value="">All saved answers</option>
          <option value="tutor">Lessons and hints</option>
          <option value="playground">Notebook and coding help</option>
        </select>
      </label>
      {['area_id', 'skill_id', 'course_id', 'section_id', 'target_id'].some((key) => params.get(key)) && (
        <p>
          Filtered to the selected learning context. <Link to="/answers">Show all answers</Link>
        </p>
      )}
      {history.isPending ? (
        <p role="status">Loading saved answers…</p>
      ) : history.isError ? (
        <div role="alert">
          Could not load saved answers. <Button onClick={() => void history.refetch()}>Retry history</Button>
        </div>
      ) : (
        <>
          {history.data.items.length === 0 && (
            <p>
              No saved answers in this view yet. Completed tutor replies are saved as you learn; earlier
              browser-only chats are not automatically imported.
            </p>
          )}
          <ol className="grid gap-3">
            {history.data.items.map((answer) => (
              <li key={answer.id}>
                <Card className="min-w-0 break-words">
                  <Link to={`/answers/${encodeURIComponent(answer.id)}?${params}`} className="font-medium">
                    {answer.request_text
                      ? answer.request_text.slice(0, 180) + (answer.request_text.length > 180 ? '…' : '')
                      : 'Explanation requested'}
                  </Link>
                  <p className="text-xs text-muted mt-1">
                    {answer.surface === 'playground' ? 'Notebook / coding help' : 'Lesson / hint'} ·{' '}
                    {new Date(answer.created_at).toLocaleString()}
                  </p>
                  <p className="mt-2 whitespace-pre-wrap">{answer.preview}</p>
                </Card>
              </li>
            ))}
          </ol>
          <div className="flex gap-3">
            {params.get('cursor') && <Button onClick={() => update('cursor', '')}>Newest answers</Button>}
            {history.data.next_cursor && (
              <Button
                onClick={() => {
                  const next = new URLSearchParams(params)
                  next.set('cursor', history.data.next_cursor!)
                  setParams(next)
                }}
              >
                Older answers
              </Button>
            )}
          </div>
        </>
      )}
    </div>
  )
}

function Answer({ id }: { id: string }) {
  const [params] = useSearchParams()
  const [source, setSource] = useState<{ id: string; citation: string } | null>(null)
  const heading = useRef<HTMLHeadingElement>(null)
  const trigger = useRef<HTMLButtonElement | null>(null)
  const answer = useQuery({
    queryKey: ['answer', id],
    queryFn: ({ signal }) =>
      apiFetch<Schemas['AnswerDetail']>(`/api/answers/${encodeURIComponent(id)}`, { signal }),
    retry: false,
  })
  useEffect(() => {
    heading.current?.focus()
  }, [])
  const data = answer.data
  const sources = Array.isArray(data?.metadata.sources)
    ? data.metadata.sources.filter(
        (s): s is { chunk_id: string; citation: string; cited?: boolean; flagged?: unknown } =>
          !!s && typeof s === 'object' && typeof s.chunk_id === 'string' && typeof s.citation === 'string',
      )
    : []
  const dropped = Array.isArray(data?.metadata.dropped)
    ? data.metadata.dropped.filter((value): value is string => typeof value === 'string')
    : []
  const withheld = withheldCount(dropped)
  const conversation = Array.isArray(data?.request.history)
    ? data.request.history
        .filter(
          (message): message is { role: string; text: string } =>
            !!message &&
            typeof message === 'object' &&
            typeof message.role === 'string' &&
            typeof message.text === 'string',
        )
        .slice(-6)
    : []
  return (
    <div className="grid gap-4 min-w-0 break-words">
      <Link to={`/answers?${params}`}>Back to saved answers</Link>
      <h1 ref={heading} tabIndex={-1} className="text-2xl font-semibold">
        Saved answer
      </h1>
      {answer.isPending ? (
        <p role="status">Loading answer…</p>
      ) : answer.isError ? (
        <div role="alert">
          {answer.error instanceof ApiError && answer.error.status === 404
            ? 'This saved answer is unavailable.'
            : 'Could not load this answer.'}
          <Button onClick={() => void answer.refetch()}>Retry answer</Button>
        </div>
      ) : (
        data && (
          <>
            <p className="text-sm text-muted">
              Saved {new Date(data.created_at).toLocaleString()}. This is a past response, not a newly checked
              answer.
            </p>
            {data.learner_question && (
              <Card>
                <h2 className="font-semibold">Your question</h2>
                <p className="whitespace-pre-wrap">{data.learner_question}</p>
              </Card>
            )}
            {data.target_label && <p className="text-sm">Target at the time: {data.target_label}</p>}
            <Card>
              <h2 className="font-semibold">Request at the time</h2>
              <p className="whitespace-pre-wrap">{data.request_text || 'Explanation requested'}</p>
            </Card>
            <Card>
              <Markdown text={data.text} />
              <ReadAloud text={data.text} />
            </Card>
            {typeof data.metadata.parent_answer_id === 'string' && (
              <p>
                This reply continues a{' '}
                <Link
                  className="underline"
                  to={`/answers/${encodeURIComponent(data.metadata.parent_answer_id)}`}
                >
                  previous saved answer
                </Link>
                .
              </p>
            )}
            {data.request.historical_answer && typeof data.request.historical_answer === 'object' && (
              <details>
                <summary>Historical context supplied for this reply</summary>
                <p className="text-sm text-muted">
                  Unverified saved context, not freshly retrieved source evidence.
                </p>
                <pre className="whitespace-pre-wrap break-words text-sm">
                  {JSON.stringify(data.request.historical_answer, null, 2)}
                </pre>
              </details>
            )}
            <AnswerFeedback key={`feedback:${data.id}`} answerId={data.id} />
            <AnswerFollowup key={data.id} answerId={data.id} />
            {sources.length > 0 ? (
              <details>
                <summary>Source references</summary>
                <p className="text-sm text-muted">
                  These references were saved with the answer. Opening a passage shows the current corpus
                  copy, which may have changed.
                </p>
                {sources.map((s) => (
                  <div key={s.chunk_id}>
                    <button
                      className="block underline text-left"
                      onClick={(event) => {
                        trigger.current = event.currentTarget
                        setSource({ id: s.chunk_id, citation: s.citation })
                      }}
                    >
                      {s.citation}
                    </button>
                    {s.cited === false && <span> — not cited in the answer</span>}
                    {Array.isArray(s.flagged) && s.flagged.some((flag) => typeof flag === 'string') && (
                      <span className="text-warn">
                        {' '}
                        (flagged: {s.flagged.filter((flag) => typeof flag === 'string').join(', ')})
                      </span>
                    )}
                  </div>
                ))}
                {source && (
                  <SourceViewer
                    key={source.id}
                    chunkId={source.id}
                    citation={source.citation}
                    turnId={data.turn_id}
                    onClose={() => {
                      setSource(null)
                      trigger.current?.focus()
                    }}
                  />
                )}
              </details>
            ) : (
              <p className="text-sm text-muted">No course source references were saved with this answer.</p>
            )}
            {withheld > 0 && (
              <p className="text-sm text-muted">
                {withheld} source{withheld === 1 ? '' : 's'} withheld: flagged text from a web or untrusted
                tier was not sent to the tutor.
              </p>
            )}
            {conversation.length > 0 && (
              <details>
                <summary>Conversation supplied at the time</summary>
                <p className="text-sm text-muted">
                  Earlier messages supplied with this request, not verified source evidence. At most the last
                  six messages are shown.
                </p>
                <ol className="grid gap-3 mt-3">
                  {conversation.map((message, index) => (
                    <li key={index}>
                      <h3 className="font-medium">
                        {message.role === 'assistant' ? 'Tutor' : message.role === 'user' ? 'You' : 'Message'}
                      </h3>
                      <p className="whitespace-pre-wrap">{message.text}</p>
                    </li>
                  ))}
                </ol>
              </details>
            )}
            <details>
              <summary>Material and code supplied at the time</summary>
              {['exercise', 'code', 'output'].map((key) =>
                typeof data.request[key] === 'string' && data.request[key] ? (
                  <div key={key} className="mt-3">
                    <h3 className="font-medium">
                      {key === 'exercise' ? 'Material / task' : key === 'code' ? 'Code' : 'Reported output'}
                    </h3>
                    <pre className="whitespace-pre-wrap break-words text-sm">{String(data.request[key])}</pre>
                  </div>
                ) : null,
              )}
              {data.request.output_stale === true && (
                <p>The output was already marked as belonging to earlier code.</p>
              )}
              {data.surface !== 'playground' && (
                <p>
                  The original retrieved passages are not copied into this history. Use the source references
                  above.
                </p>
              )}
            </details>
          </>
        )
      )}
    </div>
  )
}
