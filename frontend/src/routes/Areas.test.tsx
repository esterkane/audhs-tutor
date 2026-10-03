import { fireEvent, screen } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { jsonResponse, renderApp } from '../test/utils'
import { Areas } from './Areas'

vi.mock('./Curriculum', () => ({
  DraftEditor: ({ draft }: { draft: { id: string } }) => <p>Reviewing draft {draft.id}</p>,
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
