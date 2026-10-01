import { beforeEach, describe, expect, it } from 'vitest'
import { useMode } from './mode'

describe('mode store', () => {
  beforeEach(() =>
    useMode.setState({
      mode: 'steady',
      energy: 3,
      socratic: false,
      sessionId: null,
      skillId: null,
    }),
  )

  it('defaults to explicit, steady, energy 3 and never switches on its own', () => {
    const s = useMode.getState()
    expect(s.mode).toBe('steady')
    expect(s.socratic).toBe(false)
    expect(s.energy).toBe(3)
  })

  it('only changes through explicit setters', () => {
    useMode.getState().setMode('low_capacity')
    useMode.getState().setEnergy(1)
    useMode.getState().setSession('s1', 'k1')
    expect(useMode.getState()).toMatchObject({
      mode: 'low_capacity',
      energy: 1,
      sessionId: 's1',
      skillId: 'k1',
    })
    useMode.getState().reset()
    expect(useMode.getState().sessionId).toBeNull()
    expect(useMode.getState().mode).toBe('low_capacity') // preferences survive a session reset
  })
})
