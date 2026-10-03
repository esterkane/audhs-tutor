import { useQueryClient } from '@tanstack/react-query'
import { act, fireEvent, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { jsonResponse, renderApp } from '../test/utils'
import { Together } from './Together'
import { claimReading, useReadingControls } from '../features/voice/readingOwner'
vi.mock('../features/audio/settings', async (original) => ({
  ...(await original<object>()),
  bindOutput: () => vi.fn(),
}))

describe('Together', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('shows the current task and offers ambient sound only when the preference allows it', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string) => {
        if (url.endsWith('/api/sessions/current'))
          return jsonResponse({
            id: 's1',
            mode: 'steady',
            energy: 3,
            active_skill: { id: 'k', title: 'Softmax' },
            next_skill: { id: 'other', title: 'Next recommendation' },
            state: { phase: 'review', block_status: 'running', plan_complete: false },
          })
        if (url.endsWith('/api/preferences'))
          return jsonResponse({ values: { 'ui.ambient': 'off' }, specs: [] })
        return jsonResponse({})
      }),
    )
    renderApp(<Together />)
    expect(await screen.findByText('Now: Softmax')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /brown noise/i })).not.toBeInTheDocument()
    expect(screen.getByText(/not a live human companion/)).toBeInTheDocument()
    expect(screen.queryByText(/Next recommendation/)).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Back to the session' })).toHaveAttribute('href', '/review')
  })
})

describe('Together audio ownership', () => {
  afterEach(() => {
    claimReading(() => {})()
    vi.unstubAllGlobals()
  })
  function setup() {
    const instances: {
      stop: ReturnType<typeof vi.fn>
      close: ReturnType<typeof vi.fn<() => Promise<void>>>
      resolve: () => void
      reject: () => void
    }[] = []
    vi.stubGlobal(
      'AudioContext',
      class {
        sampleRate = 8
        destination = {}
        state =
          instances.push({
            stop: vi.fn(),
            close: vi.fn(async () => {}),
            resolve: () => {},
            reject: () => {},
          }) - 1
        createBuffer() {
          return { getChannelData: () => new Float32Array(32) }
        }
        createBufferSource() {
          return { connect: (gain: unknown) => gain, start: vi.fn(), stop: instances[this.state].stop }
        }
        createGain() {
          return { connect: vi.fn() }
        }
        resume() {
          return new Promise<void>((resolve, reject) => {
            instances[this.state].resolve = resolve
            instances[this.state].reject = () => reject(new Error('blocked'))
          })
        }
        close() {
          return instances[this.state].close()
        }
      },
    )
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string) =>
        jsonResponse(
          url.endsWith('/api/preferences') ? { values: { 'ui.ambient': 'brown' }, specs: [] } : null,
        ),
      ),
    )
    return instances
  }
  it('claims only on play, stops for replacement and resumes only by explicit play', async () => {
    const instances = setup()
    renderApp(<Together />)
    const previous = vi.fn()
    const release = claimReading(previous, 'reading')
    fireEvent.click(await screen.findByRole('button', { name: 'Play brown noise' }))
    expect(previous).toHaveBeenCalledWith('brown noise')
    expect(useReadingControls.getState().reading?.kind).toBe('ambient')
    act(() => {
      claimReading(() => {}, 'another reading')()
    })
    expect(instances[0].stop).toHaveBeenCalledOnce()
    expect(screen.getByText(/Brown noise stopped for another reading/)).toBeInTheDocument()
    expect(instances).toHaveLength(1)
    release()
    fireEvent.click(screen.getByRole('button', { name: 'Play brown noise' }))
    await act(async () => {
      instances[0].reject()
      instances[1].resolve()
    })
    expect(instances[1].stop).not.toHaveBeenCalled()
    expect(useReadingControls.getState().reading?.status).toBe('Playing brown noise')
    act(() => useReadingControls.getState().reading?.stop())
    expect(instances[1].stop).toHaveBeenCalledOnce()
    expect(useReadingControls.getState().reading).toBeNull()
  })
  it('stops and releases when the ambient preference is turned off', async () => {
    const instances = setup()
    function PreferenceSwitch() {
      const query = useQueryClient()
      return (
        <button
          onClick={() => query.setQueryData(['preferences'], { values: { 'ui.ambient': 'off' }, specs: [] })}
        >
          Disable ambient
        </button>
      )
    }
    renderApp(
      <>
        <Together />
        <PreferenceSwitch />
      </>,
    )
    fireEvent.click(await screen.findByRole('button', { name: 'Play brown noise' }))
    fireEvent.click(screen.getByRole('button', { name: 'Disable ambient' }))
    await screen.findByText(/Ambient sound can be enabled/)
    expect(instances[0].stop).toHaveBeenCalledOnce()
    expect(useReadingControls.getState().reading).toBeNull()
  })
  it('releases ownership on current resume failure and unmount', async () => {
    const instances = setup()
    const view = renderApp(<Together />)
    fireEvent.click(await screen.findByRole('button', { name: 'Play brown noise' }))
    await act(async () => {
      instances[0].reject()
    })
    expect(useReadingControls.getState().reading).toBeNull()
    expect(screen.getByText(/could not start/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Play brown noise' }))
    view.unmount()
    expect(instances[1].stop).toHaveBeenCalledOnce()
    expect(instances[1].close).toHaveBeenCalledOnce()
    expect(useReadingControls.getState().reading).toBeNull()
  })
})
