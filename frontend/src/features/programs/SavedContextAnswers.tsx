import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { apiFetch, type Schemas } from '../../lib/api'
import { Button } from '../../components/ui/button'

export function SavedContextAnswers({
  courseId,
  sectionId,
  targetId,
  areaId,
}: {
  courseId?: string
  sectionId?: string
  targetId?: string
  areaId?: string
}) {
  const [open, setOpen] = useState(false)
  const scope = targetId ? 'target' : areaId ? 'learning area' : 'course'
  const params = new URLSearchParams()
  if (targetId) params.set('target_id', targetId)
  if (areaId) params.set('area_id', areaId)
  else params.set('surface', 'playground')
  if (courseId) params.set('course_id', courseId)
  if (sectionId) params.set('section_id', sectionId)
  const query = useQuery({
    queryKey: ['answers', 'context', params.toString()],
    queryFn: ({ signal }) => apiFetch<Schemas['AnswerPage']>(`/api/answers?${params}&limit=5&suggestions=true`, { signal }),
    enabled: open && Boolean(targetId || courseId || areaId),
  })
  if (!targetId && !courseId && !areaId) return null
  return (
    <details onToggle={(event) => setOpen(event.currentTarget.open)} className="mt-3 text-sm">
      <summary>{targetId ? 'Previously answered here' : `Saved answers for this ${scope}`}</summary>
      <p className="text-muted my-2">
        Past replies for this {scope}, newest first. Your code or material may have changed; these are not
        newly checked answers.
      </p>
      {open &&
        (query.isPending ? (
          <p role="status">Loading previous answers…</p>
        ) : query.isError ? (
          <p role="alert">
            Could not load previous answers.{' '}
            <Button onClick={() => void query.refetch()}>Retry previous answers</Button>
          </p>
        ) : (
          <>
            {query.data.items.length === 0 ? (
              <p>
                No saved replies for this {scope} yet. Earlier answers without this recorded context remain in
                the general history.
              </p>
            ) : (
              <ul className="grid gap-3">
                {query.data.items.map((answer) => (
                  <li key={answer.id} className="break-words">
                    <Link className="underline" to={`/answers/${encodeURIComponent(answer.id)}?${params}`}>
                      {(
                        answer.learner_question ||
                        answer.target_label ||
                        answer.request_text ||
                        'Explanation requested'
                      ).slice(0, 180)}
                    </Link>
                    <p className="text-muted">{new Date(answer.created_at).toLocaleString()}</p>
                    <p>{answer.preview}</p>
                  </li>
                ))}
              </ul>
            )}
            <Link className="underline block mt-2" to={`/answers?${params}`}>
              Browse all answers for this {scope}
            </Link>
          </>
        ))}
    </details>
  )
}
