import { fireEvent, render, screen } from '@testing-library/react'
import { expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Library } from './Library'
vi.mock('../features/curriculum/api', () => ({
  useDrafts: () => ({ data: { drafts: [] }, isPending: false, isError: false, refetch: vi.fn() }),
}))
it('offers one search and keeps secondary browsing behind a disclosure', () => {
  render(
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter>
        <Library />
      </MemoryRouter>
    </QueryClientProvider>,
  )
  expect(screen.getByRole('heading', { level: 1, name: 'Library' })).toBeVisible()
  expect(screen.getByRole('searchbox', { name: 'Search phrase' })).toBeVisible()
  expect(screen.getByRole('link', { name: 'Create or continue knowledge material' })).toHaveAttribute(
    'href',
    '/curriculum',
  )
  expect(screen.queryByRole('link', { name: 'Search material' })).toBeNull()
  expect(screen.queryByRole('link', { name: 'Browse source passages' })).toBeNull()
  fireEvent.click(screen.getByText('Import and other library views'))
  expect(screen.getByRole('link', { name: 'Import and manage source files' })).toHaveAttribute(
    'href',
    '/corpus',
  )
  expect(screen.getByRole('link', { name: 'Browse saved answers' })).toHaveAttribute('href', '/answers')
})
