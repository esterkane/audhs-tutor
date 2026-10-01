import { describe, expect, it, vi } from 'vitest'
import { fireEvent, screen } from '@testing-library/react'
import { renderApp } from '../../test/utils'
import { PLAIN_EDITOR_KEY } from './editorPreference'

// A Proxy keeps the static members (`theme`, `lineWrapping`, …) used at module scope intact and
// makes only the constructor fail — the failure the guarded mount is designed for.
vi.mock('@codemirror/view', async (orig) => {
  const m = await orig<typeof import('@codemirror/view')>()
  return {
    ...m,
    EditorView: new Proxy(m.EditorView, {
      construct() {
        throw new Error('boom')
      },
    }),
  }
})

const exercise = {
  assessment_id: 'a1',
  skill_id: 'k1',
  exercise_id: 'x',
  title: 'T',
  prompt: 'P',
  success_criteria: [],
  starter_code: 'x = 0\n',
  checks: [],
  packages: [],
  runtime: 'pyodide',
  timeout_s: 10,
  max_output_chars: 100,
  hints_available: 0,
  policy: { where: 'w', network: 'n', filesystem: 'f', runtime_download: 'r' },
  sources: [],
  check_assessment_id: null,
  check_question: null,
}

describe('CodeEditor fallback', () => {
  it('falls back to the plain editor, says so, and does not persist the fallback as a preference', async () => {
    localStorage.clear()
    vi.stubGlobal(
      'fetch',
      vi.fn(
        async () =>
          new Response(JSON.stringify(exercise), { headers: { 'content-type': 'application/json' } }),
      ),
    )
    const { CodeExercise } = await import('./CodeExercise')
    renderApp(
      <CodeExercise
        sessionId="s1"
        skillId="k1"
        runner={{
          load: async () => {},
          run: async () => ({
            stdout: '',
            truncated: false,
            error: null,
            results: [],
            timedOut: false,
            ms: 0,
          }),
          dispose: () => {},
        }}
      />,
    )
    const note = await screen.findByText('The code editor could not start (boom); using the plain editor.')
    expect(note).toHaveAttribute('role', 'status')
    const plain = screen.getByLabelText(/Tab inserts two spaces/) as HTMLTextAreaElement
    expect(plain.tagName).toBe('TEXTAREA')
    expect(plain.value).toBe('x = 0\n')
    expect(localStorage.getItem(PLAIN_EDITOR_KEY)).toBeNull()
    // trying the code editor again fails the same way and lands on the plain editor once more
    fireEvent.click(screen.getByRole('button', { name: 'Switch to the code editor' }))
    expect(await screen.findByText(/could not start \(boom\)/)).toBeInTheDocument()
    expect(screen.getByLabelText(/Tab inserts two spaces/)).toBeInTheDocument()
    expect(localStorage.getItem(PLAIN_EDITOR_KEY)).toBeNull()
    vi.unstubAllGlobals()
  })
})
