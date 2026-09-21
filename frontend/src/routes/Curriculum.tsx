import { useState } from 'react'
import { Button } from '../components/ui/button'
import { Card, CardTitle } from '../components/ui/card'
import { Textarea } from '../components/ui/textarea'
import {
  useDraftActions,
  useDrafts,
  useMaterial,
  useSections,
  type DraftOut,
} from '../features/curriculum/api'

type Payload = DraftOut['payload'] & {
  skills?: Array<Record<string, unknown>>
  learning_objects?: Array<Record<string, unknown>>
  assessments?: Array<Record<string, unknown>>
}

/**
 * Course → curriculum (P4). Material is *searchable* after ingest and *learnable* only after a
 * reviewed draft is published. One task at a time: pick a course section → propose a draft →
 * review/edit → publish or reject. The draft is JSON the learner can edit directly; validation
 * problems are listed literally and errors block publishing.
 */
export function Curriculum() {
  const material = useMaterial()
  const drafts = useDrafts()
  const actions = useDraftActions()
  const [course, setCourse] = useState<string | null>(null)
  const sections = useSections(course)
  const [selected, setSelected] = useState<string | null>(null)
  const [useModel, setUseModel] = useState(false)
  const draft = (drafts.data?.drafts ?? []).find((d) => d.id === selected) ?? null

  return (
    <div className="grid gap-4">
      <Card>
        <CardTitle>Material → lessons</CardTitle>
        <p className="text-sm text-muted mb-2">
          Ingested material is searchable by the tutor. It becomes a lesson only after you review and publish
          a curriculum draft: skills with prerequisites, a learning object with linked source passages, and at
          least one assessment per skill. Every field of a draft is a proposal for you to edit; nothing is
          published until you say so.
        </p>
        {material.data && material.data.courses.length === 0 && (
          <p className="text-sm" role="status">
            Nothing ingested yet — add material under Corpus first.
          </p>
        )}
        <ul className="text-sm grid gap-1" aria-label="Courses">
          {(material.data?.courses ?? []).map((m) => (
            <li key={m.course} className="flex flex-wrap gap-2 items-center">
              <Button
                size="sm"
                variant={course === m.course ? 'primary' : 'secondary'}
                onClick={() => {
                  setCourse(m.course)
                  setSelected(null)
                }}
              >
                {m.course}
              </Button>
              <span className="text-muted">
                {m.status} · {m.documents} documents · {m.chunks} passages · {m.published_skills} published
                skills
                {m.drafts ? ` · ${m.drafts} open draft${m.drafts === 1 ? '' : 's'}` : ''}
              </span>
            </li>
          ))}
        </ul>
      </Card>
      {course && (
        <Card>
          <details open={!selected}>
            <summary className="cursor-pointer font-medium">Sections of {course}</summary>
            <label className="text-sm flex items-center gap-2 mb-2">
              <input type="checkbox" checked={useModel} onChange={(e) => setUseModel(e.target.checked)} />
              Ask the local model for goals, exercises and one question per lecture (a proposal, reviewed like
              everything else; without a ready model the deterministic draft is used)
            </label>
            <ul className="text-sm grid gap-1" aria-label="Sections">
              {(sections.data?.sections ?? []).map((s) => (
                <li key={String(s.section)} className="flex flex-wrap gap-2 items-center">
                  <span>
                    {s.section ?? '(no section)'} · {s.documents} documents
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
                    Propose a draft
                  </Button>
                </li>
              ))}
            </ul>
            {actions.create.isError && (
              <p role="alert" className="text-sm text-warn mt-2">
                {(actions.create.error as Error).message}
              </p>
            )}
          </details>
        </Card>
      )}
      <Card>
        <details open={!selected}>
          <summary className="cursor-pointer font-medium">Drafts</summary>
          {(drafts.data?.drafts ?? []).length === 0 ? (
            <p className="text-sm text-muted">No drafts yet. Pick a course section above.</p>
          ) : (
            <ul className="text-sm grid gap-1" aria-label="Drafts">
              {(drafts.data?.drafts ?? []).map((d) => (
                <li key={d.id} className="flex flex-wrap gap-2 items-center">
                  <Button
                    size="sm"
                    variant={selected === d.id ? 'primary' : 'secondary'}
                    onClick={() => setSelected(d.id)}
                  >
                    {d.title}
                  </Button>
                  <span className="text-muted">
                    {d.status} · v{d.version} · {d.origin} ·{' '}
                    {d.problems.filter((p) => p.level === 'error').length} errors,{' '}
                    {d.problems.filter((p) => p.level === 'warning').length} warnings
                  </span>
                </li>
              ))}
            </ul>
          )}
        </details>
      </Card>
      {draft && <DraftEditor draft={draft} />}
    </div>
  )
}

