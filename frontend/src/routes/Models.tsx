import { useState } from 'react'
import { Button } from '../components/ui/button'
import { Card, CardTitle } from '../components/ui/card'
import {
  useJobs,
  useModelActions,
  useModels,
  useRouting,
  useSearchModels,
  type ModelRow,
} from '../features/models/api'

const SOURCES = ['ollama_library', 'huggingface_gguf', 'huggingface_mlx', 'huggingface_fastembed', 'hosted']
const ROLES = ['chat', 'code', 'embed', 'rerank', 'judge', 'stt', 'tts']

function benchSummary(b: Record<string, unknown> | null | undefined): string {
  if (!b) return '—'
  if (typeof b.ms_per_16_docs === 'number') return `${b.ms_per_16_docs} ms / 16 docs`
  const parts: string[] = []
  if (typeof b.tok_per_s === 'number') parts.push(`${(b.tok_per_s as number).toFixed(1)} tok/s`)
  if (typeof b.first_token_ms === 'number') parts.push(`first token ${b.first_token_ms} ms`)
  const hc = b.tutoring_hard_checks as { passed?: number; total?: number } | undefined
  if (hc && typeof hc.passed === 'number') parts.push(`tutoring checks ${hc.passed}/${hc.total ?? '?'}`)
  return parts.join(' · ') || JSON.stringify(b).slice(0, 40)
}

function Row({ m, busy, onStart }: { m: ModelRow; busy: boolean; onStart: () => void }) {
  const { pull, bench, remove } = useModelActions()
  const canPull = ['available', 'failed', 'removed'].includes(m.status)
  return (
    <tr>
      <td className="pr-2 font-medium">{m.display_name}</td>
      <td className="pr-2">{m.runtime}</td>
      <td className="pr-2">{m.role}</td>
      <td className="pr-2">{m.status}</td>
      <td className="pr-2">{m.size_gb != null ? `${m.size_gb.toFixed(1)} GB` : '—'}</td>
      <td className="pr-2">{m.licence ?? '—'}</td>
      <td className="pr-2">{benchSummary(m.benchmark as Record<string, unknown> | null)}</td>
      <td className="flex gap-1">
        {canPull && (
          <Button
            size="sm"
            disabled={busy}
            onClick={() => {
              onStart()
              pull.mutate(m.id)
            }}
          >
            Download
          </Button>
        )}
        {m.status === 'ready' && (
          <Button
            size="sm"
            disabled={busy}
            onClick={() => {
              onStart()
              bench.mutate(m.id)
            }}
          >
            Bench
          </Button>
        )}
        {m.status === 'ready' && m.runtime !== 'hosted' && (
          <Button
            size="sm"
            variant="ghost"
            onClick={() => {
              if (window.confirm(`Remove ${m.display_name} from disk?`)) remove.mutate(m.id)
            }}
          >
            Remove
          </Button>
        )}
      </td>
    </tr>
  )
}

function AddForm() {
  const { add } = useModelActions()
  const search = useSearchModels()
  const [q, setQ] = useState('')
  const [gguf, setGguf] = useState(true)
  const [form, setForm] = useState({
    source: 'huggingface_gguf',
    repo_id: '',
    file: '',
    tag: '',
    role: 'chat',
  })
  return (
    <div className="grid gap-3">
      <form
        className="flex flex-wrap gap-2 items-end"
        onSubmit={(e) => {
          e.preventDefault()
          search.mutate({ q, gguf, mlx: false })
        }}
      >
        <label className="text-sm font-medium grow">
          Search Hugging Face
          <input
            className="block w-full border border-line rounded-md px-2 py-1 mt-1"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            required
          />
        </label>
        <label className="text-sm font-medium flex items-center gap-1 h-10">
          <input type="checkbox" checked={gguf} onChange={(e) => setGguf(e.target.checked)} /> GGUF only
        </label>
        <Button type="submit" disabled={search.isPending || !q}>
          Search
        </Button>
      </form>
      {search.data && (
        <ul className="text-sm grid gap-1">
          {search.data.hits.map((h) => (
            <li key={h.repo_id} className="flex flex-wrap items-center gap-2">
              <span className="grow">
                {h.repo_id} <span className="text-muted">· {h.downloads ?? 0} downloads</span>
              </span>
              <Button size="sm" onClick={() => setForm({ ...form, repo_id: h.repo_id })}>
                Use
              </Button>
            </li>
          ))}
        </ul>
      )}
      <form
        className="flex flex-wrap gap-2 items-end"
        onSubmit={(e) => {
          e.preventDefault()
          add.mutate({
            source: form.source,
            repo_id: form.repo_id,
            file: form.file || null,
            tag: form.tag || null,
            role: form.role,
            price_in: 0,
            price_out: 0,
          })
        }}
      >
        <label className="text-sm font-medium">
          Source
          <select
            className="block border border-line rounded-md px-2 py-1 mt-1"
            value={form.source}
            onChange={(e) => setForm({ ...form, source: e.target.value })}
          >
            {SOURCES.map((s) => (
              <option key={s}>{s}</option>
            ))}
          </select>
        </label>
        <label className="text-sm font-medium grow">
          Repo id
          <input
            className="block w-full border border-line rounded-md px-2 py-1 mt-1"
            value={form.repo_id}
            onChange={(e) => setForm({ ...form, repo_id: e.target.value })}
            required
          />
        </label>
        <label className="text-sm font-medium">
          GGUF file / hosted tag
          <input
            className="block border border-line rounded-md px-2 py-1 mt-1"
            value={form.source === 'hosted' ? form.tag : form.file}
            onChange={(e) =>
              setForm(
                form.source === 'hosted'
                  ? { ...form, tag: e.target.value }
                  : { ...form, file: e.target.value },
              )
            }
          />
        </label>
        <label className="text-sm font-medium">
          Role
          <select
            className="block border border-line rounded-md px-2 py-1 mt-1"
            value={form.role}
            onChange={(e) => setForm({ ...form, role: e.target.value })}
          >
            {ROLES.map((r) => (
              <option key={r}>{r}</option>
            ))}
          </select>
        </label>
        <Button type="submit" variant="primary" disabled={add.isPending || !form.repo_id}>
          Add to registry
        </Button>
      </form>
      {add.isError && (
        <p role="alert" className="text-warn">
          {(add.error as Error).message}
        </p>
      )}
    </div>
  )
}

