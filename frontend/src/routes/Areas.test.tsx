import { act, fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { jsonResponse, renderApp } from '../test/utils'
import { Areas } from './Areas'
import { useSearchParams } from 'react-router-dom'

vi.mock('./Curriculum', () => ({
  DraftEditor: ({ draft, onDirtyChange }: { draft: { id: string }; onDirtyChange: (dirty: boolean) => void }) => <div><p>Reviewing draft {draft.id}</p><button onClick={() => onDirtyChange(true)}>Edit fixture draft</button><button onClick={() => onDirtyChange(false)}>Save fixture draft</button></div>,
}))
vi.mock('../features/programs/SavedContextAnswers', () => ({ SavedContextAnswers: () => null }))
vi.mock('../features/areas/QuestionFeedback', () => ({ FeedbackPreferences: () => null }))

afterEach(() => vi.unstubAllGlobals())

it('takes the selected area directly to its prepared draft without activating it', async () => {
  const fetchMock = vi.fn(async (url: string) => {
    if (url.endsWith('/api/areas'))
      return jsonResponse({
        areas: [
          { id: 'local', title: 'Local inference', terms: ['local'], courses: [], documents: 4, related: [] },
        ],
      })
    if (url.endsWith('/api/curriculum/drafts'))
      return jsonResponse({
        drafts: [
          {
            id: 'unfinished',
            area_id: 'local',
            title: 'Local inference',
            status: 'draft',
            payload: { area_state: 'interrupted' },
          },
          {
            id: 'prepared',
            area_id: 'local',
            title: 'Local inference',
            status: 'draft',
            payload: { area_state: 'generated' },
          },
          {
            id: 'unrelated',
            area_id: 'other',
            title: 'Another topic',
            status: 'draft',
            payload: { area_state: 'generated' },
          },
        ],
      })
    return jsonResponse(null)
  })
  vi.stubGlobal('fetch', fetchMock)
  renderApp(<Areas />, { route: '/areas?area=local' })
  fireEvent.click(await screen.findByRole('button', { name: 'Review prepared draft' }))
  expect(await screen.findByText('Reviewing draft prepared')).toBeVisible()
  expect(fetchMock.mock.calls.some(([url]) => url.endsWith('/publish'))).toBe(false)
})

for (const requested of ['prepared', 'unrelated']) {
  it(`opens only a matching selected-area draft from URL: ${requested}`, async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string) => {
        if (url.endsWith('/api/areas'))
          return jsonResponse({
            areas: [{ id: 'local', title: 'Local', terms: [], courses: [], documents: 1, related: [] }],
          })
        if (url.endsWith('/api/curriculum/drafts'))
          return jsonResponse({
            drafts: [
              {
                id: 'prepared',
                area_id: 'local',
                title: 'Local',
                status: 'draft',
                payload: { area_state: 'generated' },
              },
              {
                id: 'unrelated',
                area_id: 'other',
                title: 'Other',
                status: 'draft',
                payload: { area_state: 'generated' },
              },
            ],
          })
        return jsonResponse(null)
      }),
    )
    renderApp(<Areas />, { route: `/areas?area=local&draft=${requested}` })
    await screen.findByRole('combobox')
    if (requested === 'prepared') expect(await screen.findByText('Reviewing draft prepared')).toBeVisible()
    else expect(screen.queryByText('Reviewing draft unrelated')).not.toBeInTheDocument()
  })
}


function HistoryChange() {
  const [, setParams] = useSearchParams()
  return <button onClick={() => setParams({ area: 'other' })}>Browse other URL</button>
}
it('retains the edited draft while browser location changes, then follows it after saving', async () => {
  vi.stubGlobal('fetch', vi.fn(async (url: string) => {
    if (url.endsWith('/api/areas')) return jsonResponse({ areas: ['local', 'other'].map(id => ({ id, title: id, terms: [], courses: [], documents: 0, related: [] })) })
    if (url.endsWith('/api/curriculum/drafts')) return jsonResponse({ drafts: [{ id: 'prepared', area_id: 'local', title: 'Draft', status: 'draft', payload: { area_state: 'generated' } }] })
    return jsonResponse(null)
  }))
  renderApp(<><HistoryChange /><Areas /></>, { route: '/areas?area=local&draft=prepared' })
  fireEvent.click(await screen.findByRole('button', { name: 'Edit fixture draft' }))
  fireEvent.click(screen.getByRole('button', { name: 'Browse other URL' }))
  expect(screen.getByText('Reviewing draft prepared')).toBeVisible()
  expect(screen.getByRole('alert')).toHaveTextContent('Your edits are still open')
  fireEvent.click(screen.getByRole('button', { name: 'Save fixture draft' }))
  expect(screen.queryByText('Reviewing draft prepared')).not.toBeInTheDocument()
  expect(screen.getByRole('combobox')).toHaveValue('other')
})

it('normalizes a saved area without losing edits typed during the save', async () => {
  let finish!: (response: Response) => void
  vi.stubGlobal('fetch', vi.fn(async (url: string, init?: RequestInit) => {
    if (init?.method === 'PUT') return new Promise<Response>(resolve => { finish = resolve })
    if (url.endsWith('/api/areas')) return jsonResponse({ areas: [{ id: 'local', title: 'Local', terms: ['old'], courses: [], documents: 0, related: [] }] })
    if (url.endsWith('/api/curriculum/drafts')) return jsonResponse({ drafts: [] })
    return jsonResponse(null)
  }))
  renderApp(<Areas />, { route: '/areas?area=local' })
  fireEvent.click(await screen.findByText('Edit area name and matching terms'))
  const name = screen.getByLabelText('Area name')
  fireEvent.change(name, { target: { value: 'Python ' } })
  fireEvent.change(screen.getByLabelText('Matching terms, separated by commas'), { target: { value: 'python, python' } })
  fireEvent.click(screen.getByRole('button', { name: 'Save area' }))
  await waitFor(() => expect(finish).toBeDefined())
  fireEvent.change(name, { target: { value: 'Newer name' } })
  await act(async () => finish(jsonResponse({ areas: [{ id: 'local', title: 'Python', terms: ['python'], courses: [], documents: 0, related: [] }] })))
  expect(name).toHaveValue('Newer name')
  expect(screen.getByLabelText('Matching terms, separated by commas')).toHaveValue('python')
  expect(screen.getByRole('combobox')).toBeDisabled()
  fireEvent.change(name, { target: { value: 'Python' } })
  await waitFor(() => expect(screen.getByRole('combobox')).toBeEnabled())
})
