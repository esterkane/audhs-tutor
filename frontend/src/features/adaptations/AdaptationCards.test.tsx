import { fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { useMode } from '../../stores/mode'
import { jsonResponse, renderApp } from '../../test/utils'
import { AdaptationCards, AdaptationLog } from './AdaptationCards'

const card = {
  id: 'a1',
  what: 'Start new material with a worked example',
  why: 'You used 2.0 hints per attempt over the last 8 attempts.',
  origin: 'observed_pattern',
  pattern: 'hint_heavy',
  pref: 'tutor.representation_default',
  value: 'worked_example',
  evidence: { attempts: 8 },
  proposed_at: '2026-09-19T10:00:00+00:00',
  reversible: true,
}
const entry = {
  ...card,
  previous: '',
  decision: 'try',
  decided_at: '2026-09-19T10:01:00+00:00',
  undone_at: null,
  in_effect: true,
  trial: true,
}

describe('AdaptationCards', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('shows the why and four explicit choices; Try posts the decision with the session', async () => {
    useMode.setState({ sessionId: 's1' })
    const calls: Array<{ url: string; body: unknown }> = []
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string, init?: RequestInit) => {
        if (url.endsWith('/api/adaptations')) return jsonResponse({ proposals: [card] })
        if (url.endsWith('/decide')) {
          calls.push({ url, body: JSON.parse(String(init?.body)) })
          return jsonResponse({ entries: [entry] })
        }
        return jsonResponse({ entries: [] })
      }),
    )
    renderApp(<AdaptationCards />)
    expect(await screen.findByText(/Suggestion: Start new material/)).toBeInTheDocument()
    expect(screen.getByText(/2.0 hints per attempt/)).toBeInTheDocument()
    expect(screen.getAllByRole('button')).toHaveLength(4)
    fireEvent.click(screen.getByRole('button', { name: 'Try it this session' }))
    await waitFor(() => expect(calls).toHaveLength(1))
    expect(calls[0].url).toContain('/api/adaptations/a1/decide')
    expect(calls[0].body).toEqual({ decision: 'try', session_id: 's1' })
  })

  it('log lists decisions and offers undo only for changes in effect', async () => {
    const undone: string[] = []
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string) => {
        if (url.endsWith('/undo')) {
          undone.push(url)
          return jsonResponse({ entries: [{ ...entry, in_effect: false, undone_at: 'now' }] })
        }
        return jsonResponse({
          entries: [entry, { ...entry, id: 'a2', decision: 'no', in_effect: false, trial: false }],
        })
      }),
    )
    renderApp(<AdaptationLog />)
    expect(await screen.findByText(/decided: try \(one session\) · in effect/)).toBeInTheDocument()
    expect(screen.getByText(/decided: no/)).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: 'Undo' })).toHaveLength(1)
    fireEvent.click(screen.getByRole('button', { name: 'Undo' }))
    await waitFor(() => expect(undone).toHaveLength(1))
  })
})
