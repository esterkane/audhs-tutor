import { act, fireEvent, render, screen, waitFor, cleanup } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, expect, it, vi } from 'vitest'
import { PrivateActivation } from './PrivateActivation'
import { activationKey, parseActivation } from './activationRecovery'

const command = { promotion_id: 'promotion', expected_version: 1, payload_sha256: 'a'.repeat(64) }
const receipt = {
  activation_id: 'activated',
  draft_id: 'draft',
  promotion_id: 'promotion',
  activated_version: 1,
  payload_sha256: command.payload_sha256,
  skill_ids: ['skill'],
  assessment_ids: ['assessment'],
  object_ids: ['object'],
  edge_ids: [],
}
const preview = {
  draft_id: 'draft',
  promotion_id: 'promotion',
  draft_version: 1,
  status: 'draft',
  command,
  skills: 1,
  assessments: 1,
  warnings: [],
  issues: [],
}
const stored = { version: 1 as const, draftId: 'draft', key: 'saved-key', command }
afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
  localStorage.clear()
})
function setup(
  options: {
    blocked?: boolean
    lost?: boolean
    committedLoss?: boolean
    deferred?: Promise<Response>
    value?: unknown
  } = {},
) {
  const posts: RequestInit[] = []
  let committed = false
  const fetch = vi.fn(async (_url: string, init?: RequestInit) => {
    if (init?.method === 'POST') {
      posts.push(init)
      if (options.deferred) return options.deferred
      if (options.committedLoss) {
        committed = true
        throw new Error('Connection lost')
      }
      if (options.lost) throw new Error('Connection lost')
      return new Response(JSON.stringify(receipt))
    }
    return new Response(
      JSON.stringify(committed ? { ...preview, command: null, receipt } : (options.value ?? preview)),
    )
  })
  vi.stubGlobal('fetch', fetch)
  const cache = new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: Infinity } } })
  cache.setQueryData(['learner'], { id: 'owner' })
  const refresh = vi.fn()
  const node = (
    <MemoryRouter>
      <QueryClientProvider client={cache}>
        <PrivateActivation
          draftId="draft"
          version={1}
          blocked={options.blocked ?? false}
          onBusy={vi.fn()}
          onRefresh={refresh}
        />
      </QueryClientProvider>
    </MemoryRouter>
  )
  return { posts, refresh, ...render(node) }
}
it('requires exact-version review and does not award evidence', async () => {
  const { posts } = setup()
  const button = await screen.findByRole('button', { name: 'Activate private lessons' })
  expect(button).toBeDisabled()
  fireEvent.click(screen.getByRole('checkbox'))
  fireEvent.click(button)
  fireEvent.click(button)
  await screen.findByText('Your private lesson is active.')
  expect(posts).toHaveLength(1)
  expect(JSON.parse(String(posts[0].body))).toEqual(command)
  expect(localStorage.getItem(activationKey('owner', 'draft'))).toBeNull()
  expect(screen.getByText(/does not award learning evidence/)).toBeVisible()
})
it('recovers without automatic submission and retries the identical request', async () => {
  localStorage.setItem(activationKey('owner', 'draft'), JSON.stringify(stored))
  const { posts } = setup()
  const retry = await screen.findByRole('button', { name: 'Retry saved activation' })
  expect(posts).toHaveLength(0)
  await waitFor(() => expect(retry).toBeEnabled())
  fireEvent.click(retry)
  await screen.findByText('Your private lesson is active.')
  expect((posts[0].headers as Record<string, string>)['Idempotency-Key']).toBe('saved-key')
})
it('retains an ambiguous request for retry after remount', async () => {
  const first = setup({ lost: true })
  await screen.findByRole('checkbox')
  fireEvent.click(screen.getByRole('checkbox'))
  fireEvent.click(screen.getByRole('button', { name: 'Activate private lessons' }))
  await screen.findByText('Connection lost')
  const saved = localStorage.getItem(activationKey('owner', 'draft'))!
  expect(parseActivation(saved, 'draft').command).toEqual(command)
  first.unmount()
  const next = setup()
  await screen.findByRole('button', { name: 'Retry saved activation' })
  expect(next.posts).toHaveLength(0)
})
it('never submits when browser recovery storage fails', async () => {
  const { posts } = setup()
  await screen.findByRole('checkbox')
  fireEvent.click(screen.getByRole('checkbox'))
  vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
    throw new Error('Full')
  })
  fireEvent.click(screen.getByRole('button', { name: 'Activate private lessons' }))
  await screen.findByText(/Nothing was sent/)
  expect(posts).toHaveLength(0)
})
it('blocks dirty drafts and does not show receipt defaults as preview counts', async () => {
  const view = setup({ blocked: true })
  expect(await screen.findByRole('button', { name: 'Activate private lessons' })).toBeDisabled()
  view.unmount()
  setup({ value: { ...preview, command: null, receipt, skills: 0, assessments: 0 } })
  await screen.findByText('Your private lesson is active.')
  expect(screen.queryByText(/0 lessons/)).not.toBeInTheDocument()
  expect(screen.queryByRole('button', { name: 'Activate private lessons' })).not.toBeInTheDocument()
})
it('does not enable activation for invalid source history', async () => {
  const { posts } = setup({ value: { ...preview, command: null, issues: ['Source history changed.'] } })
  await screen.findByText('Source history changed.')
  expect(screen.queryByRole('checkbox')).not.toBeInTheDocument()
  expect(posts).toHaveLength(0)
})
it('rejects foreign and malformed stored requests', () => {
  expect(() => parseActivation(JSON.stringify(stored), 'other')).toThrow()
  expect(() => parseActivation('broken', 'draft')).toThrow()
  expect(() =>
    parseActivation(JSON.stringify({ ...stored, command: { ...command, extra: true } }), 'draft'),
  ).toThrow()
})

