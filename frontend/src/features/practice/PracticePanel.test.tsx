import { fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { jsonResponse, renderApp } from '../../test/utils'
import { PracticePanel } from './PracticePanel'
import { VocabPanel } from './VocabPanel'

describe('practice blocks', () => {
  afterEach(() => {
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
    sessionStorage.clear()
  })

  it('movement block: three concrete options, rating, log then continue; skip is one click', async () => {
    const posts: Array<{ url: string; body: Record<string, unknown> }> = []
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string, init?: RequestInit) => {
        if (init?.method === 'POST') {
          posts.push({ url, body: JSON.parse(String(init.body)) })
          return jsonResponse({
            event_id: 'e',
            domain: 'movement',
            activity: 'stretch',
            duration_min: 0,
            self_rating: 4,
          })
        }
        return jsonResponse({
          activities: { movement: ['walk 5 minutes', 'stretch', 'stairs or squats'], guitar: [] },
        })
      }),
    )
    const done = vi.fn()
    const skip = vi.fn()
    renderApp(<PracticePanel sessionId="s1" domain="movement" plannedMin={4} onDone={done} onSkip={skip} />)
    expect(await screen.findByText('stretch')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Log and continue' })).toBeDisabled()
    fireEvent.click(screen.getByText('stretch'))
    fireEvent.click(screen.getByText('4'))
    fireEvent.click(screen.getByRole('button', { name: 'Log and continue' }))
    await waitFor(() => expect(done).toHaveBeenCalled())
    expect(posts[0].url).toBe('/api/practice')
    expect(posts[0].body).toMatchObject({
      session_id: 's1',
      domain: 'movement',
      activity: 'stretch',
      self_rating: 4,
    })
    fireEvent.click(screen.getByRole('button', { name: 'Skip this block' }))
    expect(skip).toHaveBeenCalled()
  })

  it('language block: reveal then rate a due card, continue when none are left', async () => {
    const rated: string[] = []
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string, init?: RequestInit) => {
        if (init?.method === 'POST' && url.includes('/api/review/')) {
          rated.push(url)
          return jsonResponse({ item_id: 'v1' })
        }
        if (url.includes('/api/review/due'))
          return jsonResponse({
            items: [
              {
                item_id: 'v1',
                skill_id: 'n',
                skill_title: 'German vocabulary',
                item_type: 'vocab',
                question: 'der Hund',
                options: null,
                reveal: 'the dog',
                due: 'now',
                state: 'new',
              },
            ],
            cap: 10,
            total_due: 1,
            as_of: 'now',
          })
        return jsonResponse({})
      }),
    )
    const done = vi.fn()
    renderApp(<VocabPanel sessionId="s1" onDone={done} />)
    expect(await screen.findByText('der Hund')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Show translation' }))
    expect(screen.getByText('the dog')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Good' }))
    await waitFor(() => expect(rated).toHaveLength(1))
    expect(rated[0]).toContain('/api/review/v1')
    expect(await screen.findByText('1 cards reviewed.')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Continue' }))
    expect(done).toHaveBeenCalled()
  })
  it('retains a vocabulary rating through checkpoint failure and recovers by stable card ID', async () => {
    let blocked = false
    let posts = 0
    const originalSet = Storage.prototype.setItem
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(function (this: Storage, key, value) {
      if (blocked && key === 'vocab-reviewed:v1:v-recovery') throw new Error('quota')
      originalSet.call(this, key, value)
    })
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string, init?: RequestInit) => {
        if (url.includes('/api/review/due'))
          return jsonResponse({
            items: ['v1', 'v2'].map((id) => ({
              item_id: id,
              question: `Question ${id}`,
              reveal: `Answer ${id}`,
            })),
            total_due: 2,
            cap: 10,
          })
        if (url.includes('/api/review/requests/'))
          return jsonResponse({ status: 'completed', result: { item_id: 'v1' } })
        if (init?.method === 'POST') {
          posts++
          blocked = true
          return jsonResponse({ item_id: 'v1' })
        }
        return jsonResponse({})
      }),
    )
    const first = renderApp(<VocabPanel sessionId="v-recovery" onDone={() => {}} />)
    fireEvent.click(await screen.findByRole('button', { name: 'Show translation' }))
    fireEvent.click(screen.getByRole('button', { name: 'Again' }))
    await screen.findByText(/vocabulary queue could not be stored/)
    expect(sessionStorage.getItem('review-request:v1:v-recovery')).not.toBeNull()
    first.unmount()
    blocked = false
    renderApp(<VocabPanel sessionId="v-recovery" onDone={() => {}} />)
    fireEvent.click(await screen.findByRole('button', { name: 'Check saved rating' }))
    fireEvent.click(await screen.findByRole('button', { name: 'Update review queue' }))
    await screen.findByText('Question v2')
    expect(screen.queryByText('Question v1')).not.toBeInTheDocument()
    expect(screen.queryByText('Answer v2')).not.toBeInTheDocument()
    expect(JSON.parse(sessionStorage.getItem('vocab-reviewed:v1:v-recovery')!)).toEqual(['v1'])
    expect(sessionStorage.getItem('review-request:v1:v-recovery')).toBeNull()
    expect(posts).toBe(1)
  })
})
