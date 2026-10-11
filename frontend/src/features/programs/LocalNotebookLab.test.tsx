import { act, fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { renderApp, jsonResponse } from '../../test/utils'
import { LocalNotebookLab } from './LocalNotebookLab'
afterEach(() => { vi.unstubAllGlobals(); vi.useRealTimers() })
it('offers explicit setup and opens only the prepared course', async () => {
  const fetcher = vi.fn(async (url: string, init?: RequestInit) => {
    if (url.endsWith('/status'))
      return jsonResponse({ status: 'idle', message: 'Ready to prepare', url: null, course_id: '' })
    const body = JSON.parse(init?.body as string)
    expect(body.course_id).toBe('test')
    expect(init?.headers).toMatchObject({ 'X-Notebook-Action': 'start' })
    return jsonResponse(
      body.install
        ? {
            status: 'ready',
            message: 'Ready',
            url: 'http://127.0.0.1:8890/lab/tree/test/task.ipynb?token=fixture',
            course_id: 'test',
          }
        : { status: 'needs_install', message: 'Install once', url: null, course_id: 'test' },
    )
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
    .mockResolvedValue(jsonResponse({ status: 'idle', message: 'Ready after retry', url: null, course_id: '' }))
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
