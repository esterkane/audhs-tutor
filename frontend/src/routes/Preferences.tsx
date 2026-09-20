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

export function Preferences() {
  const prefs = usePreferences()
  const set = useSetPreference()
  if (prefs.isLoading || !prefs.data) return <Card>Loading preferences…</Card>
  const values = prefs.data.values as Record<string, unknown>
  const specs = prefs.data.specs as Spec[]
  return (
    <div className="grid gap-4">
      <Card>
        <CardTitle>Preferences</CardTitle>
        <p className="text-sm text-muted mb-3">
          Everything here is explicit and reversible. The system never changes these silently.
        </p>
        <div className="grid gap-4">
          {specs.map((s) => (
            <div key={s.key}>
              {s.type === 'bool' && (
                <Choice<string>
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
                  label={s.description}
                  options={(s.choices ?? []).map((c) => ({ value: c, label: c || '(none)' }))}
                  value={(values[s.key] as string) ?? ''}
                  onChange={(v) => set.mutate({ key: s.key, value: v })}
                  columns={Math.min(4, (s.choices ?? []).length)}
                />
              )}
              {s.type === 'int' && (
                <label className="text-sm font-medium">
                  {s.description}: {String(values[s.key])} min
                  <input
                    type="range"
                    min={s.min ?? 0}
                    max={s.max ?? 60}
                    value={Number(values[s.key])}
                    onChange={(e) => set.mutate({ key: s.key, value: Number(e.target.value) })}
                    className="block w-full"
                    aria-label={s.description}
                  />
                </label>
              )}
            </div>
          ))}
        </div>
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
