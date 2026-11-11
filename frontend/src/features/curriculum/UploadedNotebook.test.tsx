import { fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { jsonResponse, renderApp } from '../../test/utils'
import { UploadedNotebook } from './UploadedNotebook'

afterEach(() => { sessionStorage.clear(); vi.unstubAllGlobals() })

it('uses the saved upload identity and requires an explicit start', async () => {
  const service = '11111111-1111-4111-8111-111111111111'
  let status: Record<string, unknown> = { service_id: service, status: 'idle', message: 'Ready to prepare' }
  const fetcher = vi.fn(async (url: string, init?: RequestInit) => {
    if (url === '/api/notebooks/uploads/test') return jsonResponse({ available: true })
    if (url === '/api/notebooks/status') return jsonResponse(status)
    expect(url).toBe('/api/notebooks/uploads/test/start')
    expect(init?.method).toBe('POST')
    const command = JSON.parse(init?.body as string)
    expect(command).toMatchObject({ course_id: 'upload-test', install: false, service_id: service })
    status = { ...command, status: 'ready', url: '/api/notebooks/open/' + service + '/' + command.request_id, message: 'Ready' }
    return jsonResponse(status)
  })
  vi.stubGlobal('fetch', fetcher)
  renderApp(<UploadedNotebook documentId="test" />)
  fireEvent.click(await screen.findByText('Open uploaded notebook locally'))
  await screen.findByText('Ready to prepare')
  expect(fetcher.mock.calls.every(([, init]) => init?.method !== 'POST')).toBe(true)
  fireEvent.click(screen.getByRole('button', { name: 'Prepare and start notebook lab' }))
  const link = await screen.findByRole('link', { name: 'Open prepared notebook in Jupyter' })
  expect(link).toHaveAttribute('href', status.url)
})

it('retries a failed lookup and hides Jupyter for a non-notebook source', async () => {
  const fetcher = vi.fn().mockRejectedValueOnce(new Error('Offline')).mockResolvedValueOnce(jsonResponse({ available: false }))
  vi.stubGlobal('fetch', fetcher)
  renderApp(<UploadedNotebook documentId="plain" />)
  fireEvent.click(await screen.findByRole('button', { name: 'Retry notebook lookup' }))
  await waitFor(() => expect(screen.queryByRole('button', { name: 'Retry notebook lookup' })).toBeNull())
  expect(fetcher).toHaveBeenCalledTimes(2)
  expect(screen.queryByText('Open uploaded notebook locally')).toBeNull()
  expect(fetcher.mock.calls.every(([url]) => url === '/api/notebooks/uploads/plain')).toBe(true)
})
