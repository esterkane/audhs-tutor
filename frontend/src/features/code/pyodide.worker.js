/* Pyodide sandbox worker (P8). Classic worker: importScripts loads the runtime from this app's
   own origin (`/pyodide/`, installed once by `make pyodide`, pinned version — ADR-0013: never a
   CDN, no silent fallback). Policy: after the runtime (and the exercise's packages) are loaded,
   network APIs are removed so learner/model code cannot reach anything; the filesystem is Pyodide's
   in-memory one; the main thread enforces the timeout by terminating this worker; stdout is capped
   here. */
/* global loadPyodide */
const PYODIDE_VERSION = '0.27.8'
const INDEX_URL = new URL('/pyodide/', self.location.href).href

let pyodide = null
let loading = null

async function ensure(packages) {
  if (!loading) {
    loading = (async () => {
      if (!(packages || []).every((p) => /^[A-Za-z0-9_.-]+$/.test(p)))
        throw new Error('package names only: the sandbox never loads packages from URLs')
      try {
        importScripts(INDEX_URL + 'pyodide.js')
      } catch (e) {
        throw new Error(
          `The Python runtime is not installed in this app (${INDEX_URL}pyodide.js could not be ` +
            'loaded). Run `make pyodide` once on the machine that serves the app — nothing is ' +
            `fetched from a CDN. (${e && e.message ? e.message : e})`,
        )
      }
      const py = await loadPyodide({ indexURL: INDEX_URL })
      if (py.version !== PYODIDE_VERSION)
        throw new Error(`Installed Python runtime is ${py.version}, expected ${PYODIDE_VERSION}`)
      if (packages && packages.length) await py.loadPackage(packages)
      // Best-effort lockdown once the runtime is loaded: remove the browser's network entry points
      // on the global *and* its prototype and freeze them, so `js.WorkerGlobalScope.prototype.fetch`
      // from Python finds nothing either. The real boundary stays the browser's worker sandbox.
      const blocked = () => {
        throw new Error('network access is disabled in the exercise sandbox')
      }
      const lock = (obj, name, value) => {
        try {
          Object.defineProperty(obj, name, { value, writable: false, configurable: false })
        } catch (e) {
          /* already locked */
        }
      }
      for (const target of [self, WorkerGlobalScope.prototype]) {
        lock(target, 'fetch', () =>
          Promise.reject(new Error('network access is disabled in the exercise sandbox')),
        )
        lock(target, 'importScripts', blocked)
        for (const name of [
          'XMLHttpRequest',
          'WebSocket',
          'EventSource',
          'Worker',
          'SharedWorker',
          'caches',
          'indexedDB',
        ])
          lock(target, name, undefined)
      }
      return py
    })().catch((e) => {
      loading = null // a failed load is not memoised: the next attempt starts over
      throw e
    })
  }
  pyodide = await loading
  return pyodide
}

self.onmessage = async (ev) => {
  const msg = ev.data
  if (msg.type === 'load') {
    try {
      await ensure(msg.packages || [])
      self.postMessage({ type: 'ready' })
    } catch (e) {
      self.postMessage({ type: 'load_error', message: String(e && e.message ? e.message : e) })
    }
    return
  }
  if (msg.type !== 'run') return
  const cap = msg.maxOutputChars || 20000
  let out = ''
  let truncated = false
  const write = (s) => {
    if (truncated) return
    if (out.length + s.length > cap) {
      out += s.slice(0, Math.max(0, cap - out.length))
      truncated = true
      return
    }
    out += s
  }
  try {
    const py = await ensure(msg.packages || [])
    py.setStdout({ batched: (s) => write(s + '\n') })
    py.setStderr({ batched: (s) => write(s + '\n') })
    const ns = py.globals.get('dict')()
    let error = null
    try {
      await py.runPythonAsync(msg.code, { globals: ns })
    } catch (e) {
      error = String(e && e.message ? e.message : e).slice(-2000)
    }
    const results = []
    if (!error) {
      for (const check of msg.checks || []) {
        try {
          await py.runPythonAsync(check.code, { globals: ns })
          results.push({ name: check.name, passed: true, detail: 'passed' })
        } catch (e) {
          const text = String(e && e.message ? e.message : e)
          const last = text.trim().split('\n').slice(-1)[0] || text
          results.push({ name: check.name, passed: false, detail: last.slice(0, 300) })
        }
      }
    }
    ns.destroy()
    self.postMessage({ type: 'result', stdout: out, truncated, error, results })
  } catch (e) {
    self.postMessage({
      type: 'result',
      stdout: out,
      truncated,
      error: String(e && e.message ? e.message : e),
      results: [],
    })
  }
}
