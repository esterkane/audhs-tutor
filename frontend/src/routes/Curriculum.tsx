import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { Button } from '../components/ui/button'
import { Card, CardTitle } from '../components/ui/card'
import { Textarea } from '../components/ui/textarea'
import { SourceViewer } from '../features/curriculum/SourceViewer'
import {
  useDraftActions,
  useDrafts,
  useMaterial,
  useSections,
  useSourceRole,
  useSources,
  type DraftOut,
} from '../features/curriculum/api'

type Payload = DraftOut['payload'] & {
  skills?: Array<Record<string, unknown>>
  learning_objects?: Array<Record<string, unknown>>
  assessments?: Array<Record<string, unknown>>
}
const statusLabel = (status: string) =>
  status === 'published' ? 'Active' : status === 'rejected' ? 'Discarded' : 'Draft — not active'
const strings = (value: unknown): string[] =>
  Array.isArray(value) ? value.filter((v): v is string => typeof v === 'string') : []

export function Curriculum() {
  const material = useMaterial()
  const drafts = useDrafts()
  const actions = useDraftActions()
  const [course, setCourse] = useState<string | null>(null)
  const [selected, setSelected] = useState<string | null>(null)
  const [dirty, setDirty] = useState(false)
  const [useModel, setUseModel] = useState(false)
  const sections = useSections(course)
  const courseDrafts = (drafts.data?.drafts ?? []).filter((d) => d.course === course)
  const draft = courseDrafts.find((d) => d.id === selected) ?? null
  const current = material.data?.courses.find((m) => m.course === course)
  const openDrafts = courseDrafts.filter((d) => d.status === 'draft')
  const history = courseDrafts.filter((d) => d.status !== 'draft')

  function draftButton(d: DraftOut) {
    return (
      <li key={d.id} className="flex flex-wrap justify-between items-center gap-2 border-b border-line py-3">
        <div>
          <p className="font-medium">{d.section ?? 'Course introduction'}</p>
          <p className="text-sm text-muted">
            {statusLabel(d.status)} · {((d.payload as Payload).skills ?? []).length} lessons
          </p>
        </div>
        <Button
          disabled={dirty}
          onClick={() => setSelected(d.id)}
          aria-label={`Review ${d.section ?? 'Course introduction'}`}
        >
          {d.status === 'draft' ? 'Review lessons' : 'View lessons'}
        </Button>
      </li>
    )
  }

  return (
    <div className="grid gap-4">
      <Card>
        <CardTitle>Turn course material into lessons</CardTitle>
        <p className="text-sm text-muted mt-2">
          Your imported files are already searchable. Here you review lesson drafts and activate the sections
          you want to study.
        </p>
        <p className="text-sm mt-2">
          Activation adds lessons to your tutor app. It does not post or share your course material online.
        </p>
        <ol className="flex flex-wrap gap-4 text-sm mt-4" aria-label="Lesson setup steps">
          <li aria-current={!course ? 'step' : undefined}>1. Choose a course</li>
          <li aria-current={course && !draft ? 'step' : undefined}>2. Choose a section</li>
          <li aria-current={draft ? 'step' : undefined}>3. Review and activate</li>
        </ol>
      </Card>
      <Card>
        <label htmlFor="lesson-course" className="block font-medium mb-2">
          Course
        </label>
        <select
          id="lesson-course"
          className="w-full rounded-md border border-line bg-card p-2 text-sm"
          value={course ?? ''}
          disabled={dirty || material.isLoading}
          onChange={(e) => {
            setCourse(e.target.value || null)
            setSelected(null)
          }}
        >
          <option value="">Choose an imported course…</option>
          {(material.data?.courses ?? []).map((m) => (
            <option key={m.course} value={m.course}>
              {m.course}
            </option>
          ))}
        </select>
        {material.isLoading && (
          <p role="status" className="text-sm mt-2">
            Loading courses…
          </p>
        )}
        {material.isError && (
          <p role="alert" className="text-sm text-warn mt-2">
            Courses could not load.{' '}
            <Button size="sm" onClick={() => void material.refetch()}>
              Retry courses
            </Button>
          </p>
        )}
        {material.data?.courses.length === 0 && (
          <p className="text-sm mt-2">
            No course material yet.{' '}
            <Link to="/corpus" className="underline">
              Import files in Corpus
            </Link>{' '}
            first.
          </p>
        )}
        {current && (
          <p className="text-sm text-muted mt-2">
            {current.documents} imported files · {current.published_skills} active lessons · {current.drafts}{' '}
            drafts to review
          </p>
        )}
        {dirty && (
          <p role="status" className="text-sm mt-2">
            Save or discard your edits before changing course or section.
          </p>
        )}
      </Card>
      {course && !draft && (
        <>
          <Card>
            <CardTitle>Choose a section to review</CardTitle>
            <p className="text-sm text-muted mt-2">
              Open an existing draft to see its lessons. Reviewing a draft does not activate it.
            </p>
            {drafts.isLoading && <p role="status">Loading drafts…</p>}
            {drafts.isError && (
              <p role="alert">
                Drafts could not load.{' '}
                <Button size="sm" onClick={() => void drafts.refetch()}>
                  Retry drafts
                </Button>
              </p>
            )}
            {drafts.isSuccess &&
              (openDrafts.length ? (
                <ul aria-label="Draft sections">{openDrafts.map(draftButton)}</ul>
              ) : (
                <p className="text-sm mt-3">No drafts waiting for review. You can create one below.</p>
              ))}
            {history.length > 0 && (
              <details className="mt-4">
                <summary className="cursor-pointer text-sm font-medium">
                  Active lessons and discarded drafts ({history.length})
                </summary>
                <ul aria-label="Previous sections">{history.map(draftButton)}</ul>
              </details>
            )}
          </Card>
          <Card>
            <details>
              <summary className="cursor-pointer font-medium">Create a new section draft</summary>
              <p className="text-sm text-muted my-2">
                Use this for a section that has no draft yet, or to prepare a new version. Existing active
                lessons stay available until you activate a replacement.
              </p>
              <label className="text-sm flex items-start gap-2 my-3">
                <input type="checkbox" checked={useModel} onChange={(e) => setUseModel(e.target.checked)} />
                Use the local model to suggest goals and exercises. Otherwise, build a basic draft from the
                sources.
              </label>
              <p className="text-xs text-muted">
                If the local model is unavailable, a basic draft is used. Every draft still needs review.
              </p>
              {sections.isLoading && <p role="status">Loading sections…</p>}
              {sections.isError && (
                <p role="alert">
                  Sections could not load.{' '}
                  <Button size="sm" onClick={() => void sections.refetch()}>
                    Retry sections
                  </Button>
                </p>
              )}
              {sections.data?.sections.length === 0 && (
                <p className="text-sm mt-2">No sections available from these files.</p>
              )}
              <ul aria-label="Sections" className="text-sm grid gap-3 mt-3">
                {(sections.data?.sections ?? []).map((s) => (
                  <li key={String(s.section)} className="flex flex-wrap gap-2 justify-between items-center">
                    <span>
                      {s.section ?? 'Course introduction'} · {s.documents} files
                      {openDrafts.some((d) => d.section === s.section) ? ' · draft already exists' : ''}
                    </span>
                    <Button
                      size="sm"
                      disabled={actions.create.isPending}
                      onClick={() =>
                        void actions.create
                          .mutateAsync({ course, section: s.section ?? null, use_model: useModel })
                          .then((d) => setSelected(d.id))
                          .catch(() => undefined)
                      }
                    >
                      Create draft
                    </Button>
                  </li>
                ))}
              </ul>
              {actions.create.isPending && (
                <p role="status" className="text-sm mt-2">
                  Preparing the draft…
                </p>
              )}
              {actions.create.isError && (
                <p role="alert" className="text-sm text-warn mt-2">
                  {actions.create.error.message}
                </p>
              )}
            </details>
          </Card>
          <SourcesPanel key={course} course={course} />
        </>
      )}
      {draft && (
        <>
          <div>
            <Button disabled={dirty} onClick={() => setSelected(null)}>
              Back to sections
            </Button>
          </div>
          <DraftEditor key={draft.id} draft={draft} onDirtyChange={setDirty} />
        </>
      )}
    </div>
  )
}

