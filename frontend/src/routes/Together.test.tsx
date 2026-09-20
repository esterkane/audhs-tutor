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
            next_skill: { id: 'k', title: 'Softmax' },
          })
        if (url.endsWith('/api/preferences'))
          return jsonResponse({ values: { 'ui.ambient': 'off' }, specs: [] })
        return jsonResponse({})
      }),
    )
    renderApp(<Together />)
    expect(await screen.findByText('Now: Softmax')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /brown noise/i })).not.toBeInTheDocument()
    expect(screen.getByText(/nothing is timed, tracked or scored/)).toBeInTheDocument()
  })
})
