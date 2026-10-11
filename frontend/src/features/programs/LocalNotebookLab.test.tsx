import { act, fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { renderApp, jsonResponse } from '../../test/utils'
import { LocalNotebookLab } from './LocalNotebookLab'
afterEach(() => { sessionStorage.clear(); vi.unstubAllGlobals(); vi.useRealTimers() })
it('offers explicit setup and opens only the prepared course', async () => {
  let setup: Record<string, unknown> = { service_id: '11111111-1111-4111-8111-111111111111', status: 'idle', message: 'Ready to prepare', url: null, course_id: '' }
  const fetcher = vi.fn(async (url: string, init?: RequestInit) => {
    if (url.endsWith('/status'))
      return jsonResponse(setup)
    const body = JSON.parse(init?.body as string)
    expect(body.course_id).toBe('test')
    expect(init?.headers).toMatchObject({ 'X-Notebook-Action': 'start' })
    setup = body.install
        ? {
            request_id: body.request_id, service_id: body.service_id, status: 'ready',
            message: 'Ready',
            url: 'http://127.0.0.1:8890/lab/tree/test/task.ipynb?token=fixture',
            course_id: 'test',
          }
        : { request_id: body.request_id, service_id: body.service_id, status: 'needs_install', message: 'Install once', url: null, course_id: 'test' }
    return jsonResponse(setup)
  })
  vi.stubGlobal('fetch', fetcher)
  renderApp(<LocalNotebookLab courseId="test" />)
  await screen.findByText('Ready to prepare')
  expect(fetcher).toHaveBeenCalledTimes(1)
  fireEvent.click(screen.getByRole('button', { name: 'Prepare and start notebook lab' }))
  fireEvent.click(await screen.findByRole('button', { name: 'Install notebook tools and start lab' }))
  await waitFor(() =>
    expect(screen.getByRole('link', { name: 'Open prepared notebook in Jupyter' })).toHaveAttribute(
      'href',
      expect.stringContaining('/test/task.ipynb'),
    ),
  )
})

it('bounds a stalled status read and retries without starting or installing anything', async () => {
  vi.useFakeTimers()
  const fetcher = vi.fn().mockImplementationOnce(() => new Promise(() => {}))
    .mockResolvedValue(jsonResponse({ service_id: '11111111-1111-4111-8111-111111111111', status: 'idle', message: 'Ready after retry', url: null, course_id: '' }))
  vi.stubGlobal('fetch', fetcher)
  renderApp(<LocalNotebookLab courseId="test" />)
  await act(async () => { await vi.advanceTimersByTimeAsync(15001) })
  await act(async () => { await vi.advanceTimersByTimeAsync(1) })
  const retry = screen.getByRole('button', { name: 'Retry status' })
  fireEvent.click(retry)
  await act(async () => { await vi.advanceTimersByTimeAsync(1) })
  expect(screen.getByText('Ready after retry')).toBeInTheDocument()
  expect(fetcher.mock.calls.every(([url]) => url.endsWith('/status'))).toBe(true)
})

it('stops background polling after a failed setup status read', async () => {
  vi.useFakeTimers()
  const fetcher = vi.fn().mockResolvedValueOnce(jsonResponse({ status: 'starting', message: 'Starting', url: null, course_id: 'test' }))
    .mockRejectedValue(new Error('Offline'))
  vi.stubGlobal('fetch', fetcher)
  renderApp(<LocalNotebookLab courseId="test" />)
  await act(async () => { await vi.advanceTimersByTimeAsync(1002) })
  await act(async () => { await vi.advanceTimersByTimeAsync(1) })
  expect(screen.getByRole('button', { name: 'Retry status' })).toBeInTheDocument()
  const calls = fetcher.mock.calls.length
  await act(async () => { await vi.advanceTimersByTimeAsync(5000) })
  expect(fetcher).toHaveBeenCalledTimes(calls)
})

it('keeps another active job visible when recovering an older course receipt', async () => {
  const pending = { request_id: '22222222-2222-4222-8222-222222222222', service_id: '11111111-1111-4111-8111-111111111111', course_id: 'test', install: false }
  sessionStorage.setItem('audhs.notebook-command.v1:test', JSON.stringify(pending))
  const fetcher = vi.fn(async (url: string) => jsonResponse(url.includes('/requests/')
    ? { ...pending, status: 'ready', message: 'Earlier setup ready', url: 'http://127.0.0.1:8890/lab?token=fixture' }
    : { ...pending, request_id: '33333333-3333-4333-8333-333333333333', course_id: 'other', status: 'installing', message: 'Installing other notebook', url: null }))
  vi.stubGlobal('fetch', fetcher)
  renderApp(<LocalNotebookLab courseId="test" />)
  await screen.findByText(/Installing other notebook/)
  fireEvent.click(screen.getByRole('button', { name: 'Check setup status' }))
  await screen.findByRole('link', { name: 'Open prepared notebook in Jupyter' })
  expect(screen.getByText(/Installing other notebook/)).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Prepare and start notebook lab' })).toBeDisabled()
  const reads = fetcher.mock.calls.filter(([url]) => url.endsWith('/status')).length
  await waitFor(() => expect(fetcher.mock.calls.filter(([url]) => url.endsWith('/status')).length).toBeGreaterThan(reads), { timeout: 2000 })
})
