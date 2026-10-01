import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, expect, it, vi } from 'vitest'
import { Visualizer } from '../../routes/Visualizer'
vi.mock('../sensory/useSensory', () => ({ useSensory: () => ({ reduced: true, sound: false }) }))
vi.mock('./render', () => ({ draw: vi.fn() }))
beforeEach(() => {
  localStorage.clear()
  vi.stubGlobal(
    'ResizeObserver',
    class {
      observe() {}
      disconnect() {}
    },
  )
})
it('keeps the same canvas and draft while switching views and applies without stopping the demo', () => {
  render(
    <MemoryRouter>
      <Visualizer />
    </MemoryRouter>,
  )
  const canvas = screen.getByLabelText('Audio-reactive visual preview')
  fireEvent.click(screen.getByRole('button', { name: 'Start demo' }))
  expect(screen.getByText(/Demo running/)).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Create' }))
  fireEvent.change(screen.getByRole('combobox', { name: 'Visual style' }), { target: { value: 'bars' } })
  fireEvent.click(screen.getByRole('button', { name: 'Apply preset' }))
  expect(screen.getByText(/Demo running/)).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Watch' }))
  expect(screen.getByLabelText('Audio-reactive visual preview')).toBe(canvas)
  fireEvent.click(screen.getByRole('button', { name: 'Create' }))
  expect(screen.getByRole('combobox', { name: 'Visual style' })).toHaveValue('bars')
})
