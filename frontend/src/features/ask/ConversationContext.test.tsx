import { fireEvent, render, screen } from '@testing-library/react'
import { expect, it } from 'vitest'
import { ConversationContext } from './ConversationContext'

it('shows historical context and omitted-history limits without treating it as evidence', () => {
  render(<ConversationContext metadata={{ context_window: { version: 1, older_exchanges_omitted: true }, opening_context: { question: 'Why do models learn weights?' } }} />)
  fireEvent.click(screen.getByText('Context used for this answer'))
  expect(screen.getByText('Why do models learn weights?')).toBeVisible()
  expect(screen.getByText(/Older intervening exchanges were omitted/)).toBeVisible()
  expect(screen.getByText(/not verified source evidence/)).toBeVisible()
})
it('does not fabricate context for legacy records', () => {
  const { rerender } = render(<ConversationContext metadata={{}} />)
  expect(screen.queryByText('Context used for this answer')).not.toBeInTheDocument()
  rerender(<ConversationContext metadata={{ context_window: { version: 1, opening_unavailable: true } }} />)
  fireEvent.click(screen.getByText('Context used for this answer'))
  expect(screen.getByText(/not reconstructed/)).toBeVisible()
})
