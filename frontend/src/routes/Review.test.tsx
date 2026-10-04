import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { Link, MemoryRouter, Route, Routes } from 'react-router-dom'
import { useMode } from '../stores/mode'
import { jsonResponse, renderApp } from '../test/utils'
import { Review } from './Review'

const due = {
  items: [
    {
      content_version: 'v1',
      item_id: 'i1',
      skill_id: 'k1',
      skill_title: 'Softmax',
      item_type: 'mcq',
      question: 'softmax([10,20,30])?',
      options: ['a', 'b'],
      reveal: 'b — largest dominates',
      due: 'x',
      state: 'review',
    },
    {
      content_version: 'v1',
      item_id: 'i2',
      skill_id: 'k1',
      skill_title: 'Softmax',
      item_type: 'cloze',
      question: 'softmax divides by the ___ of exponentials',
      options: null,
      reveal: 'sum',
      due: 'x',
      state: 'review',
    },
  ],
  cap: 5,
  total_due: 7,
  as_of: 'now',
}

const reviewSession = {
  id: 's1',
  mode: 'steady',
  energy: 3,
  socratic: false,
  started_at: 'now',
  ended_at: null,
  energy_after: null,
  next_skill: null,
  due_reviews: 7,
  review_cap: 5,
  minimum_viable: ['retrieval', 'recap'],
  plan: [
    { type: 'retrieval', planned_min: 8, node_ids: [], optional: false, reason: '' },
    { type: 'new_material', planned_min: 20, node_ids: ['k1'], optional: false, reason: '' },
  ],
  checkpoint: {},
  experiment: null,
  state: {
    block_index: 0,
    block: { type: 'retrieval', planned_min: 8, node_ids: [], optional: false, reason: '' },
    block_id: 's1:0',
    block_status: 'running',
    block_started_at: 'now',
    phase: 'review',
    skill_id: 'k1',
    next_index: 1,
    plan_version: 1,
    timer_extension_min: 0,
    plan_complete: false,
    allowed: true,
    message: '',
  },
}

