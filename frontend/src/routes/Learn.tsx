import { useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, useNavigate } from 'react-router-dom'
import { Button } from '../components/ui/button'
import { Card } from '../components/ui/card'
import { routeForPhase } from '../features/session/api'
import type { SessionOut } from '../lib/api'
import { boundedRead } from '../lib/boundedRead'
import { useMode } from '../stores/mode'

/** Navigation only: the server owns session identity and phase. */
export function Learn() {
  const navigate = useNavigate()
  const setSession = useMode(state => state.setSession)
  const current = useQuery({
    queryKey: ['session-current'],
    queryFn: ({ signal }) => boundedRead<SessionOut | null>('/api/sessions/current', signal, 'Saved session'),
    refetchOnMount: 'always',
    retry: false,
  })
  useEffect(() => {
    // Cached data cannot route before this entry's refresh succeeds.
    if (current.isFetching || !current.isSuccess) return
    if (!current.data) {
      navigate('/', { replace: true })
      return
    }
    setSession(current.data.id, current.data.state?.skill_id ?? current.data.next_skill?.id ?? null)
    navigate(routeForPhase(current.data.state), { replace: true })
  }, [current.data, current.isFetching, current.isSuccess, navigate, setSession])

  return <Card>
    <h1 className="text-page-title font-semibold">Learn</h1>
    {current.isError && !current.isFetching ? <>
      <p role="alert" className="mt-3">Could not check your saved session. No new session has been started.</p>
    </> : <p role="status" className="mt-3">Checking your saved session…</p>}
    <Button className="mt-3" aria-disabled={current.isFetching} aria-busy={current.isFetching}
      onClick={() => { if (!current.isFetching) void current.refetch() }}>Retry</Button>
    <Link to="/" className="mt-4 block underline">Return Home</Link>
  </Card>
}
