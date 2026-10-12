import { act, fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { jsonResponse, renderApp } from '../../test/utils'
import { ReferenceCopy } from './ReferenceCopy'

afterEach(() => vi.unstubAllGlobals())

it('ignores a late download after stop and prevents accidental duplicate requests', async () => {
  let finish!: (response: Response) => void
  const fetcher = vi.fn(async (_path: string, init?: RequestInit) => {
    if (init?.method !== 'POST') return jsonResponse({ snapshot: null })
    return new Promise<Response>((resolve) => { finish = resolve })
  })
  vi.stubGlobal('fetch', fetcher)
  renderApp(<ReferenceCopy referenceId="numpy-basics" />)
  const save = screen.getByRole('button', { name: 'Save a local reading copy' })
  await waitFor(() => expect(save).toBeEnabled())
  expect(fetcher.mock.calls.filter((call) => call[1]?.method === 'POST')).toHaveLength(0)
  fireEvent.click(save)
  fireEvent.click(save)
  expect(fetcher.mock.calls.filter((call) => call[1]?.method === 'POST')).toHaveLength(1)
  fireEvent.click(screen.getByRole('button', { name: 'Stop waiting' }))
  await act(async () => {
    finish(jsonResponse({ snapshot_id: 'old', fetched_at: '2026-10-12', extracted_characters: 3, text_preview: 'old' }))
  })
  expect(screen.queryByText(/Local reading copy saved/)).not.toBeInTheDocument()
  expect(screen.queryByRole('button', { name: 'Add to local library' })).not.toBeInTheDocument()
  expect(screen.getByRole('status')).toHaveTextContent('Stopped waiting')
  expect(save).toBeEnabled()
})
