import { Disclosure } from '../components/ui/disclosure'
import { SourcedAnswer } from '../features/ask/SourcedAnswer'
import { SuggestionEvidence } from '../features/ask/SuggestionEvidence'
import { SourcePicker } from '../features/ask/SourcePicker'
import { sourceSelection, useSelectedPassages } from '../features/ask/useSelectedPassages'
import { FurtherReading } from '../features/ask/FurtherReading'
import { AnswerLessonDraft } from '../features/ask/AnswerLessonDraft'
import { AnswerVisual } from '../features/ask/AnswerVisual'
import { AnswerChecks } from '../features/ask/AnswerChecks'
import { useEffect, useRef, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router-dom'
import { Markdown } from '../components/Markdown'
import { Button } from '../components/ui/button'
import { Card } from '../components/ui/card'
import { useAreas } from '../features/areas/api'
import { askQuestion } from '../features/ask/api'
import { useAskRequestRecovery, type PendingTutorRequest } from '../features/playground/useRequestRecovery'
import { RequestRecoveryControls } from '../features/playground/RequestRecoveryControls'
import { useLessonDraft } from '../features/tutor/useLessonDraft'
import { ReadAloud } from '../features/voice/ReadAloud'
import { DictationButton } from '../features/voice/DictationButton'
import { api, type Schemas } from '../lib/api'
import { boundedRead } from '../lib/boundedRead'

export function Ask() {
  const [params] = useSearchParams()
  const learner = useQuery({ queryKey: ['learner'], queryFn: api.me })
  if (learner.isPending) return <p role="status">Opening your question workspace…</p>
  if (learner.isError)
    return (
      <p role="alert">
        Could not open your workspace. <Button onClick={() => void learner.refetch()}>Retry</Button>
      </p>
    )
  const parent = params.get('answer') ?? ''
  return <AskWorkspace key={`${learner.data.id}:${parent}`} learnerId={learner.data.id} parent={parent} />
}

function AskWorkspace({ learnerId, parent }: { learnerId: string; parent: string }) {
  const scope = `ask:${learnerId}:${parent || 'new'}`
  const draft = useLessonDraft(`${scope}:question`, 'question')
  const area = useLessonDraft(`${scope}:area`, 'area')
  const preview = useLessonDraft(`${scope}:preview`, 'unfinished reply')
  const previewQuestion = useLessonDraft(`${scope}:preview-question`, 'submitted question')
  const recovery = useAskRequestRecovery(scope)
  const selection = useSelectedPassages(scope)
  const preparing = useRef(false)
  const areas = useAreas()
  const nav = useNavigate()
  const cache = useQueryClient()
  const saved = useQuery({
    queryKey: ['ask-answer', parent],
    enabled: !!parent,
    queryFn: ({ signal }) =>
      boundedRead<Schemas['AnswerDetail']>(
        `/api/answers/${encodeURIComponent(parent)}`,
        signal,
        'Saved answer',
      ),
    retry: false,
  })
  const answer = saved.data?.surface === 'ask' ? saved.data : undefined
  const areaId = parent ? (typeof answer?.area_id === 'string' ? answer.area_id : '') : area.input
  const location = useLocation()
  const [preferSaved, setPreferSaved] = useState(false)
  const [search, setSearch] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [status, setStatus] = useState('')
  const controller = useRef<AbortController | null>(null)
  const generation = useRef(0)
  const textarea = useRef<HTMLTextAreaElement>(null)
  const heading = useRef<HTMLHeadingElement>(null)
  useEffect(() => {
    const timer = window.setTimeout(() => setSearch(draft.input.slice(0, 200)), 250)
    return () => window.clearTimeout(timer)
  }, [draft.input])
  useEffect(
    () => () => {
      generation.current++
      controller.current?.abort()
    },
    [],
  )
  useEffect(() => {
    if (parent && answer) heading.current?.focus()
  }, [parent, answer])
  const query = new URLSearchParams({ limit: '5' })
  if (search.trim()) query.set('q', search)
  if (areaId) query.set('area_id', areaId)
  const suggestions = useQuery({
    queryKey: ['ask-suggestions', learnerId, search, areaId],
    queryFn: ({ signal }) =>
      boundedRead<Schemas['AnswerPage']>(`/api/ask/suggestions?${query}`, signal, 'Saved questions'),
    enabled: !parent && !busy,
    retry: false,
  })
  const ready = !parent || !!answer

  async function submit(pending?: PendingTutorRequest<Schemas['AskQuestion']>) {
    if (controller.current || preparing.current || (!pending && (!ready || selection.invalid))) return
    preparing.current = true
    setBusy(true)
    const preparationToken = generation.current
    const abort = new AbortController()
    controller.current = abort
    let intent: PendingTutorRequest<Schemas['AskQuestion']>
    try {
      const sources = pending ? pending.body.sources : await sourceSelection(selection.selected)
      if (generation.current !== preparationToken || abort.signal.aborted) {
        if (generation.current === preparationToken) {
          controller.current = null
          setBusy(false)
          setStatus('Stopped before sending. Your question and selected passages are kept.')
        }
        return
      }
      intent =
        pending ??
        recovery.prepare(
          {
            question: draft.input,
            area_id: areaId || null,
            parent_answer_id: parent || null,
            ...(sources ? { sources } : {}),
            ...(!parent && preferSaved ? { prefer_saved: true } : {}),
          },
          { snapshot: draft.input, submitted: draft.input, display: draft.input, mode: 'explicit' },
        )
    } catch (e) {
      if (generation.current === preparationToken) {
        controller.current = null
        setError(e instanceof Error ? e.message : 'Could not prepare the question.')
        setBusy(false)
      }
      return
    } finally {
      preparing.current = false
    }
    const token = ++generation.current
    const entry = window.history.state?.key
    const url = window.location.href
    let moved = false
    const onBack = () => {
      moved = true
      abort.abort()
    }
    window.addEventListener('popstate', onBack)
    const current = () =>
      generation.current === token &&
      !moved &&
      window.history.state?.key === entry &&
      window.location.href === url
    setBusy(true)
    setError('')
    setStatus(intent.body.prefer_saved ? 'Checking for a saved answer; generating locally if none matches…' : intent.body.sources ? 'Explaining with your selected local passages…' : 'Generating locally…')
    // An explicit retry keeps the existing preview until new tokens actually arrive.
    let text = ''
    let started = false
    if (!pending) preview.setInput('')
    previewQuestion.setInput(intent.body.question)
    try {
      const reply = await askQuestion(intent.body, abort.signal, intent.key, (chunk) => {
        if (!current()) return
        started = true
        text += chunk
        preview.setInput(text)
      })
      if (!current()) return
      if (!reply.answer_id)
        throw new Error(
          'The answer has no confirmed saved record. Keep the preview and recover this request.',
        )
      recovery.accept(intent.key)
      if (draft.input === intent.body.question) draft.setInput('')
      preview.setInput('')
      previewQuestion.setInput('')
      selection.set([])
      await cache.invalidateQueries({ queryKey: ['ask-suggestions'] })
      if (!current()) return
      nav(`/ask?answer=${encodeURIComponent(reply.answer_id)}`, { state: { reusedAnswerId: reply.reused ? reply.answer_id : null } })
    } catch (e) {
      if (!current()) return
      setError(
        abort.signal.aborted
          ? 'Stopped. Any received text is kept below. Check the original request to recover a saved result.'
          : e instanceof Error
            ? e.message
            : 'The question could not be completed.',
      )
      setStatus(
        started ? 'Unfinished reply — not saved as a completed answer.' : 'No completed result confirmed.',
      )
    } finally {
      window.removeEventListener('popstate', onBack)
      if (generation.current === token) {
        controller.current = null
        setBusy(false)
      }
    }
  }

  return (
    <div className="space-y-5 min-w-0">
      <header className="space-y-2">
        <h1 className="text-page-title font-semibold">Ask the tutor</h1>
        <p>Explore a question from any area. This keeps your learning session unchanged.</p>
        <div className="flex flex-wrap gap-4">
          {parent && <Link to="/ask">New topic or question</Link>}
          <Link to="/answers?surface=ask">Saved Ask conversations</Link>
        </div>
      </header>
      {parent && (
        <section aria-label="Saved explanation" className="space-y-3">
          {saved.isPending && <p role="status">Opening saved explanation…</p>}
          {saved.isError && (
            <p role="alert">
              Could not load this answer.{' '}
              <Button onClick={() => void saved.refetch()}>Retry saved answer</Button>
            </p>
          )}
          {saved.isSuccess && !answer && (
            <p role="alert">
              This is not an Ask conversation.{' '}
              <Link to={`/answers/${encodeURIComponent(parent)}`}>Open the saved answer</Link>.
            </p>
          )}
          {answer && (
            <Card>
              {location.state?.reusedAnswerId === answer.id && (
                <p role="status" className="text-sm mb-3">Reopened your saved answer without a new model call. Original date below; not refreshed from the web.</p>
              )}
              <h2 tabIndex={-1} ref={heading} className="text-panel-heading font-semibold break-words">
                {answer.request_text}
              </h2>
              <p className="text-sm text-muted my-2">
                Saved locally · {new Date(answer.created_at).toLocaleString()} · Model explanation, not
                fact-checked.
              </p>
              <SourcedAnswer key={`sources:${answer.id}`} text={answer.text} sources={Array.isArray(answer.metadata.sources) ? answer.metadata.sources : []} />
              <ReadAloud text={`${answer.request_text}\n\n${answer.text}`} />
              <AnswerChecks key={answer.id} answerId={answer.id} learnerId={learnerId} />
              <AnswerLessonDraft key={`lesson:${answer.id}`} answerId={answer.id} learnerId={learnerId} answerText={answer.text} />
              <AnswerVisual key={`visual:${answer.id}`} answerId={answer.id} learnerId={learnerId} />
              <FurtherReading key={`reading:${answer.id}`} question={answer.request_text} />
              <div className="flex flex-wrap gap-4 mt-3">
                <Link to={`/answers/${encodeURIComponent(answer.id)}`}>Review or label this answer</Link>
                {typeof answer.metadata.parent_answer_id === 'string' && (
                  <Link to={`/ask?answer=${encodeURIComponent(answer.metadata.parent_answer_id)}`}>
                    Previous question and answer
                  </Link>
                )}
              </div>
            </Card>
          )}
        </section>
      )}
      <Card>
        <form
          className="space-y-3"
          onSubmit={(event) => {
            event.preventDefault()
            if (draft.input.trim()) void submit()
          }}
        >
          <label className="block font-medium" htmlFor="ask-area">
            Knowledge area (optional)
          </label>
          <select
            id="ask-area"
            className="w-full min-h-11 rounded border border-line bg-card px-3"
            value={areaId}
            disabled={busy || !!parent}
            onChange={(event) => area.setInput(event.target.value)}
          >
            <option value="">Any area</option>
            {areas.data?.areas.map((a) => (
              <option key={a.id} value={a.id}>
                {a.title}
              </option>
            ))}
            {areaId && !areas.data?.areas.some((a) => a.id === areaId) && (
              <option value={areaId}>Selected area unavailable</option>
            )}
          </select>
          {areas.isError && (
            <p role="status">
              Area list unavailable. You can still ask without an area.{' '}
              <Button type="button" onClick={() => void areas.refetch()}>
                Retry areas
              </Button>
            </p>
          )}
          <label className="block font-medium" htmlFor="ask-question">
            {parent ? 'Your follow-up question' : 'Your question'}
          </label>
          {answer && <Disclosure label="Choose a follow-up" className="mb-3">
            <p className="text-sm text-muted mb-2">These fill the question below. Edit it, then choose Ask follow-up.</p>
            {draft.input.trim() && <p className="text-sm text-muted mb-2">Your draft is kept. Clear it before choosing a suggested follow-up.</p>}
            <div className="flex flex-wrap gap-2">
              {[
                ['Simpler', 'Explain your previous answer more simply, using a concrete example and defining unfamiliar terms. Keep important limits and uncertainties.'],
                ['More detail', 'Explain your previous answer in more detail. Cover the important assumptions, limitations, and how I could apply it in a new situation.'],
                ['Show the method', 'Show a worked example for my previous question. Explain the method, why each step is needed, and how to check the result. State what cannot be checked from the available information.'],
              ].map(([label, question]) => <Button key={label} type="button"
                disabled={busy || !ready || !!recovery.pending || !!draft.input.trim()}
                onClick={() => { draft.setInput(question); textarea.current?.focus() }}>{label}</Button>)}
            </div>
          </Disclosure>}
          <textarea
            id="ask-question"
            ref={textarea}
            rows={4}
            maxLength={2000}
            required
            disabled={busy || !ready}
            className="w-full rounded border border-line bg-card p-3"
            value={draft.input}
            aria-describedby="ask-context"
            onChange={(event) => draft.setInput(event.target.value)}
          />
          <p id="ask-context" className="text-sm text-muted">
            {parent
              ? 'Uses up to three previous replies in this branch. Start a new topic to leave that context behind.'
              : 'No lesson, webpage or course material is attached automatically.'}{' '}
            Model explanations are not fact-checked. Source review is available after saving.
          </p>
          {selection.invalid && (
            <p role="alert">
              The saved source selection needs attention. Open Attach local sources to clear it before asking.
            </p>
          )}
          {!parent && (
            <label className="flex items-start gap-2 text-sm">
              <input type="checkbox" checked={preferSaved} disabled={busy || !!recovery.pending}
                onChange={event => setPreferSaved(event.target.checked)} />
              <span>Try a saved answer first
                <span className="block text-muted">Only an identical new question you marked Helpful with matching inputs and no known source or review issue. Otherwise, generate a fresh answer. This is not a correctness check.</span>
              </span>
            </label>
          )}
          <SourcePicker
            selection={selection}
            disabled={busy || !ready || !!recovery.pending || recovery.needsDiscard}
          />
          {!parent && !busy && (
            <section aria-label="Suggested saved questions" className="space-y-2">
              <p className="text-sm font-medium">
                {search.trim() ? 'Matching saved questions' : 'Suggested saved questions'}
              </p>
              {suggestions.isFetching && (
                <p role="status" className="text-sm">
                  Searching locally…
                </p>
              )}
              {suggestions.isError && (
                <p role="status">
                  Suggestions unavailable. You can still type a question.{' '}
                  <Button type="button" onClick={() => void suggestions.refetch()}>
                    Retry suggestions
                  </Button>
                </p>
              )}
              {!suggestions.isFetching && suggestions.data?.items.length === 0 && (
                <p className="text-sm text-muted">No saved questions match yet.</p>
              )}
              {!suggestions.isFetching &&
                search === draft.input.slice(0, 200) &&
                suggestions.data?.items.map((suggestion) => (
                  <div key={suggestion.id} className="flex flex-wrap items-center gap-2">
                    <Button
                      type="button"
                      className="whitespace-normal text-left h-auto"
                      onClick={() => {
                        draft.setInput(
                          (suggestion.learner_question || suggestion.request_text).slice(0, 2000),
                        )
                        textarea.current?.focus()
                      }}
                    >
                      {suggestion.learner_question || suggestion.request_text}
                    </Button>
                    <Link
                      className="text-sm"
                      to={
                        suggestion.surface === 'ask'
                          ? `/ask?answer=${encodeURIComponent(suggestion.id)}`
                          : `/answers/${encodeURIComponent(suggestion.id)}`
                      }
                    >
                      Read saved answer
                    </Link>
                    <SuggestionEvidence answer={suggestion} matching={!!search.trim()} />
                  </div>
                ))}
            </section>
          )}
          <div className="flex flex-wrap gap-2">
            <Button
              variant="primary"
              disabled={
                busy ||
                !ready ||
                selection.invalid ||
                !draft.input.trim() ||
                !!recovery.pending ||
                recovery.needsDiscard
              }
              type="submit"
            >
              {busy ? 'Generating…' : parent ? 'Ask follow-up' : 'Ask question'}
            </Button>
            {busy ? (
              <Button type="button" onClick={() => controller.current?.abort()}>
                Stop response
              </Button>
            ) : (
              <DictationButton
                disabled={!ready}
                onTranscript={(text) =>
                  draft.setInput((previous) => `${previous}${previous ? '\n' : ''}${text}`.slice(0, 2000))
                }
              />
            )}
          </div>
          <p className="text-sm text-muted">
            Draft kept in this browser tab. Completed replies are saved in the local database.
          </p>
        </form>
        {[draft.error, area.error, preview.error, previewQuestion.error]
          .filter(Boolean)
          .slice(0, 1)
          .map((e) => (
            <p key={e} role="alert">
              {e}
            </p>
          ))}
        {error && (
          <p role="alert" className="my-3">
            {error}
          </p>
        )}
        <RequestRecoveryControls
          recovery={recovery}
          busy={busy}
          originalContext="question and conversation branch"
          retry={() => {
            if (recovery.pending) void submit(recovery.pending)
          }}
        />
      </Card>
      {(preview.input || busy || status) && (
        <section aria-label="Response in progress" className="space-y-2">
          <p role="status">{status || 'Restored unfinished reply — not a confirmed completed answer.'}</p>
          <p className="font-medium break-words">{previewQuestion.input}</p>
          {preview.input && (
            <Card>
              <Markdown text={preview.input} />
            </Card>
          )}
        </section>
      )}
    </div>
  )
}
