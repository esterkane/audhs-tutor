import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { render, act, fireEvent, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { axe } from 'vitest-axe'
import { jsonResponse, renderApp } from '../../test/utils'
import { CodeExercise } from './CodeExercise'
import { PLAIN_EDITOR_KEY } from './editorPreference'
import { assessmentRecoveryKey } from '../assess/useAssessmentSubmission'
import type { Runner, RunResult } from './runner'

const exercise = {
  content_version: 'code-version',
  check_content_version: 'check-version',
  assessment_id: 'a1',
  skill_id: 'k1',
  exercise_id: 'attn-scaled-softmax',
  title: 'Scaled dot-product attention in numpy',
  prompt: 'Implement softmax and scaled_attention.',
  starter_code: 'import numpy as np\n\ndef softmax(x):\n    ...\n',
  success_criteria: ['softmax rows sum to 1', 'scores are scaled', 'output matches a reference'],
  checks: [
    { name: 'softmax_rows', criterion: 'softmax rows sum to 1', code: 'assert 1' },
    { name: 'scaling', criterion: 'scores are scaled', code: 'assert 1' },
    { name: 'shape_and_reference', criterion: 'output matches a reference', code: 'assert 1' },
  ],
  packages: ['numpy'],
  timeout_s: 10,
  max_output_chars: 20000,
  sources: [{ chunk_id: 'c1', citation: '[Attention › Scaled]' }],
  runtime: 'pyodide-worker',
  hints_available: 3,
  attempts: 0,
  check_assessment_id: 'q1',
  check_question: 'Check question: what happens without the scaling?',
  policy: {
    where: 'your browser',
    network: 'none',
    filesystem: 'in-memory',
    runtime_download: 'served by this app from its own origin',
  },
}
const graded = {
  attempt_id: 'x',
  assessment_id: 'a1',
  skill_id: 'k1',
  kind: 'code',
  dimension: 'application',
  correct: true,
  score: 1,
  criterion_results: exercise.success_criteria.map((c) => ({
    criterion: c,
    passed: true,
    evidence: 'passed',
  })),
  misconception: null,
  confidence: 1,
  grader_level: 'deterministic:client-pyodide',
  feedback: 'All 3 checks passed.',
  next_step: 'Check question: what happens without the scaling?',
  confidence_pre: 4,
  calibration: 'calibrated',
  review: {},
  mastery: 0.4,
}

function fakeRunner(script: (code: string) => RunResult | Promise<RunResult>, loadError?: string): Runner {
  return {
    load: async () => {
      if (loadError) throw new Error(loadError)
    },
    run: async (code) => script(code),
    dispose: () => {},
  }
}
const ok: RunResult = {
  stdout: 'hello\n',
  truncated: false,
  error: null,
  results: exercise.checks.map((c) => ({ name: c.name, passed: true, detail: 'passed' })),
  timedOut: false,
  ms: 12,
}

function stub(posts: { url: string; body: unknown }[]) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, init?: RequestInit) => {
      if (init?.method === 'POST') posts.push({ url, body: JSON.parse(String(init.body)) })
      if (url.endsWith('/api/exercises/for-skill/k1')) return jsonResponse(exercise)
      if (url.endsWith('/hint')) {
        const level = (posts[posts.length - 1].body as { level: number }).level
        return jsonResponse({ level, text: `hint ${level}`, hints_available: 3 })
      }
      if (url.endsWith('/solution'))
        return jsonResponse({
          solution: 'def softmax(x): pass',
          check_question: 'Check question: why scale?',
        })
      if (url.endsWith('/api/assess/attempt')) return jsonResponse(graded)
      return jsonResponse({})
    }),
  )
}

