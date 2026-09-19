import { useNavigate } from 'react-router-dom'
import { Button } from '../components/ui/button'
import { Card, CardTitle } from '../components/ui/card'
import { Choice } from '../components/ui/choice'
import { useStartSession } from '../features/session/api'
import { MODE_LABELS, useMode, type Mode } from '../stores/mode'

export function Home() {
  const { mode, energy, socratic, setMode, setEnergy, setSocratic, setSession, sessionId } = useMode()
  const start = useStartSession()
  const nav = useNavigate()

  async function begin() {
    const s = await start.mutateAsync({ mode, energy, socratic })
    setSession(s.id, s.next_skill?.id ?? null)
    nav(s.due_reviews > 0 && (mode === 'low_capacity' || energy <= 2) ? '/review' : '/session')
  }

  return (
    <div className="grid gap-4">
      <Card>
        <CardTitle>How are you arriving?</CardTitle>
        <Choice<Mode>
          label="State mode"
          options={(Object.keys(MODE_LABELS) as Mode[]).map((m) => ({
            value: m,
            label: MODE_LABELS[m].title,
            hint: MODE_LABELS[m].hint,
          }))}
          value={mode}
          onChange={setMode}
        />
        <div className="mt-4">
          <Choice<number>
            label="Energy (1 = running on empty, 5 = plenty)"
            options={[1, 2, 3, 4, 5].map((n) => ({
              value: n,
              label: String(n),
            }))}
            value={energy}
            onChange={setEnergy}
            columns={5}
          />
        </div>
        <div className="mt-4">
          <Choice<'explicit' | 'socratic'>
            label="Questioning style for this session"
            options={[
              {
                value: 'explicit',
                label: 'Explicit (default)',
                hint: 'Direct explanations in short steps.',
              },
              {
                value: 'socratic',
                label: 'Socratic',
                hint: 'One narrowing question per turn.',
              },
            ]}
            value={socratic ? 'socratic' : 'explicit'}
            onChange={(v) => setSocratic(v === 'socratic')}
            columns={2}
          />
        </div>
      </Card>
      <div className="flex gap-2 flex-wrap">
        <Button variant="primary" size="lg" onClick={() => void begin()} disabled={start.isPending}>
          {start.isPending ? 'Starting…' : 'Start session'}
        </Button>
        {sessionId && (
          <Button size="lg" onClick={() => nav('/session')}>
            Continue current session
          </Button>
        )}
      </div>
      {start.isError && (
        <p role="alert" className="text-warn">
          Could not start: {(start.error as Error).message}
        </p>
      )}
    </div>
  )
}
