import { fireEvent, screen } from '@testing-library/react'
import { expect, it, vi } from 'vitest'
import { Shell } from './App'
import { renderApp } from '../test/utils'
import { useMode } from '../stores/mode'
vi.mock('../features/sensory/useSensory', () => ({ useSensory: () => {} }))
vi.mock('../features/audio/AudioControls', () => ({ AudioControls: () => <button>Audio controls</button> }))
vi.mock('../features/programs/LearningCompanion', () => ({ LearningCompanion: () => null }))
vi.mock('../components/ParkingLotButton', () => ({ ParkingLotButton: () => <button>Park</button> }))

it('names the current page, provides Home and a skip link, and does not infer running state from a saved id', () => {
  useMode.setState({ sessionId: 'remembered-id' })
  renderApp(
    <Shell>
      <h1>Home content</h1>
    </Shell>,
  )
  expect(document.title).toBe('Home · AuDHS Tutor')
  expect(screen.getByRole('link', { name: 'Home' })).toHaveAttribute('aria-current', 'page')
  expect(screen.getByRole('link', { name: 'Skip to learning content' })).toHaveAttribute(
    'href',
    '#main-content',
  )
  expect(screen.queryByText(/session running/)).toBeNull()
  expect(screen.getByRole('link', { name: 'Resume or manage session' })).toHaveAttribute('href', '/')
})
it('updates titles and focus after navigation and marks only the exact current route', () => {
  renderApp(
    <Shell>
      <h1>Content</h1>
    </Shell>,
  )
  fireEvent.click(screen.getByRole('link', { name: 'Audio visualizer' }))
  expect(document.title).toBe('Audio visualizer · AuDHS Tutor')
  expect(screen.getByRole('link', { name: 'Audio visualizer' })).toHaveAttribute('aria-current', 'page')
  expect(screen.getByRole('link', { name: 'Playground' })).not.toHaveAttribute('aria-current')
  expect(screen.getByRole('main')).toHaveFocus()
})

it('recognizes a valid trailing-slash route title', () => {
  renderApp(
    <Shell>
      <h1>Review content</h1>
    </Shell>,
    { route: '/review/' },
  )
  expect(document.title).toBe('Review · AuDHS Tutor')
})
