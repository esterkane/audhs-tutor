import { Link } from 'react-router-dom'
import { Button } from '../../components/ui/button'
import { useDrafts } from '../curriculum/api'

/** Mounted only for an empty selected topic: preview preparation, never activate it. */
export function HomeTopicPreparation({ areaId, secondary }: { areaId: string; secondary: boolean }) {
  const drafts = useDrafts()
  const prepared = drafts.data?.drafts?.find(
    (draft) =>
      draft.area_id === areaId && draft.status === 'draft' && draft.payload.area_state === 'generated',
  )
  const lessons = Array.isArray(prepared?.payload.skills)
    ? prepared.payload.skills.filter(
        (item): item is Record<string, unknown> => Boolean(item) && typeof item === 'object',
      )
    : []
  const objects = Array.isArray(prepared?.payload.learning_objects) ? prepared.payload.learning_objects : []
  const href = `/areas?area=${encodeURIComponent(areaId)}`
  return (
    <div className="min-w-0">
      {drafts.isPending && <p role="status">Checking prepared lessons for this topic…</p>}
      {drafts.isError && (
        <p role="alert">
          Could not check prepared lessons.{' '}
          <Button onClick={() => void drafts.refetch()}>Retry prepared lessons</Button>
        </p>
      )}
      {prepared && (
        <>
          <p className="font-medium">Lessons prepared for your review</p>
          <ul className="list-disc pl-5 my-2">
            {lessons.map((lesson, index) => {
              const object = objects.find(
                (item) => item && typeof item === 'object' && item.skill === lesson.slug,
              )
              const goal = object && typeof object.goal === 'string' ? object.goal : null
              return (
                <li key={index}>
                  {typeof lesson.title === 'string' ? lesson.title : `Lesson ${index + 1}`}
                  {goal && <p className="text-sm text-muted">{goal}</p>}
                </li>
              )
            })}
          </ul>
          <p className="text-sm mb-2">
            Review the lessons and sources, choose Activate lessons, then Go to Home and Start session.
            Nothing is activated by opening the draft.
          </p>
        </>
      )}
      <Button asChild variant={secondary ? 'secondary' : 'primary'} size="lg">
        <Link to={prepared ? `${href}&draft=${encodeURIComponent(prepared.id)}` : href}>
          {prepared ? 'Review lessons to start' : 'Review and activate a lesson'}
        </Link>
      </Button>
    </div>
  )
}