it('keeps unreadable recovery until the learner explicitly replaces it', async () => {
  localStorage.setItem(activationKey('owner', 'draft'), 'broken')
  const { posts } = setup()
  await screen.findByText(/Saved activation recovery could not be read/)
  await waitFor(() =>
    expect(screen.getByRole('button', { name: 'Replace unreadable recovery' })).toBeEnabled(),
  )
  expect(localStorage.getItem(activationKey('owner', 'draft'))).toBe('broken')
  expect(screen.getByRole('button', { name: 'Activate private lessons' })).toBeDisabled()
  fireEvent.click(screen.getByRole('button', { name: 'Replace unreadable recovery' }))
  expect(posts).toHaveLength(0)
  expect(localStorage.getItem(activationKey('owner', 'draft'))).toBeNull()
})

it('shows confirmed success rather than an obsolete network error after lost commit response', async () => {
  const { posts } = setup({ committedLoss: true })
  await screen.findByRole('checkbox')
  fireEvent.click(screen.getByRole('checkbox'))
  fireEvent.click(screen.getByRole('button', { name: 'Activate private lessons' }))
  await screen.findByText('Your private lesson is active.')
  expect(screen.queryByText('Connection lost')).not.toBeInTheDocument()
  expect(posts).toHaveLength(1)
})

it('retains recovery and ignores a late response after leaving the draft', async () => {
  let resolve!: (value: Response) => void
  const deferred = new Promise<Response>((done) => {
    resolve = done
  })
  const view = setup({ deferred })
  await screen.findByRole('checkbox')
  fireEvent.click(screen.getByRole('checkbox'))
  fireEvent.click(screen.getByRole('button', { name: 'Activate private lessons' }))
  await waitFor(() => expect(view.posts).toHaveLength(1))
  view.unmount()
  await act(async () => {
    resolve(new Response(JSON.stringify(receipt)))
    await deferred
  })
  expect(view.refresh).not.toHaveBeenCalled()
  expect(localStorage.getItem(activationKey('owner', 'draft'))).not.toBeNull()
})
