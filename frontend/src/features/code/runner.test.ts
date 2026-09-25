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
  it('reports a run crash immediately and clears its listeners', async () => {
    vi.stubGlobal('Worker', FakeWorker)
    FakeWorker.script = (w, msg) => {
      if (msg.type === 'load') w.emit({ type: 'ready' })
      else for (const fn of w.listeners.error ?? []) fn({ message: 'crash' })
    }
    const runner = createPyodideRunner()
    const result = await runner.run('pass', [], { timeoutMs: 30, maxOutputChars: 100, packages: [] })
    expect(result.timedOut).toBe(false)
    expect(result.error).toContain('crash')
    expect(FakeWorker.instances[0].listeners.error).toHaveLength(0)
    expect(FakeWorker.instances[0].listeners.message).toHaveLength(0)
    runner.dispose()
  })
  it('settles disposal during loading and permits a new worker on retry', async () => {
    vi.stubGlobal('Worker', FakeWorker)
    FakeWorker.script = () => {}
    const runner = createPyodideRunner()
    const loading = runner.load([])
    const stopped = expect(loading).rejects.toThrow('stopped')
    runner.dispose()
    await stopped
    expect(FakeWorker.instances[0].listeners.message).toHaveLength(0)
    FakeWorker.script = (w) => w.emit({ type: 'ready' })
    await runner.load([])
    runner.dispose()
  })

  it('settles disposal during a run, rejects concurrent runs and releases listeners', async () => {
    vi.stubGlobal('Worker', FakeWorker)
    FakeWorker.script = (w, msg) => {
      if (msg.type === 'load') w.emit({ type: 'ready' })
    }
    const runner = createPyodideRunner()
    await runner.load([])
    const opts = { timeoutMs: 10000, maxOutputChars: 100, packages: [] }
    const first = runner.run('pass', [], opts)
    await expect(runner.run('pass', [], opts)).rejects.toThrow('already in progress')
    runner.dispose()
    await expect(first).resolves.toMatchObject({ timedOut: false, error: 'Code execution was stopped.' })
    expect(FakeWorker.instances[0].listeners.message).toHaveLength(0)
    expect(FakeWorker.instances[0].listeners.error).toHaveLength(0)
  })

  it('cleans up timed-out runs and succeeds on a new worker', async () => {
    vi.stubGlobal('Worker', FakeWorker)
    FakeWorker.script = (w, msg) => {
      if (msg.type === 'load') w.emit({ type: 'ready' })
    }
    const runner = createPyodideRunner()
    const opts = { timeoutMs: 5, maxOutputChars: 100, packages: [] }
    await expect(runner.run('while True: pass', [], opts)).resolves.toMatchObject({ timedOut: true })
    expect(FakeWorker.instances[0].listeners.message).toHaveLength(0)
    FakeWorker.script = (w, msg) =>
      w.emit(msg.type === 'load' ? { type: 'ready' } : { type: 'result', stdout: 'ok' })
    await expect(runner.run('print("ok")', [], opts)).resolves.toMatchObject({ stdout: 'ok', error: null })
    expect(FakeWorker.instances).toHaveLength(2)
    runner.dispose()
  })
})
