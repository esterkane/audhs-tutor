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

const preferenceSections = [
  { id: 'learning', title: 'Learning and explanations', prefixes: ['questions.', 'tutor.'], keys: ['session.socratic_default'] },
  { id: 'planning', title: 'Session planning', prefixes: ['planner.', 'session.'], keys: [] },
  { id: 'voice', title: 'Voice and recordings', prefixes: ['voice.'], keys: [] },
  { id: 'display', title: 'Display and comfort', prefixes: ['ui.'], keys: [] },
  { id: 'other', title: 'Additional preferences', prefixes: [], keys: [] },
]

function sectionFor(key: string) {
  return preferenceSections.find(section => section.keys.includes(key) || section.prefixes.some(prefix => key.startsWith(prefix)))?.id ?? 'other'
}

function optionLabel(key: string, value: string) {
  if (key === 'tutor.representation_default' && value === '') return 'No preferred format'
  const labels: Record<string, string> = {
    low_capacity: 'Low capacity',
    worked_example: 'Worked example',
    brown_noise: 'Brown noise',
  }
  return labels[value] ?? (value || '(none)')
}

const numericUnits: Record<string, string> = {
  'planner.new_material_min': 'min',
  'planner.review_min': 'min',
  'voice.retention_days': 'days',
}

function effectHint(key: string): string | undefined {
  if (key.startsWith('questions.')) return 'Guides newly drafted learning-area questions. Does not rewrite saved questions or change every live tutor reply.'
  if (key.startsWith('planner.')) return 'Used when planning a new session. Saving this does not change the plan of a session already started.'
  if (['ui.theme', 'ui.density', 'ui.font_scale', 'ui.reduced_motion'].includes(key)) return 'Updates the display after saving. Your learning progress is unchanged.'
  if (key === 'tutor.representation_default') return 'A preference for new session-tutor explanations when this format is available. Explicit format choices take precedence; existing explanations stay unchanged.'
  if (key === 'session.default_mode') return 'Preselection on Home for a new session; it does not change an active session.'
  if (key === 'session.socratic_default') return 'This saved default is not applied automatically yet. Choose the questioning style in Home → Session options for each session.'
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
          {preferenceSections.map(section => {
            const sectionSpecs = specs.filter(s => ['bool', 'enum', 'int'].includes(s.type) && sectionFor(s.key) === section.id)
            if (!sectionSpecs.length) return null
            return (
              <section key={section.id} aria-labelledby={`preferences-${section.id}`} className="grid grid-cols-1 gap-4">
                <CardTitle as="h2" id={`preferences-${section.id}`} className="mb-0">{section.title}</CardTitle>
                {sectionSpecs.map((s) => (
            <div key={s.key}>
              {s.type === 'bool' && (
                <Choice<string>
                  stackOnNarrow
                  describedBy={effectHint(s.key) ? `effect-${s.key}` : undefined}
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
                  describedBy={effectHint(s.key) ? `effect-${s.key}` : undefined}
                  label={s.description}
                  options={(s.choices ?? []).map((c) => ({ value: c, label: optionLabel(s.key, c) }))}
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
                    aria-describedby={effectHint(s.key) ? `effect-${s.key}` : undefined}
                    aria-valuetext={numericValue(s.key, values[s.key])}
                  />
                </label>
              )}
              {effectHint(s.key) && <p id={`effect-${s.key}`} className="text-sm text-muted mt-2">{effectHint(s.key)}</p>}
            </div>
                ))}
              </section>
            )
          })}
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
