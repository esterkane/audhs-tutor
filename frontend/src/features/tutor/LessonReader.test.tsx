import { useEffect } from 'react'
import { fireEvent, render, screen } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { LessonReader, SavedLessonNotes } from './LessonReader'
const audio = vi.hoisted(() => ({ stop: vi.fn() }))
vi.mock('../../components/Markdown', () => ({
  Markdown: ({ text }: { text: string }) => <pre data-testid="markdown">{text}</pre>,
}))
vi.mock('../voice/ReadAloud', () => ({
  ReadAloud: ({ text }: { text: string }) => {
    useEffect(() => () => audio.stop(), [])
    return <button data-audio={text}>Listen</button>
  },
}))
vi.mock('../curriculum/SourceViewer', () => ({
  SourceViewer: ({
    chunkId,
    citation,
    onClose,
  }: {
    chunkId: string
    citation: string
    onClose: () => void
  }) => (
    <section aria-label="Saved source passage">
      <p>
        {chunkId}: {citation}
      </p>
      <button onClick={onClose}>Close saved source</button>
    </section>
  ),
}))
afterEach(() => {
  localStorage.clear()
  vi.restoreAllMocks()
  audio.stop.mockClear()
})
const explanation = '# First idea\nLook closely.\n\n## Second idea\nTry a small example.\n'
it('preserves every character while splitting headings outside code fences and keeping tables intact', () => {
  const text =
    'Introduction\n\n# Topic\n```python\n# this is code\nprint(1)\n```\n\n| x | y |\n|---|---|\n| 1 | 2 |\n\n## Next\nDone.\n'
  render(<LessonReader identity="split" text={text} active />)
  const pieces = [screen.getByTestId('markdown').textContent]
  fireEvent.click(screen.getByRole('button', { name: 'Next section' }))
  pieces.push(screen.getByTestId('markdown').textContent)
  expect(screen.getByTestId('markdown')).toHaveTextContent('# this is code')
  expect(screen.getByTestId('markdown')).toHaveTextContent('| 1 | 2 |')
  fireEvent.click(screen.getByRole('button', { name: 'Next section' }))
  pieces.push(screen.getByTestId('markdown').textContent)
  expect(pieces.join('')).toBe(text)
  expect(screen.getByRole('button', { name: 'Next section' })).toBeDisabled()
  fireEvent.click(screen.getByRole('radio', { name: 'Full explanation' }))
  expect(screen.getByTestId('markdown').textContent).toBe(text)
})
it('restores reading position and per-section notes, and gives navigation a meaningful keyboard focus target', () => {
  const view = render(<LessonReader identity="restore" text={explanation} active />)
  fireEvent.click(screen.getByRole('button', { name: 'Next section' }))
  expect(screen.getByRole('heading', { name: 'Section 2 of 2: Second idea' })).toHaveFocus()
  fireEvent.change(screen.getByLabelText('Your notes for this section (optional)'), {
    target: { value: 'Try it with two inputs.' },
  })
  fireEvent.click(screen.getByRole('button', { name: 'Previous section' }))
  expect(screen.getByLabelText('Your notes for this section (optional)')).toHaveValue('')
  fireEvent.change(screen.getByLabelText('Choose a section'), { target: { value: '1' } })
  view.unmount()
  render(<LessonReader identity="restore" text={explanation} active />)
  expect(screen.getByLabelText('Choose a section')).toHaveValue('1')
  expect(screen.getByLabelText('Your notes for this section (optional)')).toHaveValue(
    'Try it with two inputs.',
  )
})
it('stops read-aloud on navigation, full-view changes, inactivity and unmount', () => {
  const view = render(<LessonReader identity="audio" text={explanation} active />)
  expect(screen.getByRole('button', { name: 'Listen' })).toHaveAttribute(
    'data-audio',
    '# First idea\nLook closely.\n\n',
  )
  fireEvent.click(screen.getByRole('button', { name: 'Next section' }))
  expect(audio.stop).toHaveBeenCalledTimes(1)
  fireEvent.click(screen.getByRole('radio', { name: 'Full explanation' }))
  expect(audio.stop).toHaveBeenCalledTimes(2)
  expect(screen.getByRole('button', { name: 'Listen' })).toHaveAttribute('data-audio', explanation)
  view.rerender(<LessonReader identity="audio" text={explanation} active={false} />)
  expect(audio.stop).toHaveBeenCalledTimes(3)
  expect(screen.queryByRole('button', { name: 'Listen' })).toBeNull()
  view.rerender(<LessonReader identity="audio" text={explanation} active />)
  view.unmount()
  expect(audio.stop).toHaveBeenCalledTimes(4)
})
it('keeps notes editable on storage failure and never restores another content version', () => {
  const view = render(<LessonReader identity="versions" text={explanation} active={false} />)
  fireEvent.change(screen.getByLabelText('Your notes for this section (optional)'), {
    target: { value: 'Old response note' },
  })
  view.rerender(<LessonReader identity="versions" text={`${explanation}New evidence.`} active={false} />)
  expect(screen.getByLabelText('Your notes for this section (optional)')).toHaveValue('')
  vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
    throw new Error('No space')
  })
  fireEvent.change(screen.getByLabelText('Your notes for this section (optional)'), {
    target: { value: 'Keep this note' },
  })
  expect(screen.getByLabelText('Your notes for this section (optional)')).toHaveValue('Keep this note')
  expect(screen.getByRole('status')).toHaveTextContent('Could not save')
})
it('keeps reference definitions, footnotes and text without headings in one complete document', () => {
  for (const text of [
    'No headings\nJust text.',
    '# One\nSee [source][id]\n## Two\n[id]: https://example.org\n',
    '# One\nA claim[^1]\n## Two\n[^1]: Supporting detail\n',
  ]) {
    const view = render(<LessonReader identity="whole" text={text} active={false} />)
    expect(screen.getByTestId('markdown').textContent).toBe(text)
    expect(screen.queryByRole('button', { name: 'Next section' })).toBeNull()
    view.unmount()
  }
})

