import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { SessionOut } from '../../lib/api'
import { SessionContext } from './SessionContext'

const session = {
  state: { block_status: 'running', block_index: 0, skill_id: 'active', phase: 'teach' },
  plan: [{ type: 'new_material', planned_min: 10 }],
  active_skill: { id: 'active', title: 'Current concept', description: 'Explain the current idea.' },
  next_skill: { id: 'next', title: 'Unrelated recommendation' },
} as unknown as SessionOut

describe('persisted learning context', () => {
  it('uses one concept heading in the compact session orientation', () => {
    render(<SessionContext data={session} compact />)
    expect(screen.getByRole('heading', { level: 1, name: 'Learn: Current concept' })).toBeVisible()
    expect(screen.queryByText('Concept:')).not.toBeInTheDocument()
  })
  it('uses the active concept rather than the next recommendation', () => {
    render(<SessionContext data={session} />)
    expect(screen.getByText('Explain the current idea.')).toBeVisible()
    expect(screen.getByText('Current concept')).toBeVisible()
    expect(screen.getByText('Activity 1 of 1 · New material · about 10 min')).toBeVisible()
    expect(screen.queryByText('Unrelated recommendation')).not.toBeInTheDocument()
  })
  it('does not substitute stale context when provenance is missing', () => {
    render(<SessionContext data={{ ...session, state: { ...session.state, skill_id: 'different' } }} />)
    expect(screen.getByText('Concept unavailable')).toBeVisible()
    expect(screen.queryByText('Explain the current idea.')).not.toBeInTheDocument()
  })
  it('does not label a movement activity with an academic goal', () => {
    render(<SessionContext data={{ ...session, state: { ...session.state, phase: 'practice' } }} />)
    expect(screen.queryByText('Learning goal')).not.toBeInTheDocument()
  })
  it('does not show stale context after the activity ends', () => {
    const { container } = render(<SessionContext data={{ ...session, state: { ...session.state, block_status: 'ended' } }} />)
    expect(container).toBeEmptyDOMElement()
  })
})
