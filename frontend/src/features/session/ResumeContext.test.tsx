import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { SessionOut } from '../../lib/api'
import { ResumeContext } from './ResumeContext'
const session = { state: { block_status: 'running', block_index: 0, phase: 'assess' }, plan: [{ type: 'new_material', planned_min: 20 }] } as unknown as SessionOut

describe('resume context', () => {
  it('shows the checkpoint activity and original plan without claiming remaining time', () => {
    render(<ResumeContext session={session} />)
    expect(screen.getByText('Saved activity: New material · Understanding check.')).toBeVisible()
    expect(screen.getByText(/original plan, not time remaining/)).toBeVisible()
  })
  it.each(['ended', null])('omits stale activity when status is %s', block_status => {
    const { container } = render(<ResumeContext session={{ ...session, state: { ...session.state, block_status: block_status as 'ended' | null } }} />)
    expect(container).toBeEmptyDOMElement()
  })
  it('does not show a completed plan as unfinished work', () => {
    const { container } = render(<ResumeContext session={{ ...session, state: { ...session.state, plan_complete: true } }} />)
    expect(container).toBeEmptyDOMElement()
  })
  it('does not invent a duration for unavailable plan data', () => {
    const { container } = render(<ResumeContext session={{ ...session, plan: [] }} />)
    expect(container).toBeEmptyDOMElement()
  })
})
