import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { apiFetch, type Schemas } from '../../lib/api'
import { Button } from '../../components/ui/button'
import { Disclosure } from '../../components/ui/disclosure'

import { useAuthoringSetup } from './hybridAuthoringApi'

export function AuthoringSetup() {
  const query = useAuthoringSetup()
  const cache = useQueryClient()
  const [key, setKey] = useState('')
  const [editedCap, setCap] = useState<string | null>(null)
  const cap = editedCap ?? String(query.data?.daily_budget_usd || 5)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  async function configure(enabled: boolean) {
    setBusy(true)
    setMessage('')
    try {
      const dollars = Number(cap)
      if (!Number.isFinite(dollars) || dollars <= 0 || dollars > 1000)
        throw new Error('Set a daily limit between $0.01 and $1,000.')
      if (key) {
        await apiFetch('/api/authoring/key', { method: 'POST', body: JSON.stringify({ key }) })
        setKey('')
      }
      for (const [name, value] of [
        ['authoring.daily_budget_cents', Math.round(dollars * 100)],
        ['authoring.enabled', enabled],
      ]) {
        await apiFetch('/api/preferences', { method: 'PUT', body: JSON.stringify({ key: name, value }) })
      }
      await cache.invalidateQueries({ queryKey: ['authoring-setup'] })
      setMessage('Authoring settings saved.')
    } catch (e) {
      setMessage(e instanceof Error ? e.message : 'Settings could not be saved.')
    } finally {
      setBusy(false)
    }
  }
  const data = query.data
  return (
    <Disclosure label="Authoring setup: OpenAI or local">
      <div className="space-y-3 max-w-2xl">
        {query.isError && <p role="alert">Authoring settings could not load. Reload to retry.</p>}
        <p>
          OpenAI can help discuss research and draft material. Those requests send the selected source, your
          writing and relevant saved context to OpenAI. Accepted lessons and normal study stay local. Full
          histories stay saved here.
        </p>
        <p>
          {data?.enabled ? 'OpenAI authoring enabled' : 'Local authoring'} ·{' '}
          {data?.model_id ?? 'Loading model…'} ·{' '}
          {data?.key_configured ? 'API key configured' : 'API key needed for OpenAI'}
        </p>
        <p>
          Counted today: ${(data?.counted_today_usd ?? 0).toFixed(4)}. The app reserves estimated maximum cost
          before a call; unknown billing counts conservatively. Limit resets at midnight UTC. Other
          applications using this key are outside this app’s cap.
        </p>
        <label className="block">
          OpenAI API key
          <input
            className="block border rounded p-2 w-full"
            type="password"
            autoComplete="off"
            value={key}
            onChange={(e) => setKey(e.target.value)}
            placeholder={data?.key_configured ? 'Leave blank to keep saved key' : 'Enter key on this machine'}
          />
        </label>
        <p className="text-sm text-muted">
          Stored in a private local file, excluded from Git. Never included in a lesson, export or browser
          storage.
        </p>
        <label className="block">
          Daily authoring limit (USD)
          <input
            className="ml-2 w-24 rounded border border-line bg-card p-2"
            type="number"
            min="0.01"
            max="1000"
            step="0.01"
            value={cap}
            onChange={(e) => setCap(e.target.value)}
          />
        </label>
        <div className="flex flex-wrap gap-2">
          <Button disabled={busy} onClick={() => void configure(true)}>
            Use OpenAI for authoring
          </Button>
          <Button variant="secondary" disabled={busy} onClick={() => void configure(false)}>
            Use local authoring
          </Button>
        </div>
        {message && <p role="status">{message}</p>}
      </div>
    </Disclosure>
  )
}

