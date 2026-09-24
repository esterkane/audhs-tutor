import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { Card, CardTitle } from '../components/ui/card'
import { Button } from '../components/ui/button'
import { useAreas, useAreaActions, useAreaJob, type Area } from '../features/areas/api'
import { FeedbackPreferences } from '../features/areas/QuestionFeedback'
import { useDrafts } from '../features/curriculum/api'
import { DraftEditor } from './Curriculum'

export function Areas() {
  const query = useAreas(),
    actions = useAreaActions(),
    job = useAreaJob(),
    drafts = useDrafts()
  const qc = useQueryClient()
  const wasRunning = useRef(false)
  useEffect(() => {
    if (wasRunning.current && !job.data?.running) {
      void qc.invalidateQueries({ queryKey: ['curriculum'] })
      void qc.invalidateQueries({ queryKey: ['areas'] })
    }
    wasRunning.current = Boolean(job.data?.running)
  }, [job.data?.running, qc])
  const [selected, setSelected] = useState(''),
    [draftId, setDraftId] = useState(''),
    [dirty, setDirty] = useState(false)
  const area = query.data?.areas.find((a) => a.id === selected)
  const areaDrafts =
    drafts.data?.drafts.filter((d) => d.area_id === selected && d.status !== 'rejected') ?? []
  const draft = areaDrafts.find((d) => d.id === draftId)
  const coverage = draft?.payload.area_coverage as Record<string, unknown> | undefined
  const error =
    query.error ||
    actions.initialize.error ||
    actions.start.error ||
    actions.stop.error ||
    job.error ||
    drafts.error
  return (
    <div className="grid gap-4">
      <Card>
        <CardTitle>Learning areas</CardTitle>
        <p className="text-sm mt-2">
          Build knowledge across courses. Choose an area, review its source-backed draft, then activate
          lessons when they are ready.
        </p>
        <p className="text-sm text-muted mt-2">
          Courses remain source references. Suggested matches and shared sources are not verified
          prerequisites or proof that two concepts are equivalent.
        </p>
        {query.isLoading && <p role="status">Loading areas…</p>}
        {query.data?.areas.length === 0 && (
          <Button disabled={actions.initialize.isPending} onClick={() => actions.initialize.mutate()}>
            Suggest areas from my material
          </Button>
        )}
        {!!query.data?.areas.length && (
          <>
            <label className="block font-medium mt-3" htmlFor="knowledge-area">
              Area to review
            </label>
            <select
              id="knowledge-area"
              value={selected}
              disabled={dirty}
              className="w-full border border-line rounded p-2"
              onChange={(e) => {
                setSelected(e.target.value)
                setDraftId('')
              }}
            >
              <option value="">Choose a knowledge area…</option>
              {query.data.areas.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.title} · {a.courses.length} courses · {a.documents} source candidates
                </option>
              ))}
            </select>
            <p className="text-sm text-muted mt-2">
              {query.data.total_documents} imported documents · {query.data.unassigned_documents} without an
              area match. Matching terms are editable; a document can belong to several areas.
            </p>
            {!job.data?.running && (
              <Button
                className="mt-3"
                disabled={actions.start.isPending || dirty}
                onClick={() => actions.start.mutate()}
              >
                Create all missing area drafts locally
              </Button>
            )}
          </>
        )}
        {job.data?.running && (
          <div role="status" className="mt-3 text-sm">
            Drafting {job.data.current ?? 'starting'} · {job.data.finished}/{job.data.total}
            <Button disabled={actions.stop.isPending} onClick={() => actions.stop.mutate()}>
              Stop drafting
            </Button>
          </div>
        )}
        {job.data?.error && <p role="alert">{job.data.error}</p>}
        {!job.data?.running && !!job.data?.results.length && (
          <details className="mt-3">
            <summary>Draft batch results</summary>
            <ul>
              {job.data.results.map((r) => (
                <li key={r.area}>
                  {r.area}: {r.result.replaceAll('_', ' ')}
                </li>
              ))}
            </ul>
          </details>
        )}
        {error && (
          <p role="alert" className="mt-2">
            {error.message}
          </p>
        )}
        <FeedbackPreferences />
        <p className="text-sm mt-4">
          <Link to="/curriculum">Advanced: existing course drafts and source roles</Link>
        </p>
      </Card>
      {area && (
        <Card>
          <CardTitle>{area.title}</CardTitle>
          <AreaSettings key={area.id} area={area} disabled={dirty || Boolean(job.data?.running)} />
          <p className="text-sm mt-3">
            {areaDrafts.length
              ? 'Review a draft below. Nothing becomes active until you choose Activate lessons.'
              : 'No draft yet. Use “Create all missing area drafts locally” above.'}
          </p>
          <Button
            className="mt-3"
            disabled={dirty || actions.start.isPending || Boolean(job.data?.running)}
            onClick={() => actions.start.mutate({ area_id: area.id, force_new: true })}
          >
            Create a new draft from current sources
          </Button>
          <p className="text-sm text-muted">
            Keeps earlier drafts and active lessons. Uses your accepted question preferences.
          </p>
          <ul className="grid gap-2 mt-3">
            {areaDrafts.map((d) => (
              <li key={d.id}>
                <Button disabled={dirty} onClick={() => setDraftId(d.id)}>
                  {d.title} —{' '}
                  {d.status === 'published'
                    ? 'active'
                    : String(d.payload.area_state ?? 'draft').replaceAll('_', ' ')}
                </Button>
              </li>
            ))}
          </ul>
          <details className="text-sm mt-3">
            <summary>Courses contributing source candidates</summary>
            <ul>
              {area.courses.map((c) => (
                <li key={c}>{c}</li>
              ))}
            </ul>
          </details>
          <details className="text-sm mt-3">
            <summary>Connections through shared source documents</summary>
            <p>{area.related.join(' · ') || 'No shared sources yet.'}</p>
          </details>
        </Card>
      )}
      {draft && (
        <>
          <Card>
            <CardTitle>Draft coverage</CardTitle>
            <p className="text-sm">
              Selected{' '}
              {String(
                (draft.payload.area_coverage as Record<string, unknown> | undefined)?.selected_passages ?? 0,
              )}{' '}
              passages from the first topic-matching prose passage in each selected document. This sample does
              not cover every course or lesson.
            </p>
            <p className="text-sm mt-2">
              {String(coverage?.eligible_documents ?? 0)} eligible documents ·{' '}
              {String(coverage?.eligible_passages ?? 0)} candidate passages before topic filtering.
            </p>
            <details className="text-sm mt-2">
              <summary>Sources actually sampled for this draft</summary>
              <ul>
                {Array.isArray(coverage?.selected_courses) &&
                  coverage.selected_courses.map((c) => <li key={String(c)}>{String(c)}</li>)}
              </ul>
            </details>
            {typeof draft.payload.area_error === 'string' && <p role="alert">{draft.payload.area_error}</p>}
          </Card>
          <DraftEditor key={draft.id} draft={draft} onDirtyChange={setDirty} />
        </>
      )}
    </div>
  )
}
function AreaSettings({ area, disabled }: { area: Area; disabled: boolean }) {
  const { edit } = useAreaActions()
  const [title, setTitle] = useState(area.title),
    [terms, setTerms] = useState(area.terms.join(', '))
  return (
    <details className="mt-3 text-sm">
      <summary>Edit area name and matching terms</summary>
      <label className="block mt-2">
        Area name
        <input
          className="block border border-line rounded p-2 w-full"
          maxLength={120}
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />
      </label>
      <label className="block mt-2">
        Matching terms, separated by commas
        <input
          className="block border border-line rounded p-2 w-full"
          value={terms}
          onChange={(e) => setTerms(e.target.value)}
        />
      </label>
      <p className="text-muted mt-2">
        Matches source titles and sections; course-name matches are shown as context only. Editing terms does
        not rewrite existing drafts.
      </p>
      <Button
        disabled={disabled || edit.isPending || !title.trim() || !terms.trim()}
        onClick={() =>
          edit.mutate({
            id: area.id,
            title,
            terms: terms
              .split(',')
              .map((s) => s.trim())
              .filter(Boolean),
            description: area.description,
          })
        }
      >
        Save area
      </Button>
      {edit.error && <p role="alert">{edit.error.message}</p>}
      {edit.isSuccess && <p role="status">Area saved.</p>}
    </details>
  )
}
