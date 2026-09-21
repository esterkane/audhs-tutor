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

  function spawn(): Worker {
    return new Worker(new URL('./pyodide.worker.js', import.meta.url), { type: 'classic' })
  }

  function load(packages: string[]): Promise<void> {
    if (ready) return ready
    worker = worker ?? spawn()
    const w = worker
    ready = new Promise<void>((resolve, reject) => {
      const onMsg = (ev: MessageEvent) => {
        if (ev.data?.type === 'ready') {
          w.removeEventListener('message', onMsg)
          resolve()
        } else if (ev.data?.type === 'load_error') {
          w.removeEventListener('message', onMsg)
          ready = null
          reject(new Error(ev.data.message))
        }
      }
      w.addEventListener('message', onMsg)
      w.addEventListener('error', (e) => {
        ready = null
        reject(new Error(e.message || 'worker failed'))
      })
      w.postMessage({ type: 'load', packages })
    })
    return ready
  }

  return {
    load,
    async run(code, checks, opts) {
      await load(opts.packages)
      const w = worker!
      const t0 = performance.now()
      return new Promise<RunResult>((resolve) => {
        let done = false
        const timer = setTimeout(() => {
          if (done) return
          done = true
          // the only way to stop a busy WebAssembly thread: kill it and start fresh next time
          w.terminate()
          worker = null
          ready = null
          resolve({
            stdout: '',
            truncated: false,
            error: `Stopped after ${Math.round(opts.timeoutMs / 1000)} s — the code did not finish (infinite loop?).`,
            results: [],
            timedOut: true,
            ms: Math.round(performance.now() - t0),
          })
        }, opts.timeoutMs)
        const onErr = (e: ErrorEvent) => {
          if (done) return
          done = true
          clearTimeout(timer)
          w.removeEventListener('message', onMsg)
          w.removeEventListener('error', onErr)
          resolve({
            stdout: '',
            truncated: false,
            error: `The runtime crashed: ${e.message || 'unknown error'}`,
            results: [],
            timedOut: false,
            ms: Math.round(performance.now() - t0),
          })
        }
        const onMsg = (ev: MessageEvent) => {
          if (ev.data?.type !== 'result' || done) return
          done = true
          clearTimeout(timer)
          w.removeEventListener('message', onMsg)
          w.removeEventListener('error', onErr)
          resolve({
            stdout: ev.data.stdout ?? '',
            truncated: !!ev.data.truncated,
            error: ev.data.error ?? null,
            results: ev.data.results ?? [],
            timedOut: false,
            ms: Math.round(performance.now() - t0),
          })
        }
        w.addEventListener('message', onMsg)
        w.postMessage({
          type: 'run',
          code,
          checks,
          maxOutputChars: opts.maxOutputChars,
          packages: opts.packages,
        })
      })
    },
    dispose() {
      worker?.terminate()
      worker = null
      ready = null
    },
  }
}
