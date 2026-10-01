import { fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { axe } from 'vitest-axe'
import { renderApp, jsonResponse } from '../test/utils'
import { Playground } from './Playground'
import { PLAIN_EDITOR_KEY } from '../features/code/editorPreference'
import type { Runner } from '../features/code/runner'

const result = { stdout: 'hello', error: null, truncated: false, results: [], timedOut: false, ms: 1 }
const runner = (): Runner => ({ load: async () => {}, run: async () => result, dispose: vi.fn() })
beforeEach(() => {
  localStorage.clear()
  localStorage.setItem(PLAIN_EDITOR_KEY, '1')
})
afterEach(() => vi.unstubAllGlobals())

it('keeps independent drafts, marks stale output and sends explicit bounded tutor context', async () => {
  const requests: Array<Record<string, unknown>> = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, init?: RequestInit) => {
      if (url.endsWith('/api/sessions/current')) return jsonResponse({ id: 's1' })
      if (url.endsWith('/api/playground/tutor')) {
        requests.push(JSON.parse(String(init?.body)))
        return jsonResponse({
          text: 'Inspect the stripped string.',
          model: 'fake',
          route: 'primary',
          source_note: 'No course sources.',
          turn_id: 't1',
        })
      }
      return jsonResponse({})
    }),
  )
  const { container, unmount } = renderApp(<Playground runnerFactory={runner} />)
  const code = screen.getByLabelText(/Python code/)
  fireEvent.change(code, { target: { value: 'print("hello")' } })
  fireEvent.click(screen.getByRole('button', { name: 'Run code' }))
  expect(await screen.findByText('hello')).toBeVisible()
  fireEvent.change(code, { target: { value: 'print("changed")' } })
  expect(screen.getByText(/output is from earlier code/)).toBeVisible()
  fireEvent.click(screen.getByRole('button', { name: 'One hint' }))
  expect(await screen.findByText('Inspect the stripped string.')).toBeVisible()
  expect(requests[0]).toMatchObject({
    code: 'print("changed")',
    output_stale: true,
    intent: 'hint',
    session_id: 's1',
  })
  expect(code).toHaveValue('print("changed")')
  fireEvent.change(screen.getByLabelText('Workspace'), { target: { value: 'complete' } })
  expect((screen.getByLabelText(/Python code/) as HTMLTextAreaElement).value).toContain('def clean')
  fireEvent.change(screen.getByLabelText('Workspace'), { target: { value: 'scratch' } })
  expect(screen.getByLabelText(/Python code/)).toHaveValue('print("changed")')
  expect(await axe(container)).toHaveNoViolations()
  unmount()
  renderApp(<Playground runnerFactory={runner} />)
  expect(screen.getByLabelText(/Python code/)).toHaveValue('print("changed")')
})

it('stops an in-flight run and keeps a failed tutor question for retry', async () => {
  const dispose = vi.fn()
  const factory = (): Runner => ({ load: async () => {}, run: () => new Promise(() => {}), dispose })
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      if (url.endsWith('/api/sessions/current')) return jsonResponse({ id: 's1' })
      return jsonResponse({ error: { code: 'unavailable', message: 'Tutor unavailable' } }, 503)
    }),
  )
  renderApp(<Playground runnerFactory={factory} />)
  fireEvent.click(screen.getByRole('button', { name: 'Run code' }))
  fireEvent.click(screen.getByRole('button', { name: 'Stop run' }))
  expect(await screen.findByText('Run stopped. Your code is kept.')).toBeVisible()
  expect(dispose).toHaveBeenCalled()
  fireEvent.change(screen.getByLabelText('Ask about your code'), { target: { value: 'Why does this fail?' } })
  await waitFor(() => expect(screen.getByRole('button', { name: 'Send question' })).toBeEnabled())
  fireEvent.click(screen.getByRole('button', { name: 'Send question' }))
  expect(await screen.findByText('Tutor unavailable')).toBeVisible()
  expect(screen.getByLabelText('Ask about your code')).toHaveValue('Why does this fail?')
})

it('preserves a new question and identifies replies to code edited while waiting', async () => {
  let reply!: (value: Response) => void
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      if (url.endsWith('/api/sessions/current')) return jsonResponse({ id: 's1' })
      return new Promise<Response>((resolve) => {
        reply = resolve
      })
    }),
  )
  renderApp(<Playground runnerFactory={runner} />)
  const question = screen.getByLabelText('Ask about your code')
  fireEvent.change(question, { target: { value: 'First question' } })
  await waitFor(() => expect(screen.getByRole('button', { name: 'Send question' })).toBeEnabled())
  fireEvent.click(screen.getByRole('button', { name: 'Send question' }))
  fireEvent.change(question, { target: { value: 'My next question' } })
  fireEvent.change(screen.getByLabelText(/Python code/), { target: { value: 'print(42)' } })
  reply(
    jsonResponse({ text: 'A response.', model: 'fake', route: 'primary', source_note: 'General guidance.' }),
  )
  expect(await screen.findByText('This answer refers to earlier code.')).toBeVisible()
  expect(question).toHaveValue('My next question')
})

it('shares a pending session start across workspace switches', async () => {
  let started!: (value: Response) => void
  let starts = 0
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      if (url.endsWith('/api/sessions/current')) return jsonResponse(null)
      if (url.endsWith('/api/sessions')) {
        starts++
        return new Promise<Response>((resolve) => {
          started = resolve
        })
      }
      return jsonResponse({})
    }),
  )
  renderApp(<Playground runnerFactory={runner} />)
  await waitFor(() => expect(screen.getByRole('button', { name: 'Start session for tutor' })).toBeEnabled())
  fireEvent.click(screen.getByRole('button', { name: 'Start session for tutor' }))
  fireEvent.change(screen.getByLabelText('Workspace'), { target: { value: 'worked' } })
  expect(screen.getByRole('button', { name: 'Starting…' })).toBeDisabled()
  await waitFor(() => expect(starts).toBe(1))
  started(jsonResponse({ id: 's2', state: {} }))
  expect(await screen.findByText(/Tutor activity uses your current session/)).toBeVisible()
  expect(starts).toBe(1)
})
