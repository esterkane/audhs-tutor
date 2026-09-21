import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { axe } from 'vitest-axe'
import { jsonResponse, renderApp } from '../../test/utils'
import { CodeExercise } from './CodeExercise'
import type { Runner, RunResult } from './runner'

const exercise = {
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
    runtime_download: 'jsDelivr once',
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
  afterEach(() => {
    vi.unstubAllGlobals()
    localStorage.clear()
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
    expect(submit).toBeDisabled() // confidence still missing
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
    expect(attempt).toMatchObject({ assessment_id: 'a1', confidence_pre: 4, hint_count: 0 })
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
    expect((posts[posts.length - 1].body as Record<string, unknown>).assessment_id).toBe('q1')
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

  it('explains a runtime that cannot load, accessibly, and still shows the exercise', async () => {
    stub([])
    renderApp(
      <CodeExercise sessionId="s1" skillId="k1" runner={fakeRunner(() => ok, 'network unreachable')} />,
    )
    fireEvent.click(await screen.findByRole('button', { name: 'Run' }))
    expect(await screen.findByRole('alert')).toHaveTextContent(/could not be loaded \(network unreachable\)/)
    expect(screen.getByLabelText(/Your code/)).toBeInTheDocument()
  })
})
