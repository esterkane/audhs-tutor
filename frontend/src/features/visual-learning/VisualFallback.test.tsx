import { render, screen } from '@testing-library/react'
import { expect, it, vi } from 'vitest'
import { VisualFallback } from './VisualFallback'
it('keeps adjacent learning content when rendering fails', () => {
  const error = vi.spyOn(console, 'error').mockImplementation(() => {})
  function Broken(): never { throw new Error('renderer unavailable') }
  try {
    render(<><VisualFallback><Broken /></VisualFallback><p>Training mean is 3.</p><button>Check answer</button></>)
    expect(screen.getByRole('status')).toHaveTextContent('diagram is unavailable')
    expect(screen.getByText('Training mean is 3.')).toBeVisible()
    expect(screen.getByRole('button', { name: 'Check answer' })).toBeEnabled()
  } finally { error.mockRestore() }
})
