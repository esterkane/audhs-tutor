import { afterEach, describe, expect, it, vi } from 'vitest'
import { createPyodideRunner } from './runner'

/**
 * A failed runtime load must not poison later attempts: after `make pyodide` the learner clicks
 * "Try loading the runtime again" and the runner has to start a fresh worker instead of re-asking
 * one whose load already failed.
 */
class FakeWorker {
  static instances: FakeWorker[] = []
  static script: (w: FakeWorker, msg: { type: string }) => void = () => {}
  listeners: Record<string, ((ev: unknown) => void)[]> = {}
  terminated = false
  constructor() {
    FakeWorker.instances.push(this)
  }
  addEventListener(type: string, fn: (ev: unknown) => void) {
    ;(this.listeners[type] ??= []).push(fn)
  }
  removeEventListener(type: string, fn: (ev: unknown) => void) {
    this.listeners[type] = (this.listeners[type] ?? []).filter((f) => f !== fn)
  }
  postMessage(msg: { type: string }) {
    queueMicrotask(() => FakeWorker.script(this, msg))
  }
  emit(data: unknown) {
    for (const fn of this.listeners.message ?? []) fn({ data })
  }
  terminate() {
    this.terminated = true
  }
}

describe('createPyodideRunner', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    FakeWorker.instances = []
  })

  it('discards a worker whose load failed and succeeds with a fresh one on retry', async () => {
    vi.stubGlobal('Worker', FakeWorker)
    let attempt = 0
    FakeWorker.script = (w, msg) => {
      if (msg.type !== 'load') return
      attempt += 1
      w.emit(attempt === 1 ? { type: 'load_error', message: 'not installed' } : { type: 'ready' })
    }
    const runner = createPyodideRunner()
    await expect(runner.load(['numpy'])).rejects.toThrow('not installed')
    expect(FakeWorker.instances).toHaveLength(1)
    expect(FakeWorker.instances[0].terminated).toBe(true)
    await expect(runner.load(['numpy'])).resolves.toBeUndefined()
    expect(FakeWorker.instances).toHaveLength(2)
    expect(FakeWorker.instances[1].terminated).toBe(false)
    // no stale listeners remain on the live worker after a successful load
    expect(FakeWorker.instances[1].listeners.error ?? []).toHaveLength(0)
    runner.dispose()
  })
})
