import type { DraftOut } from '../features/curriculum/api'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { axe } from 'vitest-axe'
import { jsonResponse, renderApp } from '../test/utils'
import { Curriculum } from './Curriculum'

const material = {
  courses: [
    {
      course: 'PyTorch Fundamentals',
      documents: 3,
      chunks: 12,
      drafts: 0,
      published_skills: 0,
      status: 'searchable',
    },
  ],
}
const sections = { course: 'PyTorch Fundamentals', sections: [{ section: 'Tensors', documents: 3 }] }
const sourcesList = {
  course: 'PyTorch Fundamentals',
  counts: { primary: 1, supplemental: 1, excluded: 1 },
  sources: [
    {
      document_id: 'doc1',
      title: 'Tensors intro',
      section: 'Tensors',
      lecture: 'Tensors intro',
      source_type: 'udemy_caption',
      uri: '/x/001 - Tensors intro.vtt',
      chunks: 4,
      role: 'primary',
      reason: 'lecture material (caption, transcript, slides, notes, document)',
      decided_by: 'suggested',
    },
    {
      document_id: 'doc2',
      title: 'community-notebook',
      section: 'Tensors',
      lecture: null,
      source_type: 'notebook',
      uri: '/x/community-notebook.ipynb',
      chunks: 2,
      role: 'supplemental',
      reason: 'unnumbered code or notebook: reference material, not a lecture',
      decided_by: 'suggested',
    },
    {
      document_id: 'doc3',
      title: 'sponsor page',
      section: 'Tensors',
      lecture: null,
      source_type: 'markdown',
      uri: '/x/sponsor.md',
      chunks: 1,
      role: 'excluded',
      reason: '',
      decided_by: 'owner',
    },
  ],
}
const draft = {
  id: 'd1',
  course: 'PyTorch Fundamentals',
  section: 'Tensors',
  title: 'PyTorch Fundamentals › Tensors',
  status: 'draft',
  origin: 'deterministic',
  version: 1,
  payload: {
    skills: [{ slug: 'py-tensors', title: 'Tensors', prerequisites: [] }],
    learning_objects: [{ skill: 'py-tensors', concept: 'Tensors', goal: 'g', sources: ['c1'] }],
    assessments: [],
  },
  problems: [{ level: 'error', where: 'py-tensors', message: 'at least one assessment is required' }],
  created_at: 'now',
  updated_at: 'now',
  published_at: null,
  model_call_id: null,
}

function setup(initial: DraftOut[] = [], publishError = false) {
  let drafts = initial
  const calls: Array<{ url: string; method: string; body: unknown }> = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, init?: RequestInit) => {
      const method = init?.method ?? 'GET'
      const body = init?.body ? JSON.parse(String(init.body)) : undefined
      if (method !== 'GET') calls.push({ url, method, body })
      if (url.endsWith('/material')) return jsonResponse(material)
      if (url.includes('/sections')) return jsonResponse(sections)
      if (url.includes('/chunks/'))
        return jsonResponse({
          chunk_id: 'question-source',
          text: 'Specific question evidence.',
          citation: 'Course › Question source',
          document_title: 'Question source',
          source_type: 'text',
          trust_tier: 2,
          uri: '/test/source.txt',
        })
      if (url.includes('/sources/')) return jsonResponse({})
      if (url.includes('/sources')) return jsonResponse(sourcesList)
      if (url.endsWith('/drafts') && method === 'POST') {
        drafts = [draft]
        return jsonResponse(draft)
      }
      if (url.endsWith('/drafts')) return jsonResponse({ drafts })
      if (url.endsWith('/publish')) {
        if (publishError)
          return jsonResponse(
            { error: { code: 'bad_request', message: 'Activation failed; draft unchanged.' } },
            400,
          )
        const published = { ...drafts[0], status: 'published' }
        drafts = [published]
        return jsonResponse({ draft: published, skills: 1, assessments: 1 })
      }
      if (method === 'PUT') {
        const updated = { ...drafts[0], payload: body.payload, version: 2, problems: [] }
        drafts = [updated]
        return jsonResponse(updated)
      }
      return jsonResponse({})
    }),
  )
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const rendered = renderApp(
    <QueryClientProvider client={qc}>
      <Curriculum />
    </QueryClientProvider>,
    { route: '/curriculum' },
  )
  return {
    ...rendered,
    calls,
    refresh: async (next: DraftOut[]) => {
      drafts = next
      await qc.invalidateQueries({ queryKey: ['curriculum', 'drafts'] })
    },
  }
}
async function chooseCourse() {
  await screen.findByRole('option', { name: 'PyTorch Fundamentals' })
  fireEvent.change(screen.getByLabelText('Course'), { target: { value: 'PyTorch Fundamentals' } })
}