function DraftEditor({ draft }: { draft: DraftOut }) {
  const actions = useDraftActions()
  const payload = draft.payload as Payload
  const [text, setText] = useState(() => JSON.stringify(payload, null, 2))
  const [parseError, setParseError] = useState<string | null>(null)
  const errors = draft.problems.filter((p) => p.level === 'error')
  const warnings = draft.problems.filter((p) => p.level === 'warning')
  const editable = draft.status === 'draft'
  const skills = payload.skills ?? []
  const objects = payload.learning_objects ?? []
  const assessments = payload.assessments ?? []
  const modelTouched = new Set(
    [...skills, ...objects].filter((x) => x.origin === 'model').map((x) => String(x.slug ?? x.skill)),
  ).size

  function save() {
    try {
      const next = JSON.parse(text) as DraftOut['payload']
      setParseError(null)
      actions.update.mutate({ id: draft.id, payload: next })
    } catch (e) {
      setParseError((e as Error).message)
    }
  }

  return (
    <Card key={draft.id + draft.version}>
      <CardTitle>
        {draft.title} · {draft.status}
      </CardTitle>
      <p className="text-sm text-muted">
        {skills.length} skills · {objects.length} learning objects · {assessments.length} assessments
        {assessments.some((a) => a.auto) ? ' · cloze items marked auto were cut from the source text' : ''}
        {assessments.some((a) => a.guessable)
          ? ' · items marked guessable blank a title word — edit or replace them before publishing'
          : ''}
        {draft.origin === 'model'
          ? ` · goals/criteria/exercises on ${modelTouched} of ${skills.length} lessons were proposed by the local model — check them against the source`
          : ''}
      </p>
      <ol className="text-sm mt-2 grid gap-1" aria-label="Skills in this draft">
        {skills.map((sk) => {
          const slug = String(sk.slug)
          const obj = objects.find((o) => o.skill === slug)
          const n = assessments.filter((a) => a.skill === slug).length
          const problems = draft.problems.filter((p) => p.where === slug)
          return (
            <li key={slug}>
              <span className="font-medium">{String(sk.title)}</span>
              <span className="text-muted">
                {' '}
                · needs {((sk.prerequisites as string[] | undefined) ?? []).length || 'no'} prerequisite
                {((sk.prerequisites as string[] | undefined) ?? []).length === 1 ? '' : 's'} ·{' '}
                {((obj?.sources as string[] | undefined) ?? []).length} source passages · {n} assessment
                {n === 1 ? '' : 's'}
                {problems.length ? ` · ${problems.length} problem${problems.length === 1 ? '' : 's'}` : ''}
              </span>
            </li>
          )
        })}
      </ol>
      {(errors.length > 0 || warnings.length > 0) && (
        <ul className="text-sm mt-2 grid gap-1" aria-label="Validation">
          {errors.map((p, i) => (
            <li key={`e${i}`} className="text-warn">
              error · {p.where}: {p.message}
            </li>
          ))}
          {warnings.map((p, i) => (
            <li key={`w${i}`} className="text-muted">
              warning · {p.where}: {p.message}
            </li>
          ))}
        </ul>
      )}
      <details className="mt-3" open={editable}>
        <summary className="cursor-pointer text-sm font-medium">
          {editable ? 'Edit the draft (JSON)' : 'Draft content (read-only)'}
        </summary>
        <label htmlFor="draft-json" className="sr-only">
          Draft JSON
        </label>
        <Textarea
          id="draft-json"
          value={text}
          onChange={(e) => setText(e.target.value)}
          readOnly={!editable}
          className="mt-2 min-h-64 font-mono text-xs"
        />
        {parseError && (
          <p role="alert" className="text-sm text-warn mt-1">
            Not valid JSON: {parseError}
          </p>
        )}
        {editable && (
          <Button size="sm" className="mt-2" onClick={save} disabled={actions.update.isPending}>
            Save and re-validate
          </Button>
        )}
      </details>
      {editable && (
        <div className="flex gap-2 flex-wrap mt-3 items-center">
          <Button
            variant="primary"
            disabled={errors.length > 0 || actions.publish.isPending}
            onClick={() => actions.publish.mutate(draft.id)}
          >
            {errors.length > 0
              ? `Publish (fix ${errors.length} error${errors.length === 1 ? '' : 's'} first)`
              : 'Publish these lessons'}
          </Button>
          <Button
            variant="ghost"
            disabled={actions.reject.isPending}
            onClick={() => actions.reject.mutate(draft.id)}
          >
            Reject draft
          </Button>
        </div>
      )}
      {actions.publish.isSuccess && (
        <p className="text-sm mt-2" role="status">
          Published: {actions.publish.data.skills} skills, {actions.publish.data.edges} prerequisite links,{' '}
          {actions.publish.data.new_object_versions} new learning-object versions,{' '}
          {actions.publish.data.assessments} new assessments. The skills are on the map and can be chosen as a
          goal on Home.
        </p>
      )}
      {(actions.publish.isError || actions.update.isError || actions.reject.isError) && (
        <p role="alert" className="text-sm text-warn mt-2">
          {((actions.publish.error ?? actions.update.error ?? actions.reject.error) as Error).message}
        </p>
      )}
    </Card>
  )
}
