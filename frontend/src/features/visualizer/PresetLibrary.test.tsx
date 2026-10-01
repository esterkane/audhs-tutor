import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, expect, it, vi } from 'vitest'
import { PresetLibrary } from './PresetLibrary'
import { initial } from './engine'
beforeEach(() => localStorage.clear())
it('saving a named copy selects its identity without loading over a draft', () => {
  const onLoad = vi.fn(),
    onSaved = vi.fn()
  render(<PresetLibrary preset={initial} onLoad={onLoad} onSaved={onSaved} />)
  fireEvent.change(screen.getByLabelText('Preset name'), { target: { value: 'Named copy' } })
  fireEvent.click(screen.getByRole('button', { name: 'Save as new visual' }))
  expect(onLoad).not.toHaveBeenCalled()
  expect(onSaved).toHaveBeenCalledOnce()
  expect(screen.getByRole('button', { name: 'Load Named copy' })).toBeVisible()
})
