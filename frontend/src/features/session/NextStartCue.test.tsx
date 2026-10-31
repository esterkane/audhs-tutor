import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { jsonResponse, renderApp } from '../../test/utils'
import { NextStartCue } from './NextStartCue'
afterEach(() => vi.unstubAllGlobals())
it('saves only an explicit cue and displays it from authoritative preferences', async () => {
  let cue = ''
  const writes: unknown[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (_url: string, init?: RequestInit) => {
      if (init?.body) {
        const body = JSON.parse(String(init.body))
        writes.push(body)
        cue = body.value
      }
      return jsonResponse({ values: { 'session.next_start_cue': cue }, specs: [] })
    }),
  )
  renderApp(
    <>
      <NextStartCue editor />
      <NextStartCue />
    </>,
  )
  const input = screen.getByLabelText('If-then starting cue (optional)')
  fireEvent.change(input, { target: { value: 'After tea, recall one saved question.' } })
  await waitFor(() => expect(screen.getByRole('button', { name: 'Save next-start cue' })).toBeEnabled())
  expect(writes).toEqual([])
  fireEvent.click(screen.getByRole('button', { name: 'Save next-start cue' }))
  await screen.findByText('Next-start cue saved for Home.')
  expect(
    within(screen.getByRole('complementary', { name: 'Next-start cue' })).getByText(
      'After tea, recall one saved question.',
    ),
  ).toBeVisible()
  expect(writes).toEqual([{ key: 'session.next_start_cue', value: 'After tea, recall one saved question.' }])
  fireEvent.change(input, { target: { value: '' } })
  fireEvent.click(screen.getByRole('button', { name: 'Clear next-start cue' }))
  await screen.findByText('Next-start cue cleared.')
  expect(screen.queryByText('Your next-start cue')).not.toBeInTheDocument()
})
