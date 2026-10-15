import { fireEvent, render, screen } from '@testing-library/react'
import { useState } from 'react'
import { expect, it, vi } from 'vitest'
import { apiFetch } from '../../lib/api'
import { SourcePicker } from './SourcePicker'
import { previousPassages, type SelectablePassage } from './useSelectedPassages'

vi.mock('../../lib/api', () => ({ apiFetch: vi.fn() }))
const source = { chunk_id: 'old', citation: 'Reference version 1', text: 'Fit on training data only.' }

it('rejects malformed snapshots without inventing current search or trust metadata', () => {
  expect(previousPassages([source])).toEqual([source])
  expect(previousPassages([source, source])).toBeNull()
  expect(previousPassages([{ ...source, text: null }])).toBeNull()
  expect(previousPassages([{ ...source, text: 'x'.repeat(16001) }])).toBeNull()
  expect(previousPassages([{ ...source, score: 1, trust_tier: 3 }])).toEqual([source])
})

it('shows historical passages without selecting or searching and preserves existing selections', () => {
  function Fixture() {
    const [selected, set] = useState<SelectablePassage[]>([{ chunk_id: 'kept', citation: 'Already selected', text: 'Keep me' }])
    return <SourcePicker disabled={false} previousSources={[source]} selection={{ selected, set, invalid: false, error: '' }} />
  }
  render(<Fixture />)
  fireEvent.click(screen.getByText(/Attach local sources/))
  fireEvent.click(screen.getByRole('button', { name: 'Review previous passages' }))
  expect(apiFetch).not.toHaveBeenCalled()
  expect(screen.getByRole('checkbox', { name: source.citation })).not.toBeChecked()
  expect(screen.getByRole('button', { name: 'Remove Already selected' })).toBeVisible()
  fireEvent.click(screen.getByRole('checkbox', { name: source.citation }))
  expect(screen.getByRole('button', { name: `Remove ${source.citation}` })).toBeVisible()
  fireEvent.change(screen.getByLabelText('Find passages in your local library'), { target: { value: 'Different query' } })
  expect(screen.getByRole('button', { name: `Remove ${source.citation}` })).toBeVisible()
  expect(apiFetch).not.toHaveBeenCalled()
})
