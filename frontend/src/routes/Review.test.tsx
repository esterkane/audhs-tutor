import { fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { Route, Routes } from 'react-router-dom'
import { useMode } from '../stores/mode'
import { jsonResponse, renderApp } from '../test/utils'
import { Review } from './Review'

const due = {
  items: [
    {
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
  afterEach(() => vi.unstubAllGlobals())

  it('reveals before rating, sends confidence per card, resets it, and advances the plan when done', async () => {
    useMode.setState({ sessionId: 's1' })
    const posts: Array<[string, unknown]> = []
    const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
      if (url.startsWith('/api/review/due')) return jsonResponse(due)
      if (url.endsWith('/api/sessions/s1')) return jsonResponse(reviewSession)
      if (init?.method === 'POST') posts.push([url, JSON.parse(String(init.body))])
      if (url.endsWith('/api/plan/blocks/next'))
        return jsonResponse({ ...reviewSession.state, block_index: 1, phase: 'teach', block_id: 's1:1' })
      return jsonResponse({
        item_id: 'i1',
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
    expect(screen.getByRole('button', { name: /show answer/i })).toBeDisabled()
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
    expect(screen.getByRole('button', { name: /show answer/i })).toBeDisabled()
    fireEvent.click(screen.getByRole('button', { name: '2' }))
    fireEvent.click(screen.getByRole('button', { name: /show answer/i }))
    fireEvent.click(screen.getByRole('button', { name: /again/i }))
    await waitFor(() => expect(posts.filter(([u]) => u.startsWith('/api/review/i')).length).toBe(2))
    expect(posts.find(([u]) => u === '/api/review/i2')?.[1]).toMatchObject({ rating: 1, confidence_pre: 2 })
    expect(await screen.findByText(/review done/i)).toBeInTheDocument()
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
})