afterEach(() => vi.unstubAllGlobals())

describe('Curriculum', () => {
  it('guides draft creation, blocks invalid or unsaved activation, then activates explicitly', async () => {
    const { container, calls } = setup()
    await chooseCourse()
    fireEvent.click(screen.getByText('Create a new section draft'))
    fireEvent.click(await screen.findByRole('button', { name: 'Create draft' }))
    expect(await screen.findByText(/at least one assessment is required/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Activate lessons' })).toBeDisabled()
    expect(screen.getByText(/You’ll learn:/).parentElement).toHaveTextContent('g')
    expect(screen.getByText('Advanced: edit draft data').closest('details')).not.toHaveAttribute('open')
    fireEvent.click(screen.getByText('Advanced: edit draft data'))
    fireEvent.change(screen.getByLabelText('Draft JSON'), {
      target: {
        value: JSON.stringify({ ...draft.payload, assessments: [{ skill: 'py-tensors', kind: 'mcq' }] }),
      },
    })
    expect(screen.getByLabelText('Course')).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Back to sections' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Activate lessons' })).toBeDisabled()
    fireEvent.click(screen.getByRole('button', { name: 'Save changes' }))
    await waitFor(() => expect(screen.getByRole('button', { name: 'Activate lessons' })).toBeEnabled())
    expect(await axe(container)).toHaveNoViolations()
    expect(calls.filter((c) => c.url.endsWith('/publish'))).toHaveLength(0)
    fireEvent.click(screen.getByRole('button', { name: 'Activate lessons' }))
    expect(await screen.findByText('These lessons are active.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Go to Home' })).toHaveAttribute('href', '/')
    expect(calls.filter((c) => c.url.endsWith('/publish'))).toHaveLength(1)
  })

  it('shows only this course’s drafts and resets preview and JSON when changing sections', async () => {
    const second = {
      ...draft,
      id: 'd2',
      section: 'Shapes',
      payload: { ...draft.payload, skills: [{ slug: 'shapes', title: 'Shapes', prerequisites: [] }] },
    }
    setup([draft, second, { ...draft, id: 'other', course: 'Other course', section: 'Hidden section' }])
    await chooseCourse()
    expect(screen.queryByText('Hidden section')).not.toBeInTheDocument()
    fireEvent.click(await screen.findByRole('button', { name: 'Review Tensors' }))
    expect(screen.getByLabelText('Draft JSON')).toHaveValue(JSON.stringify(draft.payload, null, 2))
    fireEvent.click(screen.getByRole('button', { name: 'Back to sections' }))
    fireEvent.click(screen.getByRole('button', { name: 'Review Shapes' }))
    expect(screen.getByLabelText('Draft JSON')).toHaveValue(JSON.stringify(second.payload, null, 2))
    expect(screen.getByText('1. Shapes')).toBeInTheDocument()
  })

  it('keeps valid saved drafts inactive while edits are unsaved, and allows discard', async () => {
    const { calls } = setup([{ ...draft, problems: [] }])
    await chooseCourse()
    fireEvent.click(await screen.findByRole('button', { name: 'Review Tensors' }))
    fireEvent.click(screen.getByText('Advanced: edit draft data'))
    fireEvent.change(screen.getByLabelText('Draft JSON'), { target: { value: '{invalid' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save changes' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Not valid JSON')
    expect(screen.getByRole('button', { name: 'Activate lessons' })).toBeDisabled()
    fireEvent.click(screen.getByRole('button', { name: 'Discard unsaved edits' }))
    expect(screen.getByRole('button', { name: 'Activate lessons' })).toBeEnabled()
    expect(calls).toHaveLength(0)
  })

  it('keeps source choices secondary and saves or resets explicit roles', async () => {
    const { calls } = setup()
    await chooseCourse()
    fireEvent.click(await screen.findByText(/Advanced: choose source files/))
    fireEvent.change(screen.getByLabelText('Role of community-notebook'), { target: { value: 'excluded' } })
    await waitFor(() => expect(calls).toHaveLength(1))
    expect(calls[0]).toMatchObject({ method: 'PUT', body: { role: 'excluded', reason: '' } })
    fireEvent.click(screen.getByRole('button', { name: 'use suggestion' }))
    await waitFor(() => expect(calls).toHaveLength(2))
    expect(calls[1].method).toBe('DELETE')
  })
})

