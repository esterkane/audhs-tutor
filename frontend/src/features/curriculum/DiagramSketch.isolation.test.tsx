import { fireEvent, render, screen } from '@testing-library/react'
import { expect, it } from 'vitest'
import { DiagramSketch } from './DiagramSketch'

it('separates practice between lessons using the same source and restores it on return', () => {
  const label = { page: 1, text: 'Example', position: null }
  const source = { upload_id: 'same-upload', version_id: 'same-version', diagram_label: label }
  const open = (identity: string) => {
    const view = render(<DiagramSketch identity={identity} source={source} label={label} />)
    fireEvent.click(screen.getByText('Sketch or describe the diagram'))
    return view
  }
  const notes = () => screen.getByLabelText('My description of the diagram')
  const first = open('first:1')
  fireEvent.change(notes(), { target: { value: 'First observation' } })
  first.unmount()
  const second = open('second:1')
  expect(notes()).toHaveValue('')
  fireEvent.change(notes(), { target: { value: 'Second observation' } })
  second.unmount()
  open('first:1')
  expect(notes()).toHaveValue('First observation')
})