const ROLE_LABELS: Record<string, string> = {
  primary: 'primary — lessons are built from it',
  supplemental: 'supplemental — not used for lessons; still searchable by the tutor',
  excluded: 'excluded — not used for lessons; still searchable by the tutor',
}

/** What each document is for this course. Suggestions are literal rules; only your choice sticks. */
function SourcesPanel({ course }: { course: string }) {
  const sources = useSources(course)
  const roles = useSourceRole()
  if (sources.isError)
    return (
      <Card>
        <p role="alert" className="text-sm text-warn">
          The sources of {course} could not be loaded: {(sources.error as Error).message}
        </p>
      </Card>
    )
  if (!sources.data) return null
  const counts = sources.data.counts
  return (
    <Card>
      <details>
        <summary className="cursor-pointer font-medium">
          Advanced: choose source files ({counts.primary} primary, {counts.supplemental + counts.excluded}{' '}
          reference only)
        </summary>
        <p className="text-sm text-muted my-2">
          Choose which files new lesson drafts use. Primary files supply lesson content; supplemental and
          excluded files stay searchable but are not used to build lessons. Changes apply to future drafts,
          not drafts you already reviewed.
        </p>
        <ul className="text-sm grid gap-1" aria-label="Sources">
          {sources.data.sources.map((s) => (
            <li key={s.document_id} className="flex flex-wrap gap-2 items-center">
              <span className="min-w-48">
                <span className="text-muted">{s.section ?? '(no section)'} · </span>
                {s.title}
                <span className="text-muted">
                  {' '}
                  · {s.source_type} · {s.chunks} passages
                  {s.chunks === 0 ? ' · no unique passages' : ''}
                </span>
              </span>
              <label className="flex items-center gap-1">
                <select
                  className="border border-line rounded-md px-1 py-0.5"
                  value={s.role}
                  aria-label={`Role of ${s.title}`}
                  onChange={(e) =>
                    roles.set.mutate({ course, documentId: s.document_id, role: e.target.value })
                  }
                >
                  {Object.entries(ROLE_LABELS).map(([v, l]) => (
                    <option key={v} value={v}>
                      {l}
                    </option>
                  ))}
                </select>
              </label>
              <span className="text-muted text-xs">
                {s.decided_by === 'owner'
                  ? `your choice${s.reason ? `: ${s.reason}` : ' (no reason recorded)'}`
                  : `suggested: ${s.reason}`}
              </span>
              {s.decided_by === 'owner' && (
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => roles.reset.mutate({ course, documentId: s.document_id })}
                >
                  use suggestion
                </Button>
              )}
            </li>
          ))}
        </ul>
        {(roles.set.isError || roles.reset.isError) && (
          <p role="alert" className="text-sm text-warn mt-2">
            The role was not saved; try again.
          </p>
        )}
      </details>
    </Card>
  )
}

