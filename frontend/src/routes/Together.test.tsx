import { screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { jsonResponse, renderApp } from '../test/utils'
import { Together } from './Together'

describe('Together', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('shows the current task and offers ambient sound only when the preference allows it', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string) => {
        if (url.endsWith('/api/sessions/current'))
          return jsonResponse({
            id: 's1',
            mode: 'steady',
            energy: 3,
            active_skill: { id: 'k', title: 'Softmax' },
            next_skill: { id: 'other', title: 'Next recommendation' },
            state: { phase: 'review', block_status: 'running', plan_complete: false },
          })
        if (url.endsWith('/api/preferences'))
          return jsonResponse({ values: { 'ui.ambient': 'off' }, specs: [] })
        return jsonResponse({})
      }),
    )
    renderApp(<Together />)
    expect(await screen.findByText('Now: Softmax')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /brown noise/i })).not.toBeInTheDocument()
    expect(screen.getByText(/not a live human companion/)).toBeInTheDocument()
    expect(screen.queryByText(/Next recommendation/)).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Back to the session' })).toHaveAttribute('href', '/review')
  })
})
