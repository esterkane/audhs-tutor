import { expect, it } from 'vitest'
import { initial } from './engine'
import { createWorkspaceCheckpointStore, WORKSPACE_KEY, type WorkspaceCheckpoint } from './workspaceCheckpoint'
const fixture = (): WorkspaceCheckpoint => ({ version: 1, preset: initial, history: { text: '{unfinished', past: [JSON.stringify(initial)], future: [] }, view: 'Create', renderer: 'graph', savedId: null })
it('restores unfinished text separately from validated applied graph and undo history', () => {
  const store = createWorkspaceCheckpointStore(() => localStorage)
  expect(store.write(fixture())).toBe(true)
  expect(createWorkspaceCheckpointStore(() => localStorage).read()).toEqual(fixture())
})
it('keeps memory on quota failure and retries storage later', () => {
  let denied = true
  const store = createWorkspaceCheckpointStore(() => ({ getItem: () => null, setItem: (key, value) => { if (denied) throw Error('quota'); localStorage.setItem(key, value) } }))
  expect(store.write(fixture())).toBe(false)
  expect(store.read()).toEqual(fixture())
  denied = false
  expect(store.write(fixture())).toBe(true)
})
it.each(['{"version":99}', '{broken', JSON.stringify({ ...fixture(), history: { text: '', past: ['invalid'], future: [] } })])('preserves unsupported stored data: %s', raw => {
  localStorage.setItem(WORKSPACE_KEY, raw)
  const store = createWorkspaceCheckpointStore(() => localStorage)
  expect(store.read()).toBeNull()
  expect(store.write(fixture())).toBe(false)
  expect(localStorage.getItem(WORKSPACE_KEY)).toBe(raw)
  expect(store.read()).toEqual(fixture())
})
it('handles unavailable storage while retaining a tab checkpoint', () => {
  const store = createWorkspaceCheckpointStore(() => { throw Error('denied') })
  expect(store.read()).toBeNull()
  expect(store.write(fixture())).toBe(false)
  expect(store.read()).toEqual(fixture())
})