export function FactualReviews({ draftId, onOpen }: { draftId: string; onOpen: (id: string) => void }) {
  const cache = useQueryClient()
  const path = `/api/knowledge-material/drafts/${draftId}/factual-review`
  const query = useQuery({
    queryKey: ['factual-review', draftId],
    queryFn: () => apiFetch<Schemas['FactualReviewOut'] | null>(path),
  })
  const [editedUrls, setUrls] = useState<string | null>(null)
  const urls = editedUrls ?? query.data?.urls.join('\n') ?? ''
  const [editedDays, setDays] = useState<number | null>(null)
  const days = editedDays ?? query.data?.interval_days ?? 30
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  async function action(kind: 'save' | 'run' | 'pause' | string) {
    setBusy(true)
    setMessage('')
    try {
      if (kind === 'save' || kind === 'pause')
        await apiFetch(path, {
          method: 'PUT',
          body: JSON.stringify({
            urls: urls
              .split('\n')
              .map((x) => x.trim())
              .filter(Boolean),
            interval_days: days,
            enabled: kind === 'save',
          }),
        })
      else if (kind === 'run') await apiFetch(`${path}/run`, { method: 'POST' })
      else {
        const revision = await apiFetch<Schemas['DraftOut']>(`${path}/revisions/${kind}`, { method: 'POST' })
        await cache.cancelQueries({ queryKey: ['curriculum', 'drafts'], exact: true })
        cache.setQueryData<Schemas['DraftList']>(['curriculum', 'drafts'], (previous) => ({
          drafts: [revision, ...(previous?.drafts ?? []).filter((d) => d.id !== revision.id)],
        }))
        onOpen(revision.id)
      }
      await query.refetch()
    } catch (e) {
      setMessage(e instanceof Error ? e.message : 'Review could not finish.')
    } finally {
      setBusy(false)
    }
  }
  return (
    <Disclosure label="Factual reviews and updates (optional)">
      <div className="space-y-3 max-w-2xl">
        <p>
          Choose up to three public documentation pages. While this app runs, due reviews fetch fresh excerpts
          and use your OpenAI authoring budget. Results are evidence-backed suggestions for your review.
          Accepted material stays unchanged until you explicitly activate a revision.
        </p>
        <label className="block">
          Reference URLs (one per line)
          <textarea
            className="block border rounded p-2 w-full"
            value={urls}
            onChange={(e) => setUrls(e.target.value)}
          />
        </label>
        <label className="block">
          Review every (days)
          <input
            className="ml-2 w-24 rounded border border-line bg-card p-2"
            type="number"
            min="1"
            max="365"
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
          />
        </label>
        <div className="flex flex-wrap gap-2">
          <Button disabled={busy || !urls.trim()} onClick={() => void action('save')}>
            Save review schedule
          </Button>
          <Button
            variant="secondary"
            disabled={busy || !query.data?.enabled}
            onClick={() => void action('run')}
          >
            Check references now
          </Button>
          <Button
            variant="secondary"
            disabled={busy || !query.data?.enabled}
            onClick={() => void action('pause')}
          >
            Pause reviews
          </Button>
        </div>
        {query.data && (
          <p>
            {query.data.enabled ? `Next due: ${query.data.next_due_at}` : 'Reviews paused'}. Checks resume
            when the app is running.
          </p>
        )}
        {busy && <p role="status">Checking or saving…</p>}
        {message && <p role="status">{message}</p>}
        {query.data?.history
          .slice()
          .reverse()
          .map((item) => {
            const proposal = item.proposal
            const sources = item.sources
            return (
              <article key={String(item.id)} className="border-t pt-3 space-y-2">
                <p>
                  {String(item.checked_at)} ·{' '}
                  {item.outcome === 'sources_unchanged'
                    ? 'Reference text unchanged; no new model review'
                    : item.outcome === 'reviewed'
                      ? 'Review proposal ready'
                      : 'Review failed; material unchanged'}
                </p>
                {item.error_message && <p>{item.error_message}</p>}
                {proposal?.findings.map((finding, i) => (
                  <div key={i}>
                    <p>
                      {finding.claim} · {finding.verdict.replaceAll('_', ' ')}
                    </p>
                    <blockquote>{finding.quote}</blockquote>
                    <p>{finding.explanation}</p>
                    <p className="break-all">{sources?.[finding.source_index - 1]?.url}</p>
                  </div>
                ))}
                {!!proposal?.proposed_explanation && (
                  <Disclosure label="Proposed explanation">
                    <p className="whitespace-pre-wrap">{proposal.proposed_explanation}</p>
                    <Button disabled={busy} onClick={() => void action(String(item.id))}>
                      Create update draft
                    </Button>
                  </Disclosure>
                )}
              </article>
            )
          })}
      </div>
    </Disclosure>
  )
}
