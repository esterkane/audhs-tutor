import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import BreakDesign from './BreakDesign'
import { useComfort } from './comfortStore'

describe('optional break designs', () => {
  it('defaults off and remembers an explicit choice on this device', () => {
    expect(useComfort.getState().breakDesign).toBe('off')
    useComfort.getState().setBreakDesign('frost')
    expect(JSON.parse(localStorage.getItem('audhs-comfort')!).state.breakDesign).toBe('frost')
    useComfort.getState().setBreakDesign('off')
  })
  it.each(['frost', 'liquid'] as const)('changes %s only on a button action, without animation', design => {
    const { container } = render(<BreakDesign design={design} />)
    const graphic = container.querySelector('svg')!
    const before = graphic.innerHTML
    fireEvent.click(screen.getByRole('button', { name: 'Change pattern' }))
    expect(graphic.innerHTML).not.toBe(before)
    expect(container.querySelector('animate, canvas')).toBeNull()
    expect(graphic).toHaveAttribute('aria-hidden', 'true')
  })
})
