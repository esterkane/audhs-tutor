import { useStopSession } from './useStopSession'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Button } from '../../components/ui/button'
import { apiFetch, type Schemas } from '../../lib/api'
import { usePreferences } from '../preferences/api'

/** Ending a session is always available and never submits an assessment or a rating. */
export function SessionControls({ sessionId, skillId }: { sessionId: string; skillId?: string | null }) {
  const qc = useQueryClient()
  const prefs = usePreferences()
  const marks = (prefs.data?.values?.['learning.material_marks'] ?? {}) as Record<string, string>
  const stop = useStopSession(sessionId)
  const mark = useMutation({
    mutationFn: (status: 'clear' | 'later' | null) =>
      apiFetch<Schemas['MaterialMarkOut']>(`/api/skills/${skillId}/mark`, {
        method: 'PUT',
        body: JSON.stringify({ status }),
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['preferences'] })
    },
  })
  return (
    <section aria-label="Session controls" className="border border-line rounded-md p-3">
      <div className="flex gap-2 flex-wrap">
        <Button onClick={() => stop.mutate()} disabled={stop.isPending}>
          Stop session
        </Button>
        <Button onClick={() => stop.mutate()} disabled={stop.isPending}>
          Change topic
        </Button>
        {skillId && (
          <>
            <Button
              pressed={marks[skillId] === 'clear'}
              onClick={() => mark.mutate('clear')}
              disabled={mark.isPending}
            >
              This is clear
            </Button>
            <Button
              pressed={marks[skillId] === 'later'}
              onClick={() => mark.mutate('later')}
              disabled={mark.isPending}
            >
              Ask me again later
            </Button>
            {marks[skillId] && (
              <Button variant="ghost" onClick={() => mark.mutate(null)} disabled={mark.isPending}>
                Undo label
              </Button>
            )}
          </>
        )}
      </div>
      <p className="text-xs text-muted mt-2">
        Stop saves completed work and returns Home; change topic opens the topic chooser there. No rating
        needed.
      </p>
      {skillId && marks[skillId] && (
        <p role="status" className="text-sm mt-2">
          {marks[skillId] === 'clear'
            ? 'Saved as clear for you.'
            : 'Saved in your Ask me later list on Home.'}{' '}
          This label does not change assessed mastery.
        </p>
      )}
      {(stop.error || mark.error) && <p role="alert">{(stop.error || mark.error)?.message}</p>}
    </section>
  )
}
