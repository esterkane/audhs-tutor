import { fireEvent, render, screen } from '@testing-library/react'
import { expect, it, vi } from 'vitest'
import { axe } from 'vitest-axe'
import { RepeatSection } from './RepeatSection'
it('requires explicit valid bounds and does not change repeat while editing', async () => {
  const change = vi.fn()
  const { container, rerender } = render(
    <RepeatSection duration={10} enabled active={null} onChange={change} />,
  )
  fireEvent.click(screen.getByText('Repeat a short section (optional)'))
  fireEvent.change(screen.getByLabelText('Section start (seconds)'), { target: { value: '4' } })
  fireEvent.change(screen.getByLabelText('Section end (seconds)'), { target: { value: '3' } })
  expect(change).not.toHaveBeenCalled()
  fireEvent.click(screen.getByRole('button', { name: 'Enable repeat' }))
  expect(screen.getByRole('alert')).toBeVisible()
  expect(change).not.toHaveBeenCalled()
  fireEvent.change(screen.getByLabelText('Section end (seconds)'), { target: { value: '6' } })
  fireEvent.click(screen.getByRole('button', { name: 'Enable repeat' }))
  expect(change).toHaveBeenCalledWith({ start: 4, end: 6 })
  rerender(<RepeatSection duration={10} enabled active={{ start: 4, end: 6 }} onChange={change} />)
  expect(screen.getByRole('status')).toHaveTextContent('Repeat on: 4.0–6.0')
  expect(await axe(container)).toHaveNoViolations()
  fireEvent.click(screen.getByRole('button', { name: 'Turn repeat off' }))
  expect(change).toHaveBeenLastCalledWith(null)
})