describe('Review', () => {
  afterEach(() => {
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
    sessionStorage.clear()
  })

  it('waits for delayed session state before saving Stop and opening recap', async () => {
    useMode.setState({ sessionId: 's1' })
    let release!: (response: Response) => void
    const sessionRead = new Promise<Response>((resolve) => {
      release = resolve
    })
    const ended = vi.fn()
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string) => {
        if (url.endsWith('/api/skills')) return jsonResponse({ skills: [], next_skill_id: null })
        if (url.startsWith('/api/review/due')) return jsonResponse(due)
        if (url.endsWith('/api/sessions/s1')) return sessionRead
        if (url.endsWith('/api/plan/blocks/end')) {
          ended()
          return jsonResponse({ ...reviewSession.state, block_status: 'ended' })
        }
        return jsonResponse(null)
      }),
    )
    renderApp(
      <Routes>
        <Route path="/" element={<Review />} />
        <Route path="/recap" element={<p>RECAP SCREEN</p>} />
      </Routes>,
    )
    await screen.findByRole('button', { name: 'Show answer' })
    fireEvent.click(screen.getByRole('button', { name: 'Stop here (save progress)' }))
    expect(screen.queryByText('RECAP SCREEN')).not.toBeInTheDocument()
    expect(ended).not.toHaveBeenCalled()
    await act(async () => {
      release(jsonResponse(reviewSession))
    })
    await screen.findByText('RECAP SCREEN')
    expect(ended).toHaveBeenCalledTimes(1)
  })

  it('keeps the review visible when Stop cannot read session state and permits retry', async () => {
    useMode.setState({ sessionId: 's1' })
    let fail = true
    const ended = vi.fn()
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string) => {
        if (url.endsWith('/api/skills')) return jsonResponse({ skills: [], next_skill_id: null })
        if (url.startsWith('/api/review/due')) return jsonResponse(due)
        if (url.endsWith('/api/sessions/s1')) {
          if (fail) throw new Error('Session unavailable')
          return jsonResponse(reviewSession)
        }
        if (url.endsWith('/api/plan/blocks/end')) {
          ended()
          return jsonResponse({ ...reviewSession.state, block_status: 'ended' })
        }
        return jsonResponse(null)
      }),
    )
    renderApp(
      <Routes>
        <Route path="/" element={<Review />} />
        <Route path="/recap" element={<p>RECAP SCREEN</p>} />
      </Routes>,
    )
    await screen.findByRole('button', { name: 'Show answer' })
    fireEvent.click(screen.getByRole('button', { name: 'Stop here (save progress)' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Session unavailable')
    expect(ended).not.toHaveBeenCalled()
    expect(screen.queryByText('RECAP SCREEN')).not.toBeInTheDocument()
    fail = false
    fireEvent.click(screen.getByRole('button', { name: 'Stop here (save progress)' }))
    await screen.findByText('RECAP SCREEN')
    expect(ended).toHaveBeenCalledTimes(1)
  })

  it('does not navigate back to recap after leaving while Stop saves', async () => {
    useMode.setState({ sessionId: 's1' })
    let release!: (response: Response) => void
    const save = new Promise<Response>((resolve) => {
      release = resolve
    })
    const ending = vi.fn()
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string) => {
        if (url.endsWith('/api/skills')) return jsonResponse({ skills: [], next_skill_id: null })
        if (url.startsWith('/api/review/due')) return jsonResponse(due)
        if (url.endsWith('/api/sessions/s1')) return jsonResponse(reviewSession)
        if (url.endsWith('/api/plan/blocks/end')) {
          ending()
          return save
        }
        return jsonResponse(null)
      }),
    )
    renderApp(
      <Routes>
        <Route
          path="/"
          element={
            <>
              <Link to="/home">Leave review</Link>
              <Review />
            </>
          }
        />
        <Route path="/home" element={<p>HOME SCREEN</p>} />
        <Route path="/recap" element={<p>RECAP SCREEN</p>} />
      </Routes>,
    )
    await screen.findByRole('button', { name: 'Show answer' })
    fireEvent.click(screen.getByRole('button', { name: 'Stop here (save progress)' }))
    await waitFor(() => expect(ending).toHaveBeenCalledTimes(1))
    fireEvent.click(screen.getByRole('link', { name: 'Leave review' }))
    await screen.findByText('HOME SCREEN')
    await act(async () => {
      release(jsonResponse({ ...reviewSession.state, block_status: 'ended' }))
    })
    expect(screen.getByText('HOME SCREEN')).toBeInTheDocument()
    expect(screen.queryByText('RECAP SCREEN')).not.toBeInTheDocument()
  })

  it('reveals before rating, sends confidence per card, resets it, and advances the plan when done', async () => {
    useMode.setState({ sessionId: 's1' })
    const posts: Array<[string, unknown]> = []
    const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
      if (url.endsWith('/api/skills')) return jsonResponse({ skills: [], next_skill_id: null })
      if (url.startsWith('/api/review/due')) return jsonResponse(due)
      if (url.endsWith('/api/sessions/s1')) return jsonResponse(reviewSession)
      if (init?.method === 'POST') posts.push([url, JSON.parse(String(init.body))])
      if (url.endsWith('/api/plan/blocks/next'))
        return jsonResponse({ ...reviewSession.state, block_index: 1, phase: 'teach', block_id: 's1:1' })
      return jsonResponse({
        item_id: url.split('/').at(-1),
        due: 'later',
        state: 'review',
        stability: 3,
        predicted_retrievability: 0.9,
      })
    })
    vi.stubGlobal('fetch', fetchMock)
    renderApp(
      <Routes>
        <Route path="/" element={<Review />} />
        <Route path="/session" element={<p>SESSION SCREEN</p>} />
      </Routes>,
    )
    expect(await screen.findByText(/capped at 5; 7 due in total/)).toBeInTheDocument()
    expect(screen.queryByText(/largest dominates/)).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: /show answer/i })).toBeEnabled()
    fireEvent.click(screen.getByText('Confidence (optional)'))
    fireEvent.click(screen.getByRole('button', { name: '4' }))
    fireEvent.click(screen.getByRole('button', { name: /show answer/i }))
    expect(screen.getByText(/largest dominates/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /good/i }))
    await waitFor(() => expect(posts.some(([u]) => u === '/api/review/i1')).toBe(true))
    expect(posts.find(([u]) => u === '/api/review/i1')?.[1]).toMatchObject({
      session_id: 's1',
      rating: 3,
      confidence_pre: 4,
    })
    // second card: confidence is reset, so "Show answer" is disabled again until chosen
    expect(await screen.findByText(/Review 2 of 2/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /show answer/i })).toBeEnabled()
    fireEvent.click(screen.getByText('Confidence (optional)'))
    fireEvent.click(screen.getByRole('button', { name: '2' }))
    fireEvent.click(screen.getByRole('button', { name: /show answer/i }))
    fireEvent.click(screen.getByRole('button', { name: /^again/i }))
    await waitFor(() => expect(posts.filter(([u]) => u.startsWith('/api/review/i')).length).toBe(2))
    expect(posts.find(([u]) => u === '/api/review/i2')?.[1]).toMatchObject({ rating: 1, confidence_pre: 2 })
    expect(await screen.findByText(/review done/i)).toBeInTheDocument()
    expect(screen.queryByText('Nothing is due right now.')).not.toBeInTheDocument()
    expect(screen.queryByText(/show all 7 due/i)).not.toBeInTheDocument()
    // the review block is part of the plan: "Continue the plan" advances on the server
    fireEvent.click(screen.getByRole('button', { name: /continue the plan/i }))
    expect(await screen.findByText('SESSION SCREEN')).toBeInTheDocument()
    expect(posts.find(([u]) => u.endsWith('/api/plan/blocks/next'))?.[1]).toMatchObject({
      session_id: 's1',
      from_index: 0,
      reason: 'finished',
    })
  })
  it('keeps B when Show all refetches after A was rated, including remount', async () => {
    useMode.setState({ sessionId: 's1' })
    let rated = false
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string, init?: RequestInit) => {
        if (url.endsWith('/api/skills')) return jsonResponse({ skills: [] })
        if (url.startsWith('/api/review/due'))
          return jsonResponse(rated ? { ...due, items: [due.items[1]] } : due)
        if (url.endsWith('/api/sessions/s1')) return jsonResponse(reviewSession)
        if (init?.method === 'POST') rated = true
        return jsonResponse({ item_id: url.split('/').at(-1) })
      }),
    )
    const view = renderApp(<Review />)
    fireEvent.click(await screen.findByRole('button', { name: /show answer/i }))
    fireEvent.click(screen.getByRole('button', { name: /^good/i }))
    await screen.findByText(due.items[1].question)
    fireEvent.click(screen.getByRole('button', { name: /show all/i }))
    await waitFor(() => expect(screen.queryByText('Loading review…')).not.toBeInTheDocument())
    expect(screen.getByText(due.items[1].question)).toBeInTheDocument()
    expect(screen.queryByText('Review done')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /show answer/i }))
    view.unmount()
    renderApp(<Review />)
    expect(await screen.findByText(due.items[1].question)).toBeInTheDocument()
    expect(screen.getByText('sum')).toBeInTheDocument()
  })
  it('does not expand the capped set on remount and offers explicit expansion after completion', async () => {
    useMode.setState({ sessionId: 's1' })
    sessionStorage.setItem(
      'audhs-review-queue:v1:s1',
      JSON.stringify({
        version: 1,
        admitted: ['i1', 'i2'],
        reviewed: ['i1'],
        current: 'i2',
        revealed: null,
        all: false,
      }),
    )
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string) => {
        if (url.startsWith('/api/review/due'))
          return jsonResponse({
            ...due,
            items: [due.items[1], { ...due.items[0], item_id: 'i3', question: 'New card C' }],
          })
        if (url.endsWith('/api/sessions/s1')) return jsonResponse(reviewSession)
        return jsonResponse({ skills: [], item_id: url.split('/').at(-1) })
      }),
    )
    renderApp(<Review />)
    expect(await screen.findByText(/Review 2 of 2/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /show answer/i }))
    fireEvent.click(screen.getByRole('button', { name: /^good/i }))
    expect(await screen.findByText('Review done')).toBeInTheDocument()
    expect(screen.queryByText('New card C')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /show all due cards/i }))
    expect(await screen.findByText('New card C')).toBeInTheDocument()
  })

  it('recovers a rating explicitly after unmount without adopting a late response', async () => {
    useMode.setState({ sessionId: 's1' })
    let finish!: (r: Response) => void
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string, init?: RequestInit) => {
        if (url.startsWith('/api/review/due')) return jsonResponse(due)
        if (url.startsWith('/api/review/requests/'))
          return jsonResponse({ status: 'completed', result: { item_id: 'i1' } })
        if (url.endsWith('/api/sessions/s1')) return jsonResponse(reviewSession)
        if (url === '/api/review/i1' && init?.method === 'POST')
          return new Promise<Response>((resolve) => {
            finish = resolve
          })
        return jsonResponse({ skills: [] })
      }),
    )
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: Infinity } } })
    const mount = () =>
      render(
        <QueryClientProvider client={qc}>
          <MemoryRouter>
            <Review />
          </MemoryRouter>
        </QueryClientProvider>,
      )
    const view = mount()
    fireEvent.click(await screen.findByRole('button', { name: /show answer/i }))
    fireEvent.click(screen.getByRole('button', { name: /^good/i }))
    await waitFor(() => expect(finish).toBeDefined())
    view.unmount()
    const pendingView = mount()
    expect(await screen.findByRole('button', { name: /^good/i })).toBeDisabled()
    pendingView.unmount()
    await act(async () => {
      finish(jsonResponse({ item_id: 'i1' }))
      await new Promise((resolve) => setTimeout(resolve, 0))
    })
    mount()
    fireEvent.click(await screen.findByRole('button', { name: 'Check saved rating' }))
    fireEvent.click(await screen.findByRole('button', { name: 'Update review queue' }))
    expect(await screen.findByText(due.items[1].question)).toBeInTheDocument()
    expect(screen.queryByText(due.items[0].question)).not.toBeInTheDocument()
    expect(screen.queryByText(due.items[0].reveal)).not.toBeInTheDocument()
  })
  it('keeps a completed identity across checkpoint failure and reload, then advances without rating again', async () => {
    useMode.setState({ sessionId: 's1' })
    let posts = 0
    let denyCheckpoint = false
    const originalSet = Storage.prototype.setItem
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(function (this: Storage, key, value) {
      if (denyCheckpoint && key === 'audhs-review-queue:v1:s1') throw new Error('quota')
      originalSet.call(this, key, value)
    })
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string, init?: RequestInit) => {
        if (url.startsWith('/api/review/due')) return jsonResponse(due)
        if (url.startsWith('/api/review/requests/'))
          return jsonResponse({ status: 'completed', result: { item_id: 'i1' } })
        if (url.endsWith('/api/sessions/s1')) return jsonResponse(reviewSession)
        if (url === '/api/review/i1' && init?.method === 'POST') {
          posts++
          denyCheckpoint = true
          return jsonResponse({ item_id: 'i1' })
        }
        return jsonResponse({ skills: [] })
      }),
    )
    const view = renderApp(<Review />)
    fireEvent.click(await screen.findByRole('button', { name: /show answer/i }))
    fireEvent.click(screen.getByRole('button', { name: /^again/i }))
    await screen.findByText(/review queue could not be stored/)
    const intent = sessionStorage.getItem('review-request:v1:s1')
    expect(intent).not.toBeNull()
    view.unmount()
    renderApp(<Review />)
    fireEvent.click(await screen.findByRole('button', { name: 'Check saved rating' }))
    fireEvent.click(await screen.findByRole('button', { name: 'Update review queue' }))
    await waitFor(() =>
      expect(screen.getAllByText(/review queue could not be stored/).length).toBeGreaterThan(0),
    )
    expect(sessionStorage.getItem('review-request:v1:s1')).toBe(intent)
    denyCheckpoint = false
    fireEvent.click(screen.getByRole('button', { name: 'Update review queue' }))
    await waitFor(() =>
      expect(screen.queryByRole('region', { name: 'Review submission recovery' })).not.toBeInTheDocument(),
    )
    expect(screen.getByText(due.items[1].question)).toBeInTheDocument()
    expect(JSON.parse(sessionStorage.getItem('audhs-review-queue:v1:s1')!).reviewed).toContain('i1')
    expect(sessionStorage.getItem('review-request:v1:s1')).toBeNull()
    expect(posts).toBe(1)
  })

  it('resets confidence and timing after recovering the previous card', async () => {
    useMode.setState({ sessionId: 's1' })
    const clock = vi.spyOn(Date, 'now').mockReturnValue(1000)
    let secondBody: Record<string, unknown> | undefined
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string, init?: RequestInit) => {
        if (url.startsWith('/api/review/due')) return jsonResponse(due)
        if (url.startsWith('/api/review/requests/'))
          return jsonResponse({ status: 'completed', result: { item_id: 'i1' } })
        if (url.endsWith('/api/sessions/s1')) return jsonResponse(reviewSession)
        if (url === '/api/review/i1' && init?.method === 'POST') throw new Error('Lost response')
        if (url === '/api/review/i2' && init?.method === 'POST') {
          secondBody = JSON.parse(String(init.body))
          return jsonResponse({ item_id: 'i2' })
        }
        return jsonResponse({ skills: [] })
      }),
    )
    renderApp(<Review />)
    await screen.findByRole('button', { name: /show answer/i })
    fireEvent.click(screen.getByText('Confidence (optional)'))
    fireEvent.click(screen.getByRole('button', { name: '4' }))
    fireEvent.click(screen.getByRole('button', { name: /show answer/i }))
    fireEvent.click(screen.getByRole('button', { name: /^good/i }))
    await screen.findByText(/Lost response/)
    fireEvent.click(screen.getByRole('button', { name: 'Check saved rating' }))
    await screen.findByRole('button', { name: 'Update review queue' })
    clock.mockReturnValue(10000)
    fireEvent.click(screen.getByRole('button', { name: 'Update review queue' }))
    await screen.findByText(due.items[1].question)
    expect(screen.queryByRole('button', { name: 'Skip confidence' })).not.toBeInTheDocument()
    clock.mockReturnValue(10500)
    fireEvent.click(screen.getByRole('button', { name: /show answer/i }))
    fireEvent.click(screen.getByRole('button', { name: /^good/i }))
    await waitFor(() => expect(secondBody).toBeDefined())
    expect(secondBody?.confidence_pre).toBeUndefined()
    expect(secondBody?.latency_ms).toBe(500)
  })
})

