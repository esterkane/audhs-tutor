import { useState } from 'react'
import { Button } from '../components/ui/button'
import { Card, CardTitle } from '../components/ui/card'
import { useExperimentActions, useExperiments, useResults, type MetricOut } from '../features/experiments/api'

const METRIC_LABELS: Record<string, string> = {
  delayed_recall: 'Delayed recall (share of reviews rated Good or Easy)',
  error_rate: 'Error rate (share of wrong attempts)',
  latency_ms: 'Answer latency (ms)',
  completion: 'Block completion (share not left early)',
  voluntary_continuation: 'Voluntary continuation (sessions that ran past the plan)',
  transfer: 'Transfer (mean score on transfer items)',
}

function fmt(v: number | null | undefined, metric: string): string {
  if (v == null) return '—'
  return metric === 'latency_ms' ? `${Math.round(v)} ms` : v.toFixed(2)
}

function MetricRow({ m, primary }: { m: MetricOut; primary: boolean }) {
  return (
    <li className={primary ? 'border border-accent rounded-md p-2' : 'border border-line rounded-md p-2'}>
      <p className="font-medium">
        {METRIC_LABELS[m.metric] ?? m.metric}
        {primary ? ' · primary' : ''}
        {m.lower_is_better ? ' · lower is better' : ''}
      </p>
      <p className="text-sm">
        {m.arms.map((a) => `${a.name}: ${fmt(a.mean, m.metric)} (n=${a.n})`).join(' · ')}
        {m.difference != null
          ? ` · difference ${m.difference > 0 ? '+' : ''}${fmt(m.difference, m.metric)}`
          : ''}
        {m.ci95 ? ` · 95% CI ${fmt(m.ci95[0], m.metric)} to ${fmt(m.ci95[1], m.metric)}` : ''}
      </p>
      <p className="text-sm text-muted">{m.reading}</p>
    </li>
  )
}

function Dashboard({ id }: { id: string }) {
  const results = useResults(id)
  if (!results.data) return <p className="text-sm">Loading results…</p>
  const r = results.data
  return (
    <div className="grid gap-3">
      <p className="text-sm text-muted">
        Hypothesis: {r.experiment.hypothesis || '—'} · unit: {r.experiment.unit_type} · arms:{' '}
        {r.experiment.arms.map((a) => `${a.name} (${a.assigned} ${r.experiment.unit_type}s)`).join(', ')}
      </p>
      <ul className="grid gap-2" aria-label="Metrics">
        {r.metrics.map((m) => (
          <MetricRow key={m.metric} m={m} primary={m.metric === r.primary_metric} />
        ))}
      </ul>
      <details>
        <summary className="cursor-pointer text-sm font-medium">Assignments ({r.units.length})</summary>
        <ul className="text-sm mt-1">
          {r.units.map((u) => (
            <li key={String(u.id)}>
              {String(u.label)} → {String(u.arm)}
            </li>
          ))}
        </ul>
      </details>
      <p className="text-sm text-muted">
        These numbers come from your own event log and are shown as hypotheses, never as a score of you.
      </p>
    </div>
  )
}

export function Experiments() {
  const list = useExperiments()
  const { fromTemplate, start, stop } = useExperimentActions()
  const [open, setOpen] = useState<string | null>(null)
  const experiments = list.data?.experiments ?? []
  const templates = (list.data?.templates ?? []) as Array<{ id: string; name: string; hypothesis: string }>
  return (
    <div className="grid gap-4">
      <Card>
        <CardTitle>Experiments (n-of-1)</CardTitle>
        <p className="text-sm text-muted mb-3">
          Compare two ways of learning on matched skills or sessions. You start it, you stop it, and you read
          the result. While one runs, the session screen says which arm is active.
        </p>
        {experiments.length === 0 && (
          <p className="text-sm">No experiments yet. Start one from a template below.</p>
        )}
        <ul className="grid gap-2">
          {experiments.map((e) => (
            <li key={e.id} className="flex flex-wrap items-center gap-2 text-sm">
              <span className="font-medium">{e.name}</span>
              <span className="text-muted">
                {e.status} · {e.unit_type} · {e.metric} ·{' '}
                {e.arms.map((a) => `${a.name} (${a.assigned})`).join(' vs ')}
              </span>
              {e.status === 'draft' && (
                <Button size="sm" variant="primary" onClick={() => start.mutate(e.id)}>
                  Start
                </Button>
              )}
              {e.status === 'running' && (
                <Button size="sm" onClick={() => stop.mutate(e.id)}>
                  Stop
                </Button>
              )}
              <Button size="sm" pressed={open === e.id} onClick={() => setOpen(open === e.id ? null : e.id)}>
                Results
              </Button>
            </li>
          ))}
        </ul>
        {(start.isError || stop.isError) && (
          <p role="alert" className="text-warn mt-2">
            {((start.error ?? stop.error) as Error).message}
          </p>
        )}
      </Card>
      {open && (
        <Card>
          <CardTitle>Results</CardTitle>
          <Dashboard id={open} />
        </Card>
      )}
      <details className="rounded-lg border border-line bg-card p-4 shadow-sm">
        <summary className="cursor-pointer font-medium">New experiment from a template</summary>
        <ul className="grid gap-2 mt-3">
          {templates.map((t) => (
            <li key={t.id} className="flex flex-wrap items-center gap-2 text-sm">
              <span className="font-medium">{t.name}</span>
              <span className="text-muted">{t.hypothesis}</span>
              <Button size="sm" onClick={() => fromTemplate.mutate(t.id)} disabled={fromTemplate.isPending}>
                Create
              </Button>
            </li>
          ))}
        </ul>
      </details>
    </div>
  )
}
