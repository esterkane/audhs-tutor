import { fireEvent, screen, within } from '@testing-library/react'
import { expect, it, vi } from 'vitest'
import { Shell } from './App'
import { renderApp } from '../test/utils'
import { useMode } from '../stores/mode'
vi.mock('../features/areas/BrowseArea', () => ({ BrowseArea: () => null }))
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
  expect(screen.queryByRole('link', { name: 'Resume or manage session' })).toBeNull()
  expect(screen.queryByRole('link', { name: 'Start or resume' })).toBeNull()
  expect(useMode.getState().sessionId).toBe('remembered-id')
})
it('updates titles and focus after primary navigation', () => {
  renderApp(<Shell><h1>Content</h1></Shell>)
  fireEvent.click(screen.getByRole('link', { name: 'Progress' }))
  expect(document.title).toBe('Progress · AuDHS Tutor')
  expect(screen.getByRole('link', { name: 'Progress' })).toHaveAttribute('aria-current', 'page')
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

it('keeps supported tools and focused projects available without changing learning state', () => {
  useMode.setState({ sessionId: 'kept', skillId: 'kept-skill' })
  renderApp(<Shell><h1>Content</h1></Shell>)
  fireEvent.click(screen.getByRole('button', { name: 'Tools' }))
  const tools = within(screen.getByRole('dialog', { name: 'Tools and pages' }))
  const destinations = {
    Review: '/review', Vocabulary: '/vocab', 'Work alongside': '/together',
    'Skill map': '/map',
    'Saved answers': '/answers', Playground: '/playground',
    Materials: '/corpus', 'Knowledge material': '/curriculum', Models: '/models',
    Experiments: '/experiments', Preferences: '/preferences',
  }
  for (const [name, href] of Object.entries(destinations)) {
    expect(tools.getByRole('link', { name })).toHaveAttribute('href', href)
  }
  expect(screen.getByRole('link', { name: 'Projects' })).toHaveAttribute('href', '/projects')
  expect(tools.queryByRole('link', { name: 'Audio visualizer' })).toBeNull()
  expect(tools.queryByRole('link', { name: /guitar/i })).toBeNull()
  expect(useMode.getState().sessionId).toBe('kept')
  expect(useMode.getState().skillId).toBe('kept-skill')
})
