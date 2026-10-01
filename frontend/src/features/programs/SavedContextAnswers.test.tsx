import { fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { jsonResponse, renderApp } from '../../test/utils'
import { SavedContextAnswers } from './SavedContextAnswers'

afterEach(() => vi.unstubAllGlobals())
it('loads only on request with exact target scope and links the real question', async () => {
  const fetcher = vi.fn(async (url: string) => {
    expect(url).toContain('/api/answers?')
    return jsonResponse({
      items: [
        {
          id: 'saved',
          learner_question: 'Why this bin?',
          request_text: 'Internal instruction',
          preview: 'Check the boundary.',
          created_at: '2026-10-01T10:00:00Z',
        },
      ],
      next_cursor: null,
    })
  })
  vi.stubGlobal('fetch', fetcher)
  renderApp(<SavedContextAnswers courseId="course-a" sectionId="section-b" targetId="cell:3" />)
  expect(fetcher).not.toHaveBeenCalled()
  fireEvent.click(screen.getByText('Previously answered here'))
  const link = await screen.findByRole('link', { name: 'Why this bin?' })
  expect(link).toHaveAttribute('href', expect.stringContaining('target_id=cell%3A3'))
  const query = new URL(String(fetcher.mock.calls[0]?.[0]), 'http://local').searchParams
  expect(query.get('course_id')).toBe('course-a')
  expect(query.get('section_id')).toBe('section-b')
  expect(query.get('target_id')).toBe('cell:3')
  expect(screen.queryByText('Internal instruction')).not.toBeInTheDocument()
})
it('keeps a failed load retryable and distinguishes empty scoped history', async () => {
  let fail = true
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => (fail ? jsonResponse({}, 503) : jsonResponse({ items: [], next_cursor: null }))),
  )
  renderApp(<SavedContextAnswers targetId="target" />)
  fireEvent.click(screen.getByText('Previously answered here'))
  await screen.findByRole('alert')
  fail = false
  fireEvent.click(screen.getByRole('button', { name: 'Retry previous answers' }))
  await waitFor(() => expect(screen.getByText(/No saved replies for this target/)).toBeVisible())
})

it.each([
  { props: { courseId: 'course-a' }, label: 'course', expected: 'course_id=course-a' },
  { props: { areaId: 'area-b' }, label: 'learning area', expected: 'area_id=area-b' },
])('uses exact $label scope without restricting to a notebook target', async ({ props, label, expected }) => {
  const fetcher = vi.fn(async (url: string) => {
    expect(url).toContain(expected)
    expect(url).not.toContain('target_id=')
    if (props.areaId) expect(url).not.toContain('surface=playground')
    return jsonResponse({ items: [], next_cursor: null })
  })
  vi.stubGlobal('fetch', fetcher)
  renderApp(<SavedContextAnswers {...props} />)
  expect(fetcher).not.toHaveBeenCalled()
  fireEvent.click(screen.getByText(`Saved answers for this ${label}`))
  expect(await screen.findByText(new RegExp(`No saved replies for this ${label}`))).toBeVisible()
  expect(screen.getByRole('link', { name: `Browse all answers for this ${label}` })).toHaveAttribute(
    'href',
    expect.stringContaining(expected),
  )
})

it('does not turn a missing scope into a global history request', () => {
  const fetcher = vi.fn()
  vi.stubGlobal('fetch', fetcher)
  const { container } = renderApp(<SavedContextAnswers />)
  expect(container).toBeEmptyDOMElement()
  expect(fetcher).not.toHaveBeenCalled()
})
