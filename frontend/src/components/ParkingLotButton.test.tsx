import { fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { useMode } from '../stores/mode'
import { jsonResponse, renderApp } from '../test/utils'
import { ParkingLotButton } from './ParkingLotButton'

describe('ParkingLotButton', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('is always rendered and usable even without a session', () => {
    useMode.setState({ sessionId: null })
    renderApp(<ParkingLotButton />)
    expect(screen.getByRole('button', { name: /parking lot/i })).toBeEnabled()
  })

  it('parks a tangent in two interactions (open, type + Enter)', async () => {
    useMode.setState({ sessionId: 's1', skillId: 'k1' })
    const fetchMock = vi.fn(async () =>
      jsonResponse(
        {
          id: 'p1',
          text: 'RoPE',
          node_id: 'k1',
          status: 'parked',
          created_at: 'now',
        },
        201,
      ),
    )
    vi.stubGlobal('fetch', fetchMock)
    renderApp(<ParkingLotButton />)
    fireEvent.click(screen.getByRole('button', { name: /parking lot/i }))
    const box = await screen.findByLabelText(/tangent to park/i)
    fireEvent.change(box, { target: { value: 'look up RoPE' } })
    fireEvent.keyDown(box, { key: 'Enter' })
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1))
    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit]
    expect(url).toBe('/api/parking')
    expect(JSON.parse(init.body as string)).toEqual({
      session_id: 's1',
      text: 'look up RoPE',
      node_id: 'k1',
    })
  })
})