function DraftEditor({
  draft: incoming,
  onDirtyChange,
}: {
  draft: DraftOut
  onDirtyChange: (dirty: boolean) => void
}) {
  const actions = useDraftActions()
  const draft = [actions.publish.data?.draft, actions.reject.data, actions.update.data, incoming]
    .filter((d): d is DraftOut => Boolean(d))
    .reduce((latest, d) =>
      d.version > latest.version ||
      (d.version === latest.version && latest.status === 'draft' && d.status !== 'draft')
        ? d
        : latest,
    )

  const payload = draft.payload as Payload
  const [text, setText] = useState(() => JSON.stringify(payload, null, 2))
  const [savedText, setSavedText] = useState(text)
  const [parseError, setParseError] = useState<string | null>(null)
  const [source, setSource] = useState<{ id: string; label: string; skill: string } | null>(null)
  const heading = useRef<HTMLHeadingElement>(null)
  useEffect(() => {
    heading.current?.focus()
  }, [])
  const canonicalText = JSON.stringify(payload, null, 2)
  const dirty = text !== savedText
  const conflict = dirty && canonicalText !== savedText
  // A refreshed server version may arrive while this section stays open.
  // Synchronize pristine editors; preserve dirty text until explicitly discarded.
  if (!dirty && canonicalText !== savedText) {
    setText(canonicalText)
    setSavedText(canonicalText)
    setSource(null)
  }
  const busy = actions.update.isPending || actions.publish.isPending || actions.reject.isPending
  const editable = draft.status === 'draft'
  const skills = payload.skills ?? []
  const objects = payload.learning_objects ?? []
  const assessments = payload.assessments ?? []
  const errors = draft.problems.filter((p) => p.level === 'error')
  const warnings = draft.problems.filter((p) => p.level === 'warning')
  const notes = draft.problems.filter((p) => p.level === 'info')

  function save() {
    if (conflict) return
    try {
      const next = JSON.parse(text) as DraftOut['payload']
      setParseError(null)
      actions.update.mutate(
        { id: draft.id, payload: next },
        {
          onSuccess: (updated) => {
            const canonical = JSON.stringify(updated.payload, null, 2)
            setText(canonical)
            setSavedText(canonical)
            setSource(null)
            onDirtyChange(false)
          },
        },
      )
    } catch (e) {
      setParseError((e as Error).message)
    }
  }
  function discard() {
    setText(canonicalText)
    setSavedText(canonicalText)
    setSource(null)
    setParseError(null)
    onDirtyChange(false)
  }

  return (
    <Card>
      <p className="text-xs text-muted mb-1">{statusLabel(draft.status)}</p>
      <h2 ref={heading} tabIndex={-1} className="text-lg font-semibold mb-2">
        {draft.section ?? 'Course introduction'}
      </h2>
      <p className="text-sm text-muted mt-2">
        {skills.length} lessons · {assessments.length} knowledge checks
      </p>
      <p className="text-sm mt-2">
        Check the goals and practice below. Open a lesson to review its questions and source passages.
      </p>
      <ol aria-label="Lessons in this draft" className="grid gap-3 mt-4">
        {skills.map((sk, index) => {
          const slug = String(sk.slug)
          const obj = objects.find((o) => o.skill === slug)
          const checks = assessments.filter((a) => a.skill === slug)
          const prerequisites = strings(sk.prerequisites).map((id) =>
            String(skills.find((s) => s.slug === id)?.title ?? id),
          )
          return (
            <li key={slug} className="rounded-md border border-line p-3">
              <p className="font-medium">
                {index + 1}. {String(sk.title)}
              </p>
              <p className="text-sm mt-1">
                <span className="font-medium">You’ll learn: </span>
                {String(obj?.goal || 'A learning goal still needs to be added.')}
              </p>
              <details className="mt-2">
                <summary className="cursor-pointer text-sm">Review practice, questions and sources</summary>
                {prerequisites.length > 0 && (
                  <p className="text-sm mt-2">Builds on: {prerequisites.join(', ')}</p>
                )}
                {strings(obj?.examples).length > 0 && (
                  <div className="text-sm mt-3">
                    <p className="font-medium">Worked examples</p>
                    <ul className="list-disc pl-5">
                      {strings(obj?.examples).map((v, i) => (
                        <li key={i}>{v}</li>
                      ))}
                    </ul>
                  </div>
                )}
                <div className="text-sm mt-3">
                  <p className="font-medium">Practice</p>
                  {strings(obj?.exercises).length ? (
                    <ul className="list-disc pl-5">
                      {strings(obj?.exercises).map((v, i) => (
                        <li key={i}>{v}</li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-muted">No practice tasks yet.</p>
                  )}
                </div>
                <div className="text-sm mt-3">
                  <p className="font-medium">What you should be able to explain or do</p>
                  <ul className="list-disc pl-5">
                    {strings(obj?.success_criteria ?? sk.success_criteria).map((v, i) => (
                      <li key={i}>{v}</li>
                    ))}
                  </ul>
                </div>
                <div className="text-sm mt-3">
                  <p className="font-medium">Knowledge checks</p>
                  {checks.length === 0 && <p>No questions yet.</p>}
                  {checks.map((a, i) => {
                    const item = a.item as Record<string, unknown> | undefined
                    return (
                      <div key={i} className="mt-2 border-l-2 border-line pl-3">
                        <p>{String(item?.question ?? item?.prompt ?? item?.text ?? 'Question missing')}</p>
                        {strings(item?.options).length > 0 && (
                          <ul className="list-disc pl-5">
                            {strings(item?.options).map((v, j) => (
                              <li key={j}>{v}</li>
                            ))}
                          </ul>
                        )}
                        {typeof a.source_chunk_id === 'string' ? (
                          <Button
                            size="sm"
                            className="mt-2"
                            onClick={() =>
                              setSource({
                                id: String(a.source_chunk_id),
                                skill: slug,
                                label: `${String(sk.title)} — question ${i + 1} source`,
                              })
                            }
                          >
                            Read question source
                          </Button>
                        ) : (
                          <p className="text-muted mt-1">No source attached to this question.</p>
                        )}
                        <details className="mt-1">
                          <summary className="cursor-pointer text-muted">
                            Review answer and grading criteria
                          </summary>
                          {typeof item?.answer === 'number' && (
                            <p>
                              Expected answer: {strings(item.options)[item.answer] ?? 'Invalid answer index'}
                            </p>
                          )}
                          {strings(item?.answers).length > 0 && (
                            <p>Accepted answers: {strings(item?.answers).join('; ')}</p>
                          )}
                          {typeof item?.explanation === 'string' && <p>{item.explanation}</p>}
                          {a.rubric && !Array.isArray(a.rubric) ? (
                            <p>
                              Additional grading data is available under Advanced: view or edit draft data.
                            </p>
                          ) : null}
                          {Array.isArray(a.rubric) && (
                            <ul className="list-disc pl-5">
                              {a.rubric.map((r, j) => (
                                <li key={j}>
                                  {typeof r === 'object' && r ? String(r.criterion ?? '') : String(r)}
                                </li>
                              ))}
                            </ul>
                          )}
                        </details>
                      </div>
                    )
                  })}
                </div>
                <div className="text-sm mt-3">
                  <p className="font-medium">Source passages</p>
                  {strings(obj?.sources).length === 0 && (
                    <p className="text-muted">No source passages attached to this lesson.</p>
                  )}
                  <div className="flex flex-wrap gap-2 mt-1">
                    {strings(obj?.sources).map((id, i) => (
                      <Button
                        key={id}
                        size="sm"
                        onClick={() =>
                          setSource({ id, skill: slug, label: `${String(sk.title)} — passage ${i + 1}` })
                        }
                      >
                        Read passage {i + 1}
                      </Button>
                    ))}
                  </div>
                </div>
              </details>
              {source?.skill === slug && (
                <div className="mt-3">
                  <SourceViewer
                    key={source.id}
                    chunkId={source.id}
                    citation={source.label}
                    onClose={() => setSource(null)}
                  />
                </div>
              )}
            </li>
          )
        })}
      </ol>
      {errors.length > 0 && (
        <div className="mt-4 text-sm">
          <p className="font-medium text-warn">Fix these before activation</p>
          <ul aria-label="Validation errors" className="list-disc pl-5">
            {errors.map((p, i) => (
              <li key={i}>
                {p.where}: {p.message}
              </li>
            ))}
          </ul>
        </div>
      )}
      {warnings.length > 0 && (
        <details className="mt-3">
          <summary className="cursor-pointer text-sm font-medium">
            Review {warnings.length} warnings before activation
          </summary>
          <ul className="text-sm list-disc pl-5">
            {warnings.map((p, i) => (
              <li key={i}>
                {p.where}: {p.message}
              </li>
            ))}
          </ul>
        </details>
      )}
      {notes.length > 0 && (
        <details className="mt-3">
          <summary className="cursor-pointer text-sm">How this draft was prepared</summary>
          <ul className="text-sm text-muted list-disc pl-5">
            {notes.map((p, i) => (
              <li key={i}>{p.message}</li>
            ))}
          </ul>
        </details>
      )}
      <details className="mt-4">
        <summary className="cursor-pointer text-sm font-medium">
          Advanced: {editable ? 'edit draft data' : 'view draft data'}
        </summary>
        <p className="text-sm text-muted mt-2">
          For detailed changes to goals, questions or prerequisites. Save to validate your edits before
          activation. The preview above shows the saved version.
        </p>
        <label htmlFor="draft-json" className="sr-only">
          Draft JSON
        </label>
        <Textarea
          id="draft-json"
          className="mt-2 min-h-64 font-mono text-xs"
          value={text}
          readOnly={!editable || busy}
          onChange={(e) => {
            setText(e.target.value)
            onDirtyChange(e.target.value !== savedText)
          }}
        />
        {parseError && (
          <p role="alert" className="text-sm text-warn">
            Not valid JSON: {parseError}
          </p>
        )}
        {conflict && (
          <p role="alert" className="text-sm text-warn mt-2">
            This draft changed elsewhere. Copy any edits you want to keep, then discard unsaved edits to load
            the latest version.
          </p>
        )}
        {(editable || dirty) && (
          <div className="flex flex-wrap gap-2 mt-2">
            <Button size="sm" onClick={save} disabled={busy || !dirty || conflict || !editable}>
              Save changes
            </Button>
            <Button size="sm" variant="ghost" onClick={discard} disabled={!dirty || busy}>
              Discard unsaved edits
            </Button>
          </div>
        )}
      </details>
      {editable && (
        <div className="border-t border-line mt-5 pt-4">
          <p className="font-medium">Ready to study this section?</p>
          <p className="text-sm text-muted mt-1">
            Activate these {skills.length} lessons to make them available on Home and the skill map. You can
            leave this page and keep the draft for later.
          </p>
          {dirty && (
            <p role="status" className="text-sm mt-2">
              Unsaved changes — save or discard them before activation.
            </p>
          )}
          <Button
            className="mt-3"
            variant="primary"
            disabled={errors.length > 0 || dirty || busy}
            onClick={() => actions.publish.mutate(draft.id)}
          >
            {actions.publish.isPending ? 'Activating…' : 'Activate lessons'}
          </Button>
          {errors.length > 0 && (
            <p className="text-sm text-warn mt-1">
              Activation is blocked until {errors.length} validation issue
              {errors.length === 1 ? ' is' : 's are'} fixed.
            </p>
          )}
          <details className="mt-3">
            <summary className="cursor-pointer text-sm text-muted">Discard this draft instead</summary>
            <p className="text-sm my-2">
              Keeps your imported files and any already active lessons. This draft becomes read-only.
            </p>
            <Button size="sm" disabled={busy || dirty} onClick={() => actions.reject.mutate(draft.id)}>
              Discard draft
            </Button>
          </details>
        </div>
      )}
      {draft.status === 'published' && (
        <div role="status" className="mt-4">
          <p className="font-medium">These lessons are active.</p>
          <p className="text-sm mt-1">
            Choose them as a learning goal on Home, or explore them on the skill map.
          </p>
          <Link to="/" className="inline-block underline mt-2">
            Go to Home
          </Link>
        </div>
      )}
      {draft.status === 'rejected' && (
        <p role="status" className="text-sm mt-4">
          Draft discarded. Your source files and active lessons are unchanged.
        </p>
      )}
      {(actions.publish.isError || actions.update.isError || actions.reject.isError) && (
        <p role="alert" className="text-sm text-warn mt-2">
          {(actions.publish.error ?? actions.update.error ?? actions.reject.error)?.message}
        </p>
      )}
    </Card>
  )
}
