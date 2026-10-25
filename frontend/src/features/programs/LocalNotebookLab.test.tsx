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

it('checks requirements only on request and separates package gaps from possible exercises', async () => {
  const fetcher = vi.fn(async (url: string, init?: RequestInit) => {
    expect(init?.method ?? 'GET').toBe('GET')
    return jsonResponse(url.includes('/check?') ? { status: 'checked', message: 'Static check only.', code_cells: 4,
      imports: ['json', 'missing'], unavailable_imports: ['missing'], local_imports: [], possible_exercise_cells: [3], unparsed_cells: [4], install_cells: [2] }
      : { service_id: '11111111-1111-4111-8111-111111111111', status: 'idle', message: 'Ready to prepare', url: null, course_id: '' })
  })
  vi.stubGlobal('fetch', fetcher)
  renderApp(<LocalNotebookLab courseId="test" />)
  await screen.findByText('Ready to prepare')
  expect(fetcher).toHaveBeenCalledTimes(1)
  fireEvent.click(screen.getByText('Notebook requirements and exercise readiness'))
  fireEvent.click(screen.getByRole('button', { name: 'Check notebook requirements' }))
  await screen.findByText(/Imports not found in this environment: missing/)
  expect(screen.getByText(/Possible unfinished exercise cells: 3/)).toBeVisible()
  expect(screen.getByText(/Installation commands appear in cells 2/)).toBeVisible()
  expect(fetcher.mock.calls.every(([url]) => !url.endsWith('/start'))).toBe(true)
})

it('does not report platform-only standard modules as installed or ordinary package gaps', async () => {
  vi.stubGlobal('fetch', vi.fn(async (url: string) => jsonResponse(url.includes('/check?')
    ? { status: 'checked', message: 'Static check only.', imports: ['winreg'], unavailable_imports: ['winreg'], unavailable_standard_imports: ['winreg'] }
    : { service_id: '11111111-1111-4111-8111-111111111111', status: 'idle', message: 'Ready to prepare', course_id: '' })))
  renderApp(<LocalNotebookLab courseId="test" />)
  await screen.findByText('Ready to prepare')
  fireEvent.click(screen.getByText('Notebook requirements and exercise readiness'))
  fireEvent.click(screen.getByRole('button', { name: 'Check notebook requirements' }))
  await screen.findByText(/Standard-library modules unavailable in this Python build or platform: winreg/)
  expect(screen.queryByText(/Imports not found in this environment:/)).not.toBeInTheDocument()
  expect(screen.queryByText(/Imported modules were found/)).not.toBeInTheDocument()
})
