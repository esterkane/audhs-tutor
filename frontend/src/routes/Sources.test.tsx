import { fireEvent, screen } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { jsonResponse, renderApp } from '../test/utils'
import { Sources } from './Sources'

afterEach(() => vi.unstubAllGlobals())

it('does not search on opening and bounds explicit retrieval without learning writes', async () => {
  const fetch = vi.fn(async () => jsonResponse({ hits: [] }))
  vi.stubGlobal('fetch', fetch)
  renderApp(<Sources />, { route: '/sources' })
  expect(fetch).not.toHaveBeenCalled()
  fireEvent.change(screen.getByRole('searchbox'), { target: { value: 'sampling' } })
  fireEvent.click(screen.getByRole('button', { name: 'Search sources' }))
  expect(await screen.findByText(/No indexed passages matched/)).toBeVisible()
  expect(fetch).toHaveBeenCalledTimes(1)
  const [path, init] = fetch.mock.calls[0] as unknown as [string, RequestInit]
  expect(path).toBe('/api/corpus/search')
  expect(init.method).toBe('POST')
  expect(JSON.parse(String(init.body))).toEqual({ query: 'sampling', k: 8, tutor_view: false })
})

it('rejects oversized deep-linked searches before requesting retrieval', () => {
  const fetch = vi.fn()
  vi.stubGlobal('fetch', fetch)
  renderApp(<Sources />, { route: '/sources?q=' + 'a'.repeat(501) })
  expect(screen.getByRole('alert')).toHaveTextContent('500 characters')
  expect(fetch).not.toHaveBeenCalled()
  expect(screen.getByRole('button', { name: 'Search sources' })).toBeDisabled()
})
