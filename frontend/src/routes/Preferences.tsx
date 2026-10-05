import { Link } from 'react-router-dom'
import { Button } from '../components/ui/button'
import { Card, CardTitle } from '../components/ui/card'
import { Choice } from '../components/ui/choice'
import { AdaptationLog } from '../features/adaptations/AdaptationCards'
import { usePreferences, useSetPreference } from '../features/preferences/api'

type Spec = {
  key: string
  type: string
  default: unknown
  choices?: string[] | null
  min?: number | null
  max?: number | null
  description: string
}

const numericUnits: Record<string, string> = {
  'planner.new_material_min': 'min',
  'planner.review_min': 'min',
  'voice.retention_days': 'days',
}

function numericValue(key: string, value: unknown) {
  return [String(value), numericUnits[key]].filter(Boolean).join(' ')
}

export function Preferences() {
  const prefs = usePreferences()
  const set = useSetPreference()
  const readRecovery = prefs.isError && (
    <div className="mb-3">
      <p role="alert">
        {prefs.data
          ? 'Could not refresh preferences. Showing the last loaded settings.'
          : 'Could not load preferences.'}
      </p>
      <p className="text-sm text-muted">Check that the local app backend is running, then retry.</p>
      <Button className="mt-2" onClick={() => void prefs.refetch()} disabled={prefs.isFetching}>
        Retry loading preferences
      </Button>
      {prefs.isFetching && <p role="status">Retrying preferences…</p>}
      <details className="mt-2">
        <summary>Technical details</summary>
        <p className="text-sm break-words">{prefs.error.message}</p>
      </details>
    </div>
  )
  if (!prefs.data) return (
    <Card>
      <CardTitle as="h1">Preferences</CardTitle>
      {readRecovery || <p role="status">Loading preferences…</p>}
      <Link to="/" className="underline">Return Home</Link>
    </Card>
  )
  const values = prefs.data.values as Record<string, unknown>
  const specs = prefs.data.specs as Spec[]
  return (
    <div className="grid grid-cols-1 gap-4">
      <Card>
        <CardTitle as="h1">Preferences</CardTitle>
        {readRecovery}
        <p className="text-sm text-muted mb-3">
          Everything here is explicit and reversible. The system never changes these silently.
        </p>
        <div className="grid grid-cols-1 gap-4">
          {specs.map((s) => (
            <div key={s.key}>
              {s.type === 'bool' && (
                <Choice<string>
                  stackOnNarrow
                  label={s.description}
                  options={[
                    { value: 'on', label: 'On' },
                    { value: 'off', label: 'Off' },
                  ]}
                  value={values[s.key] ? 'on' : 'off'}
                  onChange={(v) => {
                    const on = v === 'on'
                    if (on && s.key === 'ui.notifications' && typeof Notification !== 'undefined')
                      void Notification.requestPermission()
                    set.mutate({ key: s.key, value: on })
                  }}
                  columns={2}
                />
              )}
              {s.type === 'enum' && (
                <Choice<string>
                  stackOnNarrow
                  label={s.description}
                  options={(s.choices ?? []).map((c) => ({ value: c, label: c || '(none)' }))}
                  value={(values[s.key] as string) ?? ''}
                  onChange={(v) => set.mutate({ key: s.key, value: v })}
                  columns={Math.min(4, (s.choices ?? []).length)}
                />
              )}
              {s.type === 'int' && (
                <label className="text-sm font-medium">
                  {s.description}: {numericValue(s.key, values[s.key])}
                  <input
                    type="range"
                    min={s.min ?? 0}
                    max={s.max ?? 60}
                    value={Number(values[s.key])}
                    onChange={(e) => set.mutate({ key: s.key, value: Number(e.target.value) })}
                    className="block w-full"
                    aria-label={s.description}
                    aria-valuetext={numericValue(s.key, values[s.key])}
                  />
                </label>
              )}
            </div>
          ))}
        </div>
        {set.isPending && <p role="status" className="text-sm text-muted mt-2">Saving preferences…</p>}
        {set.isError && (
          <p role="alert" className="text-warn mt-2">
            {(set.error as Error).message}
          </p>
        )}
        <Button className="mt-4" onClick={() => history.back()}>
          Back
        </Button>
      </Card>
      <AdaptationLog />
    </div>
  )
}
