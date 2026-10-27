import { fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { Route, Routes } from 'react-router-dom'
import { jsonResponse, renderApp } from '../test/utils'
import { Sources } from './Sources'
import { Search } from './Search'
import { Library } from './Library'
afterEach(() => vi.unstubAllGlobals())
function show(route: string) {
  return renderApp(
    <Routes>
      <Route path="/sources" element={<Sources />} />
      <Route path="/search" element={<Search />} />
      <Route path="/library" element={<Library />} />
    </Routes>,
    { route },
  )
}
function fixture() {
  const fetch = vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input)
    if (url.includes('/curriculum/drafts')) return jsonResponse({ drafts: [] })
    if (url.includes('/skills')) return jsonResponse({ skills: [] })
    if (url.includes('/answers')) return jsonResponse({ items: [], next_cursor: null })
    if (url.includes('/curriculum/chunks/'))
      return jsonResponse({
        chunk_id: 'p',
        citation: 'Exact source',
        text: 'Full source passage',
        document_title: 'Example',
        trust_tier: 2,
        uri: 'example.txt',
        open_url: null,
      })
    return jsonResponse({ hits: [] })
  })
  vi.stubGlobal('fetch', fetch)
  return fetch
}
it('does not retrieve sources on opening, then submits one bounded local search without learning writes', async () => {
  const fetch = fixture()
  show('/sources')
  await screen.findByRole('heading', { name: 'Library', level: 1 })
  await waitFor(() => expect(fetch).toHaveBeenCalled())
  expect(fetch.mock.calls.filter(([url]) => String(url).includes('/corpus/search'))).toHaveLength(0)
  fireEvent.change(screen.getByRole('searchbox'), { target: { value: 'sampling' } })
  fireEvent.click(screen.getByRole('button', { name: 'Search' }))
  await screen.findByText('No indexed passages matched.')
  const source = fetch.mock.calls.filter(([url]) => String(url).includes('/corpus/search'))
  expect(source).toHaveLength(1)
  const init = (source[0] as unknown as [string, RequestInit])[1]
  expect(JSON.parse(String(init.body))).toEqual({ query: 'sampling', k: 8, tutor_view: false })
  expect(fetch.mock.calls.filter(([url]) => /assess|sessions|tutor|publish/.test(String(url)))).toHaveLength(
    0,
  )
})
it('retains an oversized legacy query for editing without retrieval', async () => {
  const fetch = fixture()
  show('/sources?q=' + 'a'.repeat(501))
  expect(await screen.findByRole('alert')).toHaveTextContent('200 characters')
  expect(screen.getByRole('searchbox')).toHaveValue('a'.repeat(501))
  expect(fetch).not.toHaveBeenCalled()
  expect(screen.getByRole('button', { name: 'Search' })).toBeDisabled()
})
it.each(['/sources', '/search'])(
  'legacy %s query and passage remain inspectable after canonical navigation',
  async (route) => {
    const fetch = fixture()
    show(route + '?q=retained&chunk=p')
    expect(await screen.findByText('Full source passage')).toBeVisible()
    expect(screen.getByRole('region', { name: 'Selected source passage' })).toHaveFocus()
    fireEvent.click(screen.getByRole('button', { name: 'Close' }))
    expect(await screen.findByRole('searchbox')).toHaveValue('retained')
    expect(
      fetch.mock.calls.filter(([url]) => /assess|sessions|tutor|publish/.test(String(url))),
    ).toHaveLength(0)
  },
)
