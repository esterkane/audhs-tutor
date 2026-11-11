import { fireEvent, render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { expect, it } from 'vitest'
import { UploadedPdfPages } from './UploadedPdfPages'

it('retries the same versioned page in place after an image failure', () => {
  const client = new QueryClient()
  client.setQueryData(['uploaded-pdf-pages', 'doc', 'v1'], { pages: [{ page: 2, text: '', ocr: true }] })
  render(<QueryClientProvider client={client}><UploadedPdfPages uploadId="doc" versionId="v1" /></QueryClientProvider>)
  fireEvent.click(screen.getByText('Browse PDF pages'))
  const button = screen.getByRole('button', { name: 'Inspect original page 2' })
  button.focus()
  fireEvent.click(button)
  const first = screen.getByAltText('Original uploaded PDF page 2')
  expect(first.closest('figure')?.querySelector('figcaption')).toHaveTextContent(/^Original PDF page 2\.$/)
  fireEvent.error(first)
  expect(screen.getByRole('button', { name: 'Retry original page 2' })).toHaveFocus()
  fireEvent.click(button)
  const second = screen.getByAltText('Original uploaded PDF page 2')
  expect(second).not.toBe(first)
  expect(second.getAttribute('src')).toBe(first.getAttribute('src'))
  expect(screen.queryByRole('alert')).toBeNull()
})
it('updates comparison guidance when switching between textless and readable pages', () => {
  const client = new QueryClient()
  client.setQueryData(['uploaded-pdf-pages', 'doc', 'v1'], { pages: [
    { page: 1, text: '', ocr: true }, { page: 2, text: 'An authored caption.', ocr: false },
  ] })
  render(<QueryClientProvider client={client}><UploadedPdfPages uploadId="doc" versionId="v1" /></QueryClientProvider>)
  fireEvent.click(screen.getByText('Browse PDF pages'))
  fireEvent.click(screen.getByRole('button', { name: 'Inspect original page 1' }))
  expect(screen.queryByText(/Compare the original/)).not.toBeInTheDocument()
  fireEvent.change(screen.getByRole('combobox', { name: 'PDF page' }), { target: { value: '1' } })
  fireEvent.click(screen.getByRole('button', { name: 'Inspect original page 2' }))
  expect(screen.getByText('An authored caption.')).toBeInTheDocument()
  expect(screen.getByText(/Compare the original with the extracted text above/)).toBeInTheDocument()
})