it('does not restore a revealed answer against a changed content version', async () => {
  useMode.setState({ sessionId: 'version-reload' })
  sessionStorage.setItem(
    'audhs-review-queue:v1:version-reload',
    JSON.stringify({
      version: 1,
      admitted: ['i1'],
      reviewed: [],
      current: 'i1',
      revealed: 'i1',
      revealedVersion: 'old',
      all: false,
    }),
  )
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      if (url.startsWith('/api/review/due')) return jsonResponse({ ...due, items: [due.items[0]] })
      if (url.includes('/api/sessions/')) return jsonResponse(reviewSession)
      return jsonResponse({ skills: [] })
    }),
  )
  renderApp(<Review />)
  expect(await screen.findByRole('button', { name: 'Show answer' })).toBeInTheDocument()
  expect(screen.queryByRole('button', { name: /^Good/ })).not.toBeInTheDocument()
  sessionStorage.clear()
  vi.unstubAllGlobals()
})

it('retains the revealed card during a failed background refresh and explicit retry', async () => {
  sessionStorage.clear()
  useMode.setState({ sessionId: 's1' })
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  let fail = false
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      if (url.startsWith('/api/review/due'))
        return fail
          ? jsonResponse({ error: { code: 'offline', message: 'Offline' } }, 503)
          : jsonResponse(due)
      if (url.includes('/api/sessions/')) return jsonResponse(reviewSession)
      return jsonResponse({ skills: [] })
    }),
  )
  const mounted = render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <Review />
      </MemoryRouter>
    </QueryClientProvider>,
  )
  try {
    fireEvent.click(await screen.findByRole('button', { name: 'Show answer' }))
    const card = screen.getByText(due.items[0].reveal)
    fail = true
    await act(async () => {
      await qc.invalidateQueries({ queryKey: ['due', 's1'] })
    })
    expect(await screen.findByText(/Could not refresh review cards/)).toBeInTheDocument()
    expect(screen.getByText(due.items[0].reveal)).toBe(card)
    expect(screen.getByRole('button', { name: /^Good/ })).toBeEnabled()
    fail = false
    fireEvent.click(screen.getByRole('button', { name: 'Retry review cards' }))
    await waitFor(() => expect(screen.queryByText(/Could not refresh review cards/)).not.toBeInTheDocument())
    expect(screen.getByText(due.items[0].reveal)).toBe(card)
  } finally {
    mounted.unmount()
    qc.clear()
    sessionStorage.clear()
    vi.unstubAllGlobals()
  }
})

it('does not report an empty review when its initial read fails', async () => {
  sessionStorage.clear()
  useMode.setState({ sessionId: 's1' })
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      if (url.startsWith('/api/review/due')) return jsonResponse({}, 503)
      if (url.includes('/api/sessions/')) return jsonResponse(reviewSession)
      return jsonResponse({ skills: [] })
    }),
  )
  const mounted = renderApp(<Review />)
  try {
    expect(await screen.findByRole('alert')).toHaveTextContent('Could not load review cards')
    expect(screen.queryByText('Review done')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Go to Home' })).toBeEnabled()
    expect(screen.getByRole('button', { name: 'End session' })).toBeEnabled()
  } finally {
    mounted.unmount()
    vi.unstubAllGlobals()
  }
})
