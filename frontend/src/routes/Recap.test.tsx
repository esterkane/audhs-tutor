import { act, fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { Route, Routes } from 'react-router-dom'
import { jsonResponse, renderApp } from '../test/utils'
import { useMode } from '../stores/mode'
import { Recap } from './Recap'
import { recapDraftKey } from '../features/session/useRecapDraft'

afterEach(() => { vi.unstubAllGlobals(); sessionStorage.clear(); useMode.getState().reset() })

for (const save of [true, false]) it(`shares one finish operation, saving optional recap: ${save}`, async () => {
  useMode.setState({ sessionId: 's1' })
  const bodies: unknown[] = []
  let release!: (value: Response) => void
  const response = new Promise<Response>(resolve => { release = resolve })
  vi.stubGlobal('fetch', vi.fn((url: string, init?: RequestInit) => {
    if (url.endsWith('/end')) { bodies.push(JSON.parse(String(init?.body))); return response }
    return Promise.resolve(jsonResponse({ values: {}, specs: [] }))
  }))
  renderApp(<Routes><Route path="/recap" element={<Recap />} /><Route path="/" element={<p>Home destination</p>} /></Routes>, { route: '/recap' })
  fireEvent.change(screen.getByLabelText('One line for next time (optional)'), { target: { value: 'Keep notes' } })
  const first = screen.getByRole('button', { name: save ? 'Save and finish session' : 'End session' })
  fireEvent.click(first)
  fireEvent.click(first)
  await waitFor(() => expect(bodies).toHaveLength(1))
  expect(screen.getByRole('button', { name: 'Change topic' })).toBeDisabled()
  expect(screen.getByRole('button', { name: 'End session' })).toBeDisabled()
  expect(screen.getByLabelText('One line for next time (optional)')).toBeDisabled()
  expect(screen.getByRole('button', { name: 'Return Home' })).toBeEnabled()
  expect(screen.getByRole('button', { name: save ? 'Saving…' : 'Ending session…' })).toBeDisabled()
  expect(bodies).toEqual([save ? { notes: 'Keep notes' } : {}])
  await act(async () => { release(jsonResponse({ id: 's1', next_skill: null, due_reviews: 0 })); await response })
  expect(await screen.findByText(save ? 'Session saved' : 'Home destination')).toBeVisible()
  expect(useMode.getState().sessionId).toBeNull()
  if (save) expect(sessionStorage.getItem(recapDraftKey('s1'))).toBeNull()
  else expect(sessionStorage.getItem(recapDraftKey('s1'))).toContain('Keep notes')
})

it('keeps recap notes and shows one error when saving fails', async () => {
  useMode.setState({ sessionId: 's1' })
  vi.stubGlobal('fetch', vi.fn(async (url: string) => url.endsWith('/end')
    ? jsonResponse({ error: { code: 'unavailable', message: 'Save unavailable' } }, 503)
    : jsonResponse({ values: {}, specs: [] })))
  renderApp(<Recap />, { route: '/recap' })
  fireEvent.change(screen.getByLabelText('One line for next time (optional)'), { target: { value: 'Keep notes' } })
  fireEvent.click(screen.getByRole('button', { name: 'Save and finish session' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('Save unavailable')
  expect(screen.getByLabelText('One line for next time (optional)')).toHaveValue('Keep notes')
  expect(sessionStorage.getItem(recapDraftKey('s1'))).toContain('Keep notes')
  expect(useMode.getState().sessionId).toBe('s1')
})
