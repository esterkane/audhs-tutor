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

it.each([['bad coordinates', ['not a coordinate']], ['too many strokes', Array(81).fill('1,2 3,4')]])(
  'offers explicit recovery for %s without overwriting saved practice on open',
  (_reason, lines) => {
    const label = { page: 1, text: 'Example', position: null }
    const source = { upload_id: 'doc', version_id: 'v', diagram_label: label }
    const draftId = 'diagram-sketch:broken:v:1'
    const key = 'curriculum-edit:v1:' + draftId
    const record = JSON.stringify({ version: 1, draftId, baseVersion: 1, baseText: '{}',
      text: JSON.stringify({lines, description: '', reflection: '', compare: false}), savedAt: new Date().toISOString() })
    sessionStorage.setItem(key, record)
    render(<DiagramSketch identity="broken" source={source} label={label} />)
    fireEvent.click(screen.getByText('Sketch or describe the diagram'))
    expect(screen.getByRole('alert')).toHaveTextContent('could not be restored')
    expect(sessionStorage.getItem(key)).toBe(record)
    fireEvent.click(screen.getByRole('button', { name: 'Start a new sketch' }))
    expect(screen.getByLabelText('My description of the diagram')).toHaveValue('')
  },
)