function RoutingTable() {
  const routing = useRouting()
  const models = useModels()
  const { assign } = useModelActions()
  const ready = (models.data?.models ?? []).filter((m) => m.status === 'ready' && m.benchmark)
  if (!routing.data) return null
  return (
    <table className="w-full text-sm">
      <caption className="text-left text-muted mb-1">
        Routing profile "{routing.data.profile}": which model each task uses
      </caption>
      <thead>
        <tr className="text-left text-muted">
          <th scope="col" className="pr-2">
            Task
          </th>
          <th scope="col" className="pr-2">
            Uses
          </th>
          <th scope="col" className="pr-2">
            Chain
          </th>
          <th scope="col">Override</th>
        </tr>
      </thead>
      <tbody>
        {routing.data.routes.map((r) => (
          <tr key={r.task}>
            <td className="pr-2">{r.task}</td>
            <td className="pr-2 font-medium">{r.resolved ?? 'none ready'}</td>
            <td className="pr-2 text-muted">
              {r.chain.map((c) => `${c.registry_id} (${c.status})`).join(' → ')}
            </td>
            <td>
              <select
                className="border border-line rounded-md px-1 py-0.5"
                value={r.override ?? ''}
                aria-label={`Override for ${r.task}`}
                onChange={(e) => {
                  if (e.target.value) assign.mutate({ id: e.target.value, task: r.task })
                }}
              >
                <option value="">profile default</option>
                {ready.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.id}
                  </option>
                ))}
              </select>
            </td>
          </tr>
        ))}
      </tbody>
      {assign.isError && (
        <tfoot>
          <tr>
            <td colSpan={4} role="alert" className="text-warn">
              {(assign.error as Error).message}
            </td>
          </tr>
        </tfoot>
      )}
    </table>
  )
}

export function Models() {
  const models = useModels()
  const [polling, setPolling] = useState(false)
  const jobs = useJobs(polling)
  const running = (jobs.data?.jobs ?? []).filter((j) => j.status === 'running')
  const busy = running.length > 0
  return (
    <div className="grid gap-4">
      <Card>
        <CardTitle>Models</CardTitle>
        <p className="text-sm text-muted mb-2">
          Everything the tutor can run, where it comes from, whether it is downloaded and benchmarked, and
          which task uses it. Nothing downloads without your click.
        </p>
        {models.isLoading && <p>Loading…</p>}
        {models.data && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-muted">
                  <th scope="col" className="pr-2">
                    Model
                  </th>
                  <th scope="col" className="pr-2">
                    Runtime
                  </th>
                  <th scope="col" className="pr-2">
                    Role
                  </th>
                  <th scope="col" className="pr-2">
                    Status
                  </th>
                  <th scope="col" className="pr-2">
                    Size
                  </th>
                  <th scope="col" className="pr-2">
                    Licence
                  </th>
                  <th scope="col" className="pr-2">
                    Benchmark
                  </th>
                  <th scope="col">
                    <span className="sr-only">Actions</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {models.data.models.map((m) => (
                  <Row key={m.id} m={m} busy={busy} onStart={() => setPolling(true)} />
                ))}
              </tbody>
            </table>
          </div>
        )}
        {(jobs.data?.jobs ?? []).length > 0 && (
          <ul className="mt-3 text-sm grid gap-1" aria-label="Background jobs" role="status">
            {(jobs.data?.jobs ?? []).map((j) => (
              <li key={j.id}>
                {j.kind} {j.registry_id}: {j.status}
                {j.error ? ` — ${j.error}` : ''}
                {(j.log ?? []).length > 0 ? ` — ${(j.log ?? [])[(j.log ?? []).length - 1]}` : ''}
              </li>
            ))}
          </ul>
        )}
      </Card>
      <details className="rounded-lg border border-line bg-card p-4 shadow-sm">
        <summary className="cursor-pointer font-medium">Routing: which model does each task use</summary>
        <div className="mt-3 overflow-x-auto">
          <RoutingTable />
        </div>
      </details>
      <details className="rounded-lg border border-line bg-card p-4 shadow-sm">
        <summary className="cursor-pointer font-medium">Add a model (search Hugging Face)</summary>
        <div className="mt-3">
          <AddForm />
        </div>
      </details>
    </div>
  )
}
