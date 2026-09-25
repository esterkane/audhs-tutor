/**
 * Runner interface for the exercise sandbox. The real implementation drives the Pyodide worker
 * (`pyodide.worker.js`): the main thread owns the timeout (terminate + recreate the worker) so an
 * infinite loop cannot hang the page; output is capped inside the worker. Tests inject a fake.
 */
export type Check = { name: string; criterion: string; code: string }
export type CheckResult = { name: string; passed: boolean; detail: string }
export type RunResult = {
  stdout: string
  truncated: boolean
  error: string | null
  results: CheckResult[]
  timedOut: boolean
  ms: number
}
export type Runner = {
  load(packages: string[]): Promise<void>
  run(
    code: string,
    checks: Check[],
    opts: { timeoutMs: number; maxOutputChars: number; packages: string[] },
  ): Promise<RunResult>
  dispose(): void
}

export function createPyodideRunner(): Runner {
  let worker: Worker | null = null
  let ready: Promise<void> | null = null
  let cancelLoad: (() => void) | null = null
  let cancelRun: (() => void) | null = null
  let generation = 0
  let running = false

  function spawn(): Worker {
    return new Worker(new URL('./pyodide.worker.js', import.meta.url), { type: 'classic' })
  }

  function load(packages: string[]): Promise<void> {
    if (ready) return ready
    worker = worker ?? spawn()
    const w = worker
    ready = new Promise<void>((resolve, reject) => {
      let settled = false
      const settle = () => {
        settled = true
        cancelLoad = null
        w.removeEventListener('message', onMsg)
        w.removeEventListener('error', onErr)
      }
      // a failed load discards this worker: the next Run starts a fresh one, so installing the
      // runtime and clicking "Try loading the runtime again" can succeed without a reload
      const fail = (message: string) => {
        if (settled) return
        settle()
        w.terminate()
        worker = null
        ready = null
        reject(new Error(message))
      }
      const onMsg = (ev: MessageEvent) => {
        if (ev.data?.type === 'ready') {
          settle()
          resolve()
        } else if (ev.data?.type === 'load_error') {
          fail(ev.data.message)
        }
      }
      const onErr = (e: ErrorEvent) => fail(e.message || 'worker failed')
      cancelLoad = () => fail('Runtime loading was stopped.')
      w.addEventListener('message', onMsg)
      w.addEventListener('error', onErr)
      w.postMessage({ type: 'load', packages })
    })
    return ready
  }

  return {
    load,
    async run(code, checks, opts) {
      if (running) throw new Error('A code run is already in progress.')
      running = true
      const startedGeneration = generation
      try {
        await load(opts.packages)
        if (generation !== startedGeneration || !worker) throw new Error('Code execution was stopped.')
        const w = worker
        const t0 = performance.now()
        return await new Promise<RunResult>((resolve) => {
          let done = false
          const finish = (result: Partial<RunResult>, discard = false) => {
            if (done) return
            done = true
            clearTimeout(timer)
            w.removeEventListener('message', onMsg)
            w.removeEventListener('error', onErr)
            cancelRun = null
            if (discard) {
              w.terminate()
              worker = null
              ready = null
            }
            resolve({
              stdout: '',
              truncated: false,
              error: null,
              results: [],
              timedOut: false,
              ms: Math.round(performance.now() - t0),
              ...result,
            })
          }
          const timer = setTimeout(
            () =>
              finish(
                {
                  error: `Stopped after ${Math.round(opts.timeoutMs / 1000)} s — the code did not finish (infinite loop?).`,
                  timedOut: true,
                },
                true,
              ),
            opts.timeoutMs,
          )
          const onErr = (e: ErrorEvent) =>
            finish({ error: `The runtime crashed: ${e.message || 'unknown error'}` }, true)
          const onMsg = (ev: MessageEvent) => {
            if (ev.data?.type !== 'result') return
            finish({
              stdout: ev.data.stdout ?? '',
              truncated: !!ev.data.truncated,
              error: ev.data.error ?? null,
              results: ev.data.results ?? [],
            })
          }
          cancelRun = () => finish({ error: 'Code execution was stopped.' }, true)
          w.addEventListener('message', onMsg)
          w.addEventListener('error', onErr)
          try {
            w.postMessage({
              type: 'run',
              code,
              checks,
              maxOutputChars: opts.maxOutputChars,
              packages: opts.packages,
            })
          } catch (e) {
            finish({ error: `Could not start code execution: ${String(e)}` }, true)
          }
        })
      } finally {
        running = false
      }
    },
    dispose() {
      generation += 1
      cancelLoad?.()
      cancelRun?.()
      worker?.terminate()
      worker = null
      ready = null
    },
  }
}
