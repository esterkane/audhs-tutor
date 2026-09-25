import { useRef, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { Button } from '../../components/ui/button'
import { Card, CardTitle } from '../../components/ui/card'
import { useSkills } from '../skills/api'
import { api, apiFetch } from '../../lib/api'
import { useMode } from '../../stores/mode'
import { routeForPhase, useCurrentSession } from './api'

/** Explicit route intent, separate from the running session's authoritative topic. */
export function SelectedLesson({ skillId }: { skillId: string }) {
  const current = useCurrentSession()
  const skills = useSkills()
  const nav = useNavigate()
  const qc = useQueryClient()
  const lock = useRef(false)
  const [endedPrevious, setEndedPrevious] = useState(false)
  const { mode, energy, socratic, setSession } = useMode()
  const lesson = skills.data?.skills.find((s) => s.id === skillId)
  const start = useMutation({
    mutationFn: async () => {
      await apiFetch(`/api/sessions/selection/${encodeURIComponent(skillId)}`)
      if (current.data) {
        await api.endSession(current.data.id, {})
        setEndedPrevious(true)
        qc.setQueryData(['session-current'], null)
        setSession(null)
        void qc.invalidateQueries({ queryKey: ['session', current.data.id] })
      }
      return api.startSession({ mode, energy, socratic, skill_id: skillId })
    },
    onSuccess: (s) => {
      qc.setQueryData(['session-current'], s)
      qc.setQueryData(['session', s.id], s)
      setSession(s.id, s.state.skill_id)
      nav(routeForPhase(s.state), { replace: true })
    },
  })
  async function begin() {
    if (lock.current) return
    lock.current = true
    try {
      await start.mutateAsync()
    } catch {
      /* retain intent and show error */
    } finally {
      lock.current = false
    }
  }
  if (current.isError || skills.isError)
    return (
      <Card>
        <p role="alert">Could not check the lesson and current session.</p>
        <Button
          onClick={() => {
            void current.refetch()
            void skills.refetch()
          }}
        >
          Retry
        </Button>
        <Button onClick={() => nav('/')}>Home</Button>
      </Card>
    )
  if (current.isPending || skills.isPending) return <Card>Checking selected lesson…</Card>
  return (
    <Card>
      <CardTitle>{lesson ? `Learn: ${lesson.title}` : 'Lesson unavailable'}</CardTitle>
      <p>{lesson?.description}</p>
      {current.data && (
        <p>
          Your current session{current.data.active_skill ? `: ${current.data.active_skill.title}` : ''} stays
          unchanged until you choose to end it. Completed work is retained.
        </p>
      )}
      {!lesson?.unlocked && (
        <p>This lesson is unavailable or needs prerequisites. Choose an available lesson from the map.</p>
      )}
      <div className="flex flex-wrap gap-2 mt-3">
        {current.data && (
          <Button
            disabled={start.isPending}
            onClick={() => {
              const s = current.data!
              setSession(s.id, s.state.skill_id)
              nav(routeForPhase(s.state), { replace: true })
            }}
          >
            Keep current session
          </Button>
        )}
        <Button
          variant="primary"
          disabled={!lesson?.unlocked || start.isPending || current.isFetching}
          onClick={() => void begin()}
        >
          {start.isPending ? 'Starting…' : current.data ? 'End and start this lesson' : 'Start this lesson'}
        </Button>
        <Button disabled={start.isPending} onClick={() => nav('/map')}>
          Back to map
        </Button>
      </div>
      {start.isError && (
        <p role="alert">
          {endedPrevious ? 'Previous session ended; the new lesson has not started. ' : ''}Could not start
          this lesson: {start.error.message}. Your selection is retained; you can retry.
        </p>
      )}
    </Card>
  )
}