it('recovers notes and original explanation after the live turn unmounts, scoped to one session', () => {
  const live = render(<LessonReader identity="session-a:turn-1" text={explanation} active={false} />)
  fireEvent.change(screen.getByLabelText('Your notes for this section (optional)'), {
    target: { value: 'Keep this idea after the question.' },
  })
  live.unmount()
  const archive = render(<SavedLessonNotes sessionId="session-a" />)
  fireEvent.click(screen.getByText('Saved lesson notes (1)'))
  fireEvent.click(screen.getByText('Explanation 1: First idea'))
  expect(screen.getByText('Keep this idea after the question.')).toBeVisible()
  fireEvent.click(screen.getByText('Read the saved explanation'))
  expect(screen.getByTestId('markdown').textContent).toBe(explanation)
  expect(screen.queryByRole('button', { name: 'Listen' })).toBeNull()
  archive.rerender(<SavedLessonNotes sessionId="session" />)
  expect(screen.getByText('Saved lesson notes (0)')).toBeVisible()
})
it('shows archive storage denial without breaking the current page', () => {
  vi.spyOn(Storage.prototype, 'key').mockImplementation(() => {
    throw new Error('Denied')
  })
  localStorage.setItem('fixture', 'value')
  render(<SavedLessonNotes sessionId="denied" />)
  fireEvent.click(screen.getByText('Saved lesson notes (0)'))
  expect(screen.getByRole('alert')).toHaveTextContent('denied storage access')
})
it('refreshes a mounted archive when a reader saves notes', () => {
  render(
    <>
      <SavedLessonNotes sessionId="session-live" />
      <LessonReader identity="session-live:turn-1" text={explanation} active={false} />
    </>,
  )
  expect(screen.getByText('Saved lesson notes (0)')).toBeVisible()
  fireEvent.change(screen.getByLabelText('Your notes for this section (optional)'), {
    target: { value: 'New note' },
  })
  expect(screen.getByText('Saved lesson notes (1)')).toBeVisible()
})
it('archives numbered source references with stable chunk identifiers and labels legacy omissions', () => {
  const live = render(
    <LessonReader
      identity="citations:turn"
      text={'# Claim\nEvidence [1].'}
      active={false}
      sources={[{ chunk_id: 'chunk-example', citation: 'Example chapter, page 4', cited: true }]}
    />,
  )
  fireEvent.change(screen.getByLabelText('Your notes for this explanation (optional)'), {
    target: { value: 'Check this evidence.' },
  })
  live.unmount()
  const archive = render(<SavedLessonNotes sessionId="citations" />)
  fireEvent.click(screen.getByText('Saved lesson notes (1)'))
  fireEvent.click(screen.getByText('Explanation 1: Claim'))
  fireEvent.click(screen.getByText('Read the saved explanation'))
  expect(screen.getByText('Example chapter, page 4')).toBeVisible()
  expect(screen.queryByRole('region', { name: 'Saved source passage' })).toBeNull()
  fireEvent.click(screen.getByRole('button', { name: 'Example chapter, page 4' }))
  expect(screen.getByRole('region', { name: 'Saved source passage' })).toBeVisible()
  fireEvent.click(screen.getByRole('button', { name: 'Close saved source' }))
  expect(screen.queryByRole('region', { name: 'Saved source passage' })).toBeNull()
  expect(screen.getByText('Source chunk: chunk-example')).toBeVisible()
  expect(screen.getByRole('list').tagName).toBe('OL')
  archive.unmount()
  localStorage.setItem(
    'lesson-reader:v1:legacy:turn:hash',
    JSON.stringify({
      text: 'Old explanation [1]',
      reading: { selected: 0, full: true, notes: { full: 'Legacy note' } },
    }),
  )
  render(<SavedLessonNotes sessionId="legacy" />)
  fireEvent.click(screen.getByText('Saved lesson notes (1)'))
  fireEvent.click(screen.getByText('Explanation 1: Introduction'))
  fireEvent.click(screen.getByText('Read the saved explanation'))
  expect(screen.getByText(/Source details are unavailable/)).toBeVisible()
})
