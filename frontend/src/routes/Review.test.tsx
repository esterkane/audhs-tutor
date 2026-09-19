import { fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
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
  ],
  cap: 5,
  total_due: 7,
  as_of: 'now',
}

describe('Review', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('reveals before rating, shows the cap honestly, and posts the FSRS rating', async () => {
    useMode.setState({ sessionId: 's1' })
    const fetchMock = vi.fn(async (url: string) =>
      url.startsWith('/api/review/due')
        ? jsonResponse(due)
        : jsonResponse({
            item_id: 'i1',
            due: 'later',
            state: 'review',
            stability: 3,
            predicted_retrievability: 0.9,
          }),
    )
    vi.stubGlobal('fetch', fetchMock)
    renderApp(<Review />)
    expect(await screen.findByText(/capped at 5; 7 due in total/)).toBeInTheDocument()
    expect(screen.queryByText(/largest dominates/)).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /show answer/i }))
    expect(screen.getByText(/largest dominates/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /good/i }))
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2))
    const [url, init] = fetchMock.mock.calls[1] as unknown as [string, RequestInit]
    expect(url).toBe('/api/review/i1')
    expect(JSON.parse(init.body as string)).toMatchObject({
      session_id: 's1',
      rating: 3,
    })
    expect(await screen.findByText(/review done/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /finish session/i })).toBeInTheDocument()
  })
})
