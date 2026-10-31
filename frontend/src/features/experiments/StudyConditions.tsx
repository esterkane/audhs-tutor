import { useId, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiFetch, type Schemas } from '../../lib/api'
import { boundedRead } from '../../lib/boundedRead'
import { Disclosure } from '../../components/ui/disclosure'
import { Button } from '../../components/ui/button'

type Conditions = Schemas['StudyConditions']
const choices = {
  noise: ['off', 'white', 'pink', 'brown', 'other'],
  presence: ['alone', 'quiet_companion', 'human'],
  movement: ['none', 'brief_movement'],
  timer: ['hidden', 'elapsed', 'remaining'],
} as const
const labels = {
  noise: 'Sound condition',
  presence: 'Working alongside',
  movement: 'Movement before studying',
  timer: 'Timer display',
}
export function StudyConditions({ sessionId }: { sessionId?: string }) {
  const [open, setOpen] = useState(false)
  const formId = useId()
  const [conditions, setConditions] = useState<Conditions>({
    noise: 'off',
    presence: 'alone',
    movement: 'none',
    timer: 'elapsed',
  })
  const cache = useQueryClient()
  const result = useQuery({
    queryKey: ['study-conditions-summary'],
    enabled: open,
    retry: false,
    queryFn: ({ signal }) =>
      boundedRead<Schemas['ConditionsSummary']>('/api/study-conditions/summary', signal, 'Study conditions'),
  })
  const save = useMutation({
    mutationFn: () =>
      apiFetch<Schemas['ConditionsOut']>('/api/study-conditions', {
        method: 'POST',
        body: JSON.stringify({ session_id: sessionId, conditions }),
      }),
    retry: false,
    onSuccess: () => cache.invalidateQueries({ queryKey: ['study-conditions-summary'] }),
  })
  return (
    <Disclosure
      label="Study conditions and later recall (optional)"
      open={open}
      onToggle={(e) => setOpen(e.currentTarget.open)}
    >
      <p className="text-sm my-2">
        Record the conditions you actually used. This does not turn sound on, start a timer or change your
        preferences. Later recall matters more than feeling productive.
      </p>
      {sessionId && (
        <fieldset disabled={save.isPending} className="space-y-2 min-w-0">
          {(Object.keys(choices) as Array<keyof Conditions>).map((key) => (
            <div key={key}>
              <label className="block text-sm" htmlFor={`${formId}-${key}`}>
                {labels[key]}
              </label>
              <select
                id={`${formId}-${key}`}
                className="block max-w-full border border-line rounded p-2 bg-card"
                value={conditions[key]}
                onChange={(e) => {
                  setConditions({ ...conditions, [key]: e.target.value })
                  save.reset()
                }}
              >
                {choices[key].map((value) => (
                  <option value={value} key={value}>
                    {value.replaceAll('_', ' ')}
                  </option>
                ))}
              </select>
            </div>
          ))}
          <Button onClick={() => save.mutate()}>Record conditions for this lesson</Button>
          {save.isSuccess && (
            <p role="status">Conditions recorded as your self-report. No benefit has been inferred.</p>
          )}
          {save.isError && (
            <p role="alert">
              Could not record conditions. Your selections stay here. {(save.error as Error).message}
            </p>
          )}
        </fieldset>
      )}
      <h2 className="font-medium mt-3">Later review observations</h2>
      <p className="text-sm text-muted">
        Latest 90 days, up to 10,000 events. Missing conditions and same-day practice are excluded. These are
        observational associations, not proof that a condition helped; use controlled personal experiments
        before choosing a default.
      </p>
      {result.isError && (
        <p role="alert">
          Could not load observations.{' '}
          {result.data && 'Showing previously loaded observations; they may be out of date. '}
          <Button onClick={() => void result.refetch()}>Retry observations</Button>
        </p>
      )}
      {result.isPending && open && <p role="status">Loading observations…</p>}
      {result.data && (
        <>
          {(result.data.groups ?? []).length === 0 ? (
            <p className="text-sm">No qualifying later recall yet. Nothing is ranked or recommended.</p>
          ) : (
            <ul className="grid gap-2 text-sm">
              {result.data.groups.map((group, i) => (
                <li key={i} className="[overflow-wrap:anywhere]">
                  {Object.values(group.conditions).join(' · ')}: {group.recalled} of {group.items_reviewed}{' '}
                  distinct review items rated Good or Easy. This is not mastery or a treatment effect.
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </Disclosure>
  )
}
