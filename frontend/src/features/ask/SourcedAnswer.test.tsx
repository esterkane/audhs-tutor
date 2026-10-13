import { fireEvent, render, screen } from '@testing-library/react'
import { expect, it } from 'vitest'
import { SourcedAnswer } from './SourcedAnswer'

it('opens the exact saved passage and returns focus to the originating citation', () => {
  render(<SourcedAnswer text="Compare [source:S1] and [source:S2]." sources={[
    { chunk_id: 'a', source_key: 'S1', citation: 'First passage', text: '100 records' },
    { chunk_id: 'b', source_key: 'S2', citation: 'Second passage', text: '120 records' },
  ]} />)
  const citation = screen.getByRole('button', { name: 'Read source S2' })
  citation.focus()
  fireEvent.click(citation)
  expect(screen.getByRole('heading', { name: 'Second passage' })).toHaveFocus()
  expect(screen.getByText('120 records')).toBeVisible()
  fireEvent.click(screen.getAllByRole('button', { name: 'Back to answer citation' })[1])
  expect(citation).toHaveFocus()
  expect(screen.getByText(/Historical snapshots/)).toBeVisible()
})

it('does not duplicate prose when its parent rerenders', () => {
  const { rerender } = render(<SourcedAnswer text="One explanation." sources={[]} />)
  for (let i = 0; i < 5; i++) rerender(<SourcedAnswer text="One explanation." sources={[]} />)
  expect(screen.getAllByText('One explanation.')).toHaveLength(1)
})
