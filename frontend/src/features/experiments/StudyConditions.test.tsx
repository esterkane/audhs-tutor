import { fireEvent, screen } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { renderApp, jsonResponse } from '../../test/utils'
import { StudyConditions } from './StudyConditions'
afterEach(() => vi.unstubAllGlobals())
it('records only explicit self-reports without starting sound and keeps observations separate', async () => {
  const writes: unknown[] = []
  const audio = vi.fn(() => {
    throw new Error('Audio must not start')
  })
  vi.stubGlobal('AudioContext', audio)
  vi.stubGlobal(
    'fetch',
    vi.fn(async (_url: string, init?: RequestInit) => {
      if (init?.method === 'POST') {
        writes.push(JSON.parse(String(init.body)))
        return jsonResponse({
          id: 'event',
          node_id: 'lesson',
          conditions: { noise: 'white', presence: 'alone', movement: 'none', timer: 'elapsed' },
        })
      }
      return jsonResponse({ groups: [], reading: 'observations' })
    }),
  )
  renderApp(<StudyConditions sessionId="session" />)
  fireEvent.click(screen.getByText('Study conditions and later recall (optional)'))
  await screen.findByText('No qualifying later recall yet. Nothing is ranked or recommended.')
  fireEvent.change(screen.getByRole('combobox', { name: 'Sound condition', exact: true }), {
    target: { value: 'white' },
  })
  expect(writes).toEqual([])
  fireEvent.click(screen.getByRole('button', { name: 'Record conditions for this lesson' }))
  await screen.findByText('Conditions recorded as your self-report. No benefit has been inferred.')
  expect(writes).toEqual([
    {
      session_id: 'session',
      conditions: { noise: 'white', presence: 'alone', movement: 'none', timer: 'elapsed' },
    },
  ])
  expect(audio).not.toHaveBeenCalled()
})
