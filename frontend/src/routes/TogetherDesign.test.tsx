import { act, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { renderApp } from '../test/utils'
import { Together } from './Together'
import { useComfort } from '../features/sensory/comfortStore'
import { useGenerationActivity } from '../features/sensory/generationActivity'
vi.mock('../features/sensory/useSensory', () => ({ useSensory: () => ({ ambient: 'off', motion: 'off' }) }))
vi.mock('../features/session/api', () => ({ useCurrentSession: () => ({ data: null }), routeForPhase: () => '/' }))
vi.mock('../features/audio/AudioControls', () => ({ AudioControls: () => null }))
afterEach(() => {
  useComfort.setState({ breakDesign: 'off' })
  useGenerationActivity.setState({ count: 0 })
})
it('unmounts the design while generating and when inactive or embedded', async () => {
  useComfort.setState({ breakDesign: 'liquid' })
  const view = renderApp(<Together />)
  await screen.findByRole('button', { name: 'Change pattern' })
  act(() => useGenerationActivity.setState({ count: 1 }))
  expect(screen.queryByRole('button', { name: 'Change pattern' })).not.toBeInTheDocument()
  expect(screen.getByRole('status')).toHaveTextContent('Design paused')
  act(() => useGenerationActivity.setState({ count: 0 }))
  await screen.findByRole('button', { name: 'Change pattern' })
  view.rerender(<Together active={false} />)
  await waitFor(() => expect(screen.queryByRole('button', { name: 'Change pattern' })).not.toBeInTheDocument())
  view.rerender(<Together embedded />)
  expect(screen.queryByLabelText('Break design')).not.toBeInTheDocument()
})
