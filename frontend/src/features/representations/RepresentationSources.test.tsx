import { fireEvent, screen } from '@testing-library/react'
import { expect, it, vi } from 'vitest'
import { renderApp } from '../../test/utils'
import { RepresentationSources } from './RepresentationSources'
vi.mock('../curriculum/SourceViewer', () => ({
  SourceViewer: ({ chunkId, onClose }: { chunkId: string; onClose: () => void }) => (
    <div>
      Passage {chunkId}
      <button onClick={onClose}>Close source</button>
    </div>
  ),
}))
it('marks unknown legacy provenance without inventing sources', () => {
  renderApp(<RepresentationSources value={{ provenance_available: false, source_snapshot: [] }} />)
  expect(screen.getByText(/Original source details were not recorded/)).toBeVisible()
  expect(screen.queryByRole('button')).not.toBeInTheDocument()
})
it('opens the recorded ID and restores keyboard focus, labeling supplied context and warnings', async () => {
  renderApp(
    <RepresentationSources
      value={{
        provenance_available: true,
        source_snapshot: [
          {
            chunk_id: 'recorded',
            citation: 'Original label',
            trust_tier: 1,
            score: 1,
            flagged: ['untrusted instruction'],
            cited: false,
          },
        ],
      }}
    />,
  )
  fireEvent.click(screen.getByText('Source context used for this explanation'))
  const button = screen.getByRole('button', { name: '[1] Original label' })
  fireEvent.click(button)
  expect(await screen.findByText('Passage recorded')).toBeVisible()
  expect(screen.getByText(/supplied context, not cited/)).toBeVisible()
  expect(screen.getByText(/untrusted instruction/)).toBeVisible()
  fireEvent.click(screen.getByRole('button', { name: 'Close source' }))
  expect(button).toHaveFocus()
})