it('shows question-specific source evidence and readable assessment criteria', async () => {
  const detailed = {
    ...draft,
    problems: [],
    payload: {
      ...draft.payload,
      assessments: [
        {
          skill: 'py-tensors',
          kind: 'mcq',
          item: { question: 'Which shape?', options: ['Scalar', 'Vector'], answer: 1 },
          source_chunk_id: 'question-source',
        },
        {
          skill: 'py-tensors',
          kind: 'explain_back',
          item: { prompt: 'Explain the shape.' },
          rubric: [{ criterion: 'Explains dimensions', keywords: ['dimension'] }],
        },
      ],
    },
  }
  setup([detailed])
  await chooseCourse()
  fireEvent.click(await screen.findByRole('button', { name: 'Review Tensors' }))
  fireEvent.click(screen.getByText('Review practice, questions and sources'))
  expect(screen.getByText('Which shape?')).toBeInTheDocument()
  expect(screen.getByText('Explain the shape.')).toBeInTheDocument()
  fireEvent.click(screen.getAllByText('Review answer and grading criteria')[1])
  expect(screen.getByText('Explains dimensions')).toBeVisible()
  fireEvent.click(screen.getByRole('button', { name: 'Read question source' }))
  const evidence = await screen.findByText('Specific question evidence.')
  expect(evidence.closest('li')).toHaveTextContent('1. Tensors')
})

it('uses refreshed drafts after saving and protects unsaved text against newer server content', async () => {
  const { refresh } = setup([{ ...draft, problems: [] }])
  await chooseCourse()
  fireEvent.click(await screen.findByRole('button', { name: 'Review Tensors' }))
  fireEvent.click(screen.getByText('Advanced: edit draft data'))
  const input = screen.getByLabelText('Draft JSON')
  fireEvent.change(input, { target: { value: JSON.stringify({ ...draft.payload, domain: 'ai_ml' }) } })
  fireEvent.click(screen.getByRole('button', { name: 'Save changes' }))
  await waitFor(() => expect(screen.getByRole('button', { name: 'Activate lessons' })).toBeEnabled())
  const updated = {
    ...draft,
    version: 3,
    problems: [],
    payload: {
      ...draft.payload,
      learning_objects: [{ ...draft.payload.learning_objects[0], goal: 'New goal from server' }],
    },
  }
  await act(async () => {
    await refresh([updated])
  })
  await waitFor(() => expect(input).toHaveValue(JSON.stringify(updated.payload, null, 2)))
  expect(screen.getByText('New goal from server', { exact: false, selector: 'p' })).toBeInTheDocument()
  fireEvent.change(input, { target: { value: 'my unsaved text' } })
  const newest = { ...updated, version: 4, payload: { ...updated.payload, domain: 'language' } }
  await act(async () => {
    await refresh([newest])
  })
  expect(input).toHaveValue('my unsaved text')
  await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('changed elsewhere'))
  expect(screen.getByRole('button', { name: 'Save changes' })).toBeDisabled()
  expect(screen.getByRole('button', { name: 'Activate lessons' })).toBeDisabled()
  fireEvent.click(screen.getByRole('button', { name: 'Discard unsaved edits' }))
  expect(input).toHaveValue(JSON.stringify(newest.payload, null, 2))
  vi.unstubAllGlobals()
})

it('keeps the draft available and shows a failed activation without a success message', async () => {
  const { calls } = setup([{ ...draft, problems: [] }], true)
  await chooseCourse()
  fireEvent.click(await screen.findByRole('button', { name: 'Review Tensors' }))
  fireEvent.click(screen.getByRole('button', { name: 'Activate lessons' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('Activation failed')
  expect(screen.queryByText('These lessons are active.')).not.toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Activate lessons' })).toBeEnabled()
  expect(calls.filter((c) => c.url.endsWith('/publish'))).toHaveLength(1)
})

it('reports course loading failures instead of showing an empty course list', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => jsonResponse({ error: { code: 'offline', message: 'Offline' } }, 503)),
  )
  renderApp(<Curriculum />)
  expect(screen.getByRole('status')).toHaveTextContent('Loading courses')
  expect(await screen.findByRole('alert')).toHaveTextContent('Courses could not load')
  expect(screen.getByRole('button', { name: 'Retry courses' })).toBeEnabled()
  expect(screen.queryByText(/No course material yet/)).not.toBeInTheDocument()
})