describe('CodeExercise', () => {
  // the interaction tests drive the plain <textarea> (jsdom cannot type into CodeMirror);
  // the CodeMirror test below covers mounting, naming, value sync and the switch
  beforeEach(() => localStorage.setItem(PLAIN_EDITOR_KEY, '1'))
  afterEach(() => {
    vi.unstubAllGlobals()
    localStorage.clear()
    sessionStorage.clear()
  })

  it('mounts CodeMirror by default with an accessible name, syncs Reset into it and can switch to the plain editor', async () => {
    localStorage.removeItem(PLAIN_EDITOR_KEY)
    stub([])
    const { container } = renderApp(
      <CodeExercise sessionId="s1" skillId="k1" runner={fakeRunner(() => ok)} />,
    )
    const mirror = await screen.findByRole('textbox', { name: /Your code \(Python; Tab indents/ })
    expect(mirror).toHaveAttribute('contenteditable', 'true')
    expect(screen.getByTestId('code-mirror').textContent).toContain('def softmax(x):')
    expect(screen.queryByRole('textbox', { name: /Tab inserts two spaces/ })).not.toBeInTheDocument()
    // the switch keeps the code and is remembered per viewer
    fireEvent.click(screen.getByRole('button', { name: 'Switch to the plain editor' }))
    const plain = screen.getByLabelText(/Tab inserts two spaces/) as HTMLTextAreaElement
    expect(plain.value).toBe(exercise.starter_code)
    expect(localStorage.getItem(PLAIN_EDITOR_KEY)).toBe('1')
    fireEvent.change(plain, { target: { value: 'x = 1' } })
    fireEvent.click(screen.getByRole('button', { name: 'Switch to the code editor' }))
    expect(screen.getByTestId('code-mirror').textContent).toContain('x = 1')
    expect(localStorage.getItem(PLAIN_EDITOR_KEY)).toBeNull()
    // an external value (Reset) flows into the mounted editor
    fireEvent.click(screen.getByRole('button', { name: 'Reset to starter code' }))
    expect(screen.getByTestId('code-mirror').textContent).toContain('def softmax(x):')
    expect(screen.getByTestId('code-mirror').textContent).not.toContain('x = 1')
    expect(await axe(container)).toHaveNoViolations()
  })

  it('runs only on click, keeps run and submit apart, gives hints one at a time and the solution only on request', async () => {
    const posts: { url: string; body: unknown }[] = []
    stub(posts)
    const runs: string[] = []
    const runner = fakeRunner((code) => {
      runs.push(code)
      return ok
    })
    const { container } = renderApp(<CodeExercise sessionId="s1" skillId="k1" runner={runner} />)
    expect(await screen.findByText(/Code exercise: Scaled dot-product/)).toBeInTheDocument()
    expect(runs).toHaveLength(0) // nothing executes on load
    expect(screen.queryByRole('button', { name: 'Submit this attempt' })).not.toBeInTheDocument() // no run yet
    expect(screen.getByText('Sources: [Attention › Scaled]')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Run' }))
    const checks = await screen.findByRole('list', { name: 'Checks' })
    expect(within(checks).getAllByText(/passed:/)).toHaveLength(3)
    expect(within(checks).getByText(/softmax rows sum to 1/)).toBeInTheDocument()
    expect(screen.getByText(/Running is not an attempt/)).toBeInTheDocument()
    expect(posts).toHaveLength(0) // Run posted nothing
    const submit = screen.getByRole('button', { name: 'Submit this attempt' })
    expect(submit).toBeEnabled() // confidence is optional
    fireEvent.click(screen.getByText('Confidence (optional)'))
    fireEvent.click(screen.getByRole('button', { name: '4' }))
    expect(submit).toBeEnabled()
    // editing after the run makes the results stale: run again first
    fireEvent.change(screen.getByLabelText(/Your code/), { target: { value: 'x = 1' } })
    expect(screen.getByText(/run it again first/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Submit this attempt' })).toBeDisabled()
    fireEvent.click(screen.getByRole('button', { name: 'Run' }))
    await waitFor(() => expect(runs).toHaveLength(2))
    expect(await axe(container)).toHaveNoViolations()
    fireEvent.click(screen.getByRole('button', { name: 'Submit this attempt' }))
    expect(await screen.findByText('All 3 checks passed.')).toBeInTheDocument()
    const attempt = posts.find((p) => p.url.endsWith('/api/assess/attempt'))!.body as Record<string, unknown>
    expect(attempt).toMatchObject({
      assessment_id: 'a1',
      content_version: 'code-version',
      confidence_pre: 4,
      hint_count: 0,
    })
    expect(JSON.parse(attempt.answer as string)).toMatchObject({
      code: 'x = 1',
      results: ok.results,
      solution_shown: false,
    })
    // a full pass ends with the check question, answered and graded as explain-back
    expect(screen.getByText(/A review of this node is due in at least two days/)).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('Check question: what happens without the scaling?'), {
      target: { value: 'the softmax saturates' },
    })
    fireEvent.click(screen.getAllByRole('button', { name: '3' }).at(-1)!)
    fireEvent.click(screen.getByRole('button', { name: 'Check my answer' }))
    await waitFor(() => expect(posts.filter((p) => p.url.endsWith('/api/assess/attempt'))).toHaveLength(2))
    expect(posts[posts.length - 1].body).toMatchObject({
      assessment_id: 'q1',
      content_version: 'check-version',
    })
    // hints: one per click; the full solution only appears after the ladder is used up
    expect(screen.queryByRole('button', { name: 'Show the full solution' })).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Hint 1 of 3' }))
    expect(await screen.findByText('hint 1')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Hint 2 of 3' }))
    expect(await screen.findByText('hint 2')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Hint 3 of 3' }))
    expect(await screen.findByText('hint 3')).toBeInTheDocument()
    // the full solution needs a second explicit click
    fireEvent.click(await screen.findByRole('button', { name: 'Show the full solution' }))
    expect(screen.queryByText('def softmax(x): pass')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Yes, show it' }))
    expect(await screen.findByText('def softmax(x): pass')).toBeInTheDocument()
    expect(posts.filter((p) => p.url.endsWith('/solution'))).toHaveLength(1)
  })

  it('shows errors, timeouts and truncated output literally, resets, and restores the draft after a reload', async () => {
    stub([])
    let mode: 'error' | 'timeout' | 'big' = 'error'
    const runner = fakeRunner(() =>
      mode === 'error'
        ? { ...ok, error: 'SyntaxError: invalid syntax (line 3)', results: [] }
        : mode === 'timeout'
          ? {
              ...ok,
              error: 'Stopped after 10 s — the code did not finish (infinite loop?).',
              results: [],
              timedOut: true,
            }
          : { ...ok, stdout: 'x'.repeat(50), truncated: true },
    )
    const first = renderApp(<CodeExercise sessionId="s1" skillId="k1" runner={runner} />)
    const editor = (await first.findByLabelText(/Your code/)) as HTMLTextAreaElement
    fireEvent.change(editor, { target: { value: 'while True: pass' } })
    fireEvent.click(screen.getByRole('button', { name: 'Run' }))
    expect(await screen.findByText(/SyntaxError: invalid syntax/)).toBeInTheDocument()
    mode = 'timeout'
    fireEvent.click(screen.getByRole('button', { name: 'Run' }))
    expect(await screen.findByText(/did not finish \(infinite loop\?\)/)).toBeInTheDocument()
    mode = 'big'
    fireEvent.click(screen.getByRole('button', { name: 'Run' }))
    expect(await screen.findByText(/output cut at the limit/)).toBeInTheDocument()
    // the draft survives a reload (per-viewer convenience)
    first.unmount()
    const second = renderApp(<CodeExercise sessionId="s1" skillId="k1" runner={runner} />)
    expect(((await second.findByLabelText(/Your code/)) as HTMLTextAreaElement).value).toBe(
      'while True: pass',
    )
    fireEvent.click(screen.getByRole('button', { name: 'Reset to starter code' }))
    expect((screen.getByLabelText(/Your code/) as HTMLTextAreaElement).value).toBe(exercise.starter_code)
  })

  it('disposes an old run on refresh and ignores its late result during a new run', async () => {
    const sessionId = 'refresh-run-session'
    sessionStorage.setItem(
      assessmentRecoveryKey(sessionId),
      JSON.stringify({
        version: 1,
        id: '42b914ea-2562-4e73-821e-f25431583c87',
        endpoint: '/api/assess/attempt',
        rejectedContent: true,
        body: { session_id: sessionId, assessment_id: 'a1', content_version: 'old', answer: 'saved work' },
        question: exercise.prompt,
      }),
    )
    const updated = {
      ...exercise,
      content_version: 'updated-version',
      prompt: 'Updated exercise prompt.',
      checks: [{ name: 'new_check', criterion: 'new rule', code: 'assert 2' }],
    }
    let reads = 0
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => jsonResponse(++reads === 1 ? exercise : updated)),
    )
    const resolutions: Array<(result: RunResult) => void> = []
    const runMock = vi.fn<Runner['run']>(() => new Promise<RunResult>((resolve) => resolutions.push(resolve)))
    const runner: Runner = { load: vi.fn(async () => {}), run: runMock, dispose: vi.fn() }
    const { unmount } = renderApp(<CodeExercise sessionId={sessionId} skillId="k1" runner={runner} />)
    fireEvent.click(await screen.findByRole('button', { name: 'Run' }))
    await waitFor(() => expect(runMock).toHaveBeenCalledTimes(1))
    fireEvent.click(screen.getByRole('button', { name: 'Review updated question — keep my answer' }))
    expect(await screen.findByText(updated.prompt)).toBeInTheDocument()
    expect(runner.dispose).toHaveBeenCalledTimes(1)
    expect(screen.getByLabelText(/Your code/)).toHaveValue(exercise.starter_code)
    fireEvent.click(screen.getByRole('button', { name: 'Run' }))
    await waitFor(() => expect(runMock).toHaveBeenCalledTimes(2))
    expect(runner.load).toHaveBeenCalledTimes(2)
    expect(runMock.mock.calls[1]).toEqual([exercise.starter_code, updated.checks, expect.any(Object)])
    await act(async () => resolutions[0]({ ...ok, stdout: 'OBSOLETE RESULT', timedOut: true }))
    expect(screen.queryByText('OBSOLETE RESULT')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Submit this attempt' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Running/ })).toBeDisabled()
    await act(async () =>
      resolutions[1]({
        ...ok,
        stdout: 'CURRENT RESULT',
        results: [{ name: 'new_check', passed: true, detail: 'passed' }],
      }),
    )
    expect(await screen.findByText('CURRENT RESULT')).toBeInTheDocument()
    expect(screen.queryByText('OBSOLETE RESULT')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Submit this attempt' })).toBeEnabled()
    unmount()
    sessionStorage.removeItem(assessmentRecoveryKey(sessionId))
  })

  it('explains a runtime that cannot load, accessibly, and still shows the exercise', async () => {
    stub([])
    renderApp(
      <CodeExercise sessionId="s1" skillId="k1" runner={fakeRunner(() => ok, 'network unreachable')} />,
    )
    fireEvent.click(await screen.findByRole('button', { name: 'Run' }))
    expect(await screen.findByRole('alert')).toHaveTextContent(/could not be loaded \(network unreachable\)/)
    expect(screen.getByLabelText(/Your code/)).toBeInTheDocument()
  })

it('explains an unavailable exercise and retries without losing saved code', async () => {
  localStorage.setItem('code-draft:a1', 'print("saved work")')
  let fail = true
  vi.stubGlobal('fetch', vi.fn(async () => fail
    ? jsonResponse({ error: { code: 'assessment_unavailable', message: 'This question is excluded from practice.' } }, 409)
    : jsonResponse(exercise)))
  renderApp(<CodeExercise sessionId="s1" skillId="k1" runner={fakeRunner(() => ok)} />)
  await screen.findByText('This question is excluded from practice.')
  expect(screen.getByRole('link', { name: 'Manage excluded questions' })).toHaveAttribute('href', '/preferences#excluded-questions')
  expect(localStorage.getItem('code-draft:a1')).toBe('print("saved work")')
  fail = false
  fireEvent.click(screen.getByRole('button', { name: 'Retry exercise' }))
  await screen.findByText('Code exercise: Scaled dot-product attention in numpy')
  expect(localStorage.getItem('code-draft:a1')).toBe('print("saved work")')
})

  it('retains the cached editor and retry focus after another failed read', async () => {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    qc.setQueryData(['exercise', 'k1'], exercise)
    const fetcher = vi.fn(async () => jsonResponse({ error: { message: 'Backend unavailable' } }, 503))
    vi.stubGlobal('fetch', fetcher)
    render(<QueryClientProvider client={qc}><MemoryRouter>
      <CodeExercise sessionId="s1" skillId="k1" runner={fakeRunner(() => ok)} />
    </MemoryRouter></QueryClientProvider>)
    await screen.findByText('Could not refresh the exercise. Your code is kept.')
    const editor = screen.getByRole('textbox', { name: /Your code/ })
    fireEvent.change(editor, { target: { value: 'print("retained")' } })
    const retry = screen.getByRole('button', { name: 'Retry exercise' })
    retry.focus()
    fireEvent.click(retry)
    await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(2))
    await waitFor(() => expect(retry).toBeEnabled())
    expect(retry).toHaveFocus()
    expect(editor).toHaveValue('print("retained")')
    expect(screen.getByRole('textbox', { name: /Your code/ })).toBe(editor)
    qc.clear()
  })

  it('excludes and restores code practice without erasing code or treating old checks as fresh', async () => {
    let state = 'active'
    let revision = 0
    let failRefresh = false
    const posts: string[] = []
    vi.stubGlobal('fetch', vi.fn(async (url: string, init?: RequestInit) => {
      if (url === '/api/questions/a1/practice') {
        if (init?.method === 'POST') {
          state = JSON.parse(String(init.body)).action === 'suspend' ? 'suspended' : 'active'
          revision++
        }
        const status = { assessment_id: 'a1', state, revision, reason: null }
        return jsonResponse(init?.method === 'POST' ? status : { status, affected_reviews: 1 })
      }
      if (url.endsWith('/for-skill/k1')) return failRefresh
        ? jsonResponse({ error: { message: 'offline' } }, 503)
        : jsonResponse({ ...exercise, content_version: `v${revision}` })
      if (init?.method === 'POST') posts.push(url)
      if (url.endsWith('/hint')) return jsonResponse({ text: 'Remember the scale', level: 1 })
      return jsonResponse(null)
    }))
    renderApp(<CodeExercise sessionId="s1" skillId="k1" runner={fakeRunner(() => ok)} />)
    const editor = await screen.findByRole('textbox', { name: /Your code/ })
    fireEvent.change(editor, { target: { value: 'print("keep me")' } })
    fireEvent.click(screen.getByRole('button', { name: 'Run' }))
    await screen.findByRole('button', { name: 'Submit this attempt' })
    fireEvent.click(screen.getByRole('button', { name: 'Hint 1 of 3' }))
    await screen.findByText('Remember the scale')
    fireEvent.click(screen.getByRole('button', { name: 'Question practice options' }))
    fireEvent.click(await screen.findByRole('button', { name: 'Exclude this question' }))
    await screen.findByText('This exercise is excluded. You can keep editing and running your code. Restore it before submitting another code attempt.')
    expect(screen.getByRole('button', { name: 'Submit this attempt' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Hint 2 of 3' })).toBeDisabled()
    expect(editor).toHaveValue('print("keep me")')
    fireEvent.click(screen.getByRole('button', { name: 'Run' }))
    await waitFor(() => expect(screen.getByRole('button', { name: 'Run' })).toBeEnabled())
    fireEvent.click(screen.getByRole('button', { name: 'Restore this question' }))
    failRefresh = true
    fireEvent.click(await screen.findByRole('button', { name: 'Refresh restored exercise' }))
    await screen.findByText('Could not refresh the exercise. Your code and previous results are kept. Try again.')
    failRefresh = false
    fireEvent.click(screen.getByRole('button', { name: 'Refresh restored exercise' }))
    await waitFor(() => expect(screen.queryByRole('button', { name: 'Refresh restored exercise' })).not.toBeInTheDocument())
    expect(editor).toHaveValue('print("keep me")')
    expect(screen.queryByRole('button', { name: 'Submit this attempt' })).not.toBeInTheDocument()
    expect(screen.getByText('Remember the scale')).toBeVisible()
    expect(screen.getByRole('button', { name: 'Hint 2 of 3' })).toBeEnabled()
    expect(posts).toEqual(['/api/exercises/a1/hint'])
  })

  it('keeps code and explain-back text through exclusion and a failed restoration refresh', async () => {
    let state = 'active'
    let revision = 0
    let failRefresh = false
    const submissions: Record<string, unknown>[] = []
    vi.stubGlobal('fetch', vi.fn(async (url: string, init?: RequestInit) => {
      if (url === '/api/questions/q1/practice') {
        if (init?.method === 'POST') {
          state = JSON.parse(String(init.body)).action === 'suspend' ? 'suspended' : 'active'
          revision++
        }
        const status = { assessment_id: 'q1', state, revision, reason: null }
        return jsonResponse(init?.method === 'POST' ? status : { status, affected_reviews: 0 })
      }
      if (url.endsWith('/for-skill/k1')) return failRefresh
        ? jsonResponse({ error: { message: 'offline' } }, 503)
        : jsonResponse({ ...exercise, check_content_version: revision ? 'restored-check' : 'check-version' })
      if (url.endsWith('/assess/attempt')) {
        const body = JSON.parse(String(init?.body))
        submissions.push(body)
        return jsonResponse({ ...graded, assessment_id: body.assessment_id })
      }
      return jsonResponse({})
    }))
    renderApp(<CodeExercise sessionId="s1" skillId="k1" runner={fakeRunner(() => ok)} />)
    const editor = await screen.findByRole('textbox', { name: /Your code/ })
    fireEvent.change(editor, { target: { value: 'print("retained")' } })
    fireEvent.click(screen.getByRole('button', { name: /^Run$/ }))
    fireEvent.click(await screen.findByRole('button', { name: 'Submit this attempt' }))
    const answer = await screen.findByRole('textbox', { name: exercise.check_question })
    fireEvent.change(answer, { target: { value: 'Scaling keeps values comparable.' } })
    const panel = screen.getByLabelText('Explain-back practice choices')
    fireEvent.click(within(panel).getByRole('button', { name: 'Question practice options' }))
    fireEvent.click(await within(panel).findByRole('button', { name: 'Exclude this question' }))
    await waitFor(() => expect(screen.getByRole('button', { name: 'Check my answer' })).toBeDisabled())
    expect(screen.getByRole('button', { name: 'Submit this attempt' })).toBeEnabled()
    fireEvent.click(within(panel).getByRole('button', { name: 'Restore this question' }))
    failRefresh = true
    fireEvent.click(await within(panel).findByRole('button', { name: 'Refresh restored explain-back question' }))
    await within(panel).findByRole('alert')
    expect(answer).toHaveValue('Scaling keeps values comparable.')
    expect(editor).toHaveValue('print("retained")')
    expect(submissions).toHaveLength(1)
    failRefresh = false
    fireEvent.click(within(panel).getByRole('button', { name: 'Refresh restored explain-back question' }))
    await waitFor(() => expect(screen.getByRole('button', { name: 'Check my answer' })).toBeEnabled())
    expect(screen.getByRole('button', { name: 'Submit this attempt' })).toBeEnabled()
    fireEvent.click(screen.getByRole('button', { name: 'Check my answer' }))
    await waitFor(() => expect(submissions).toHaveLength(2))
    expect(submissions[1]).toMatchObject({ assessment_id: 'q1', content_version: 'restored-check', answer: 'Scaling keeps values comparable.' })
  })

})
