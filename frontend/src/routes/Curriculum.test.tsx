import { fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { axe } from 'vitest-axe'
import { Route, Routes } from 'react-router-dom'
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

describe('Curriculum', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('shows material status, proposes a draft, lists its problems, and blocks publishing until fixed', async () => {
    let drafts: unknown[] = []
    const posts: string[] = []
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string, init?: RequestInit) => {
        if (url.endsWith('/api/curriculum/material')) return jsonResponse(material)
        if (url.includes('/api/curriculum/sections')) return jsonResponse(sections)
        if (url.endsWith('/api/curriculum/drafts') && init?.method === 'POST') {
          posts.push(url)
          drafts = [draft]
          return jsonResponse(draft, 201)
        }
        if (url.endsWith('/api/curriculum/drafts')) return jsonResponse({ drafts })
        if (url.endsWith('/api/curriculum/drafts/d1') && init?.method === 'PUT') {
          posts.push(url)
          const fixed = { ...draft, version: 2, problems: [] }
          drafts = [fixed]
          return jsonResponse(fixed)
        }
        if (url.endsWith('/publish')) {
          posts.push(url)
          return jsonResponse({
            draft: { ...draft, status: 'published', problems: [] },
            skills: 1,
            edges: 0,
            learning_objects: 1,
            new_object_versions: 1,
            assessments: 1,
          })
        }
        return jsonResponse({})
      }),
    )
    const { container } = renderApp(
      <Routes>
        <Route path="/curriculum" element={<Curriculum />} />
      </Routes>,
      { route: '/curriculum' },
    )
    expect(await screen.findByRole('button', { name: 'PyTorch Fundamentals' })).toBeInTheDocument()
    expect(
      screen.getByText(/searchable · 3 documents · 12 passages · 0 published skills/),
    ).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'PyTorch Fundamentals' }))
    fireEvent.click(await screen.findByRole('button', { name: 'Propose a draft' }))
    // the draft's validation problem is listed literally and publishing is blocked
    expect(
      await screen.findByText(/error · py-tensors: at least one assessment is required/),
    ).toBeInTheDocument()
    const publish = screen.getByRole('button', { name: /Publish \(fix 1 error first\)/ })
    expect(publish).toBeDisabled()
    expect(await axe(container)).toHaveNoViolations()
    // the learner edits the JSON and re-validates; then publishing is possible
    fireEvent.change(screen.getByLabelText('Draft JSON'), {
      target: {
        value: JSON.stringify({ ...draft.payload, assessments: [{ skill: 'py-tensors', kind: 'mcq' }] }),
      },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Save and re-validate' }))
    expect(await screen.findByRole('button', { name: 'Publish these lessons' })).toBeEnabled()
    fireEvent.click(screen.getByRole('button', { name: 'Publish these lessons' }))
    expect(
      await screen.findByText(/Published: 1 skills, 0 prerequisite links, 1 new learning-object versions/),
    ).toBeInTheDocument()
    await waitFor(() => expect(posts.some((u) => u.endsWith('/publish'))).toBe(true))
  })
})
