import { screen, waitFor } from '@testing-library/react'
import { render } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { SoftTimer } from './SoftTimer'

describe('SoftTimer', () => {
  it('derives the deadline from the server start time and hides again when an extension arrives', async () => {
    const startedAt = new Date(Date.now() - 12 * 60_000).toISOString()
    const onExtend = vi.fn()
    const { rerender } = render(
      <SoftTimer
        blockKey="s1:2"
        startedAt={startedAt}
        plannedMin={10}
        extensionMin={0}
        onExtend={onExtend}
        onSaveStop={() => {}}
        onFinishBlock={() => {}}
      />,
    )
    expect(await screen.findByText(/Planned time is up \(10 min\)/)).toBeInTheDocument()
    screen.getByRole('button', { name: /5 more minutes/i }).click()
    expect(onExtend).toHaveBeenCalledWith(5)
    // the server confirms the extension: 12 min elapsed < 15 planned → the prompt disappears
    rerender(
      <SoftTimer
        blockKey="s1:2"
        startedAt={startedAt}
        plannedMin={10}
        extensionMin={5}
        onExtend={onExtend}
        onSaveStop={() => {}}
        onFinishBlock={() => {}}
      />,
    )
    await waitFor(() => expect(screen.queryByText(/Planned time is up/)).not.toBeInTheDocument())
    // a new block key with a fresh start time shows nothing
    rerender(
      <SoftTimer
        key="s1:3"
        blockKey="s1:3"
        startedAt={new Date().toISOString()}
        plannedMin={10}
        onExtend={onExtend}
        onSaveStop={() => {}}
        onFinishBlock={() => {}}
      />,
    )
    await waitFor(() => expect(screen.queryByText(/Planned time is up/)).not.toBeInTheDocument())
  })
})
