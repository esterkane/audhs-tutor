import { fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { axe } from 'vitest-axe'
import { jsonResponse, renderApp } from '../../test/utils'
import { VocabImport } from './VocabImport'

const preview = {
  lang: 'de',
  rows: [
    { row: 1, word: 'Haus', translation: 'house', example: null, status: 'new', problem: null },
    { row: 2, word: 'Baum', translation: 'tree', example: 'Der Baum', status: 'exists', problem: null },
    {
      row: 3,
      word: '',
      translation: 'x',
      example: null,
      status: 'invalid',
      problem: 'word and translation are required',
    },
  ],
  columns: { word: 0, translation: 1 },
  delimiter: ';',
  header: true,
  counts: { new: 1, exists: 1, duplicate_in_file: 0, invalid: 1 },
  errors: [],
}

describe('VocabImport', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('previews every row with a status, lets the learner fix a row, and imports only on confirm', async () => {
    const posts: Array<[string, unknown]> = []
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string, init?: RequestInit) => {
        posts.push([url, JSON.parse(String(init?.body))])
        if (url.endsWith('/import/preview')) return jsonResponse(preview)
        return jsonResponse({ lang: 'de', added: 2, reverse_added: 0, skipped_existing: 0, invalid: 0 }, 201)
      }),
    )
    const { container } = renderApp(<VocabImport />)
    fireEvent.click(screen.getByText('Or paste the list', { selector: 'summary' }))
    fireEvent.change(screen.getByLabelText('CSV text'), { target: { value: 'Wort;Bedeutung\nHaus;house' } })
    fireEvent.click(screen.getByRole('button', { name: 'Preview' }))
    expect(await screen.findByText(/Header row detected/)).toBeInTheDocument()
    expect(
      screen.getByText(/1 to import \(0 reverse only\), 1 already cards, 0 duplicates in file, 1 invalid/),
    ).toBeInTheDocument()
    expect(screen.getByLabelText('Language')).toBeDisabled() // locked after the preview
    expect(await axe(container)).toHaveNoViolations()
    expect(screen.getByText(/invalid — word and translation are required/)).toBeInTheDocument()
    // nothing was imported by previewing
    expect(posts.filter(([u]) => u.endsWith('/api/vocab/import')).length).toBe(0)
    // fixing the invalid row makes it importable; the confirm button names the count
    fireEvent.change(screen.getByLabelText('Word, row 3'), { target: { value: 'Katze' } })
    expect(screen.getByRole('button', { name: 'Import 2 cards' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Import 2 cards' }))
    await waitFor(() => expect(posts.some(([u]) => u.endsWith('/api/vocab/import'))).toBe(true))
    const body = posts.find(([u]) => u.endsWith('/api/vocab/import'))?.[1] as {
      rows: unknown[]
      reverse: boolean
    }
    expect(body.rows).toEqual([
      { word: 'Haus', translation: 'house', example: null },
      { word: 'Katze', translation: 'x', example: null },
    ])
    expect(body.reverse).toBe(false)
    expect(await screen.findByText(/Imported 2 new cards; 0 already existed, 0 invalid/)).toBeInTheDocument()
  })

  it('shows the failure and no success line when the import request fails; removing a row is reversible', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string) => {
        if (url.endsWith('/import/preview')) return jsonResponse(preview)
        return jsonResponse({ error: { code: 'db', message: 'database locked' } }, 500)
      }),
    )
    renderApp(<VocabImport />)
    fireEvent.click(screen.getByText('Or paste the list', { selector: 'summary' }))
    fireEvent.change(screen.getByLabelText('CSV text'), { target: { value: 'Haus;house' } })
    fireEvent.click(screen.getByRole('button', { name: 'Preview' }))
    await screen.findByText(/Header row detected/)
    fireEvent.click(screen.getByRole('button', { name: 'Remove row 2' }))
    expect(screen.getByText('Row 2 removed.')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Undo remove row 2' }))
    expect(screen.getByLabelText('Word, row 2')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /Import 1 card/ }))
    expect(await screen.findByRole('alert')).toHaveTextContent(/nothing was imported/)
    expect(screen.queryByText(/Imported/)).not.toBeInTheDocument()
  })
})
