import { AudioControls } from '../features/audio/AudioControls'
import { lazy, Suspense, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { Button } from '../components/ui/button'
import { Card, CardTitle } from '../components/ui/card'
import { useSensory } from '../features/sensory/useSensory'
import { useMode } from '../stores/mode'
import { openAudio, type AudioInput } from '../features/visualizer/audio'
import { demoFrame, evaluate, parsePreset, type Frame, type Preset } from '../features/visualizer/engine'
import { draw } from '../features/visualizer/render'

import { AudioLessons } from '../features/visualizer/AudioLessons'
import { LiveMeasurement } from '../features/visualizer/LiveMeasurement'
import type { Measurement } from '../features/visualizer/measurement'
import { openTone, type ToneSettings } from '../features/visualizer/tone'
import { BlockAuthoring } from '../features/visualizer/BlockAuthoring'
import { readPresetFile } from '../features/visualizer/authoring'
import { useDraftHistory } from '../features/visualizer/useDraftHistory'
import { PresetControls } from '../features/visualizer/PresetControls'
import { examples } from '../features/visualizer/examples'
import { RepeatSection } from '../features/visualizer/RepeatSection'
import { AudioWaveform } from '../features/visualizer/AudioWaveform'
import { SampleTrace } from '../features/visualizer/SampleTrace'
import { ConnectionEditor } from '../features/visualizer/ConnectionEditor'
import { SignalFlow } from '../features/visualizer/SignalFlow'
import { BlockExplanation } from '../features/visualizer/BlockExplanation'

import { RendererBoundary } from '../features/visualizer/RendererBoundary'
import { PresetLibrary } from '../features/visualizer/PresetLibrary'
import { restoredPreset, readLibrary, writeLibrary } from '../features/visualizer/library'
const Milkdrop = lazy(() => import('../features/visualizer/Milkdrop'))
const EMPTY: Frame = { bass: 0, mid: 0, treble: 0, rms: 0 }
export function Visualizer() {
  const [savedId, setSavedId] = useState<string | null>(() => {
    try {
      return readLibrary(localStorage).active
    } catch {
      return null
    }
  })
  const [renderer, setRenderer] = useState<'graph' | 'milkdrop'>('graph')
  const [richPreset, setRichPreset] = useState(0)
  const [richError, setRichError] = useState('')
  const [collectionVersion, setCollectionVersion] = useState(0)
  const [view, setView] = useState<'Watch' | 'Learn' | 'Create'>('Watch')
  const [preset, setPreset] = useState(restoredPreset)
  const history = useDraftHistory(JSON.stringify(preset, null, 2))
  const { text, change: setText } = history
  const [importDraft, setImportDraft] = useState<Preset | null>(null)
  const [importError, setImportError] = useState('')
  const importGeneration = useRef(0)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [source, setSource] = useState<'demo' | 'file' | 'lesson'>('demo')
  const [running, setRunning] = useState(false)
  const [position, setPosition] = useState({ seconds: 0, duration: 0 })
  const [repeat, setRepeat] = useState<{ start: number; end: number } | null>(null)
  const [paused, setPaused] = useState(false)
  const [finished, setFinished] = useState(false)
  const [starting, setStarting] = useState(false)
  const [audible, setAudible] = useState(false)
  const [measurement, setMeasurement] = useState<Measurement | null>(null)
  const [snapshotMeasurement, setSnapshotMeasurement] = useState<Measurement | null>(null)
  const [frame, setFrame] = useState<Frame>(EMPTY)
  const [sampleNumber, setSampleNumber] = useState(0)
  const [output, setOutput] = useState(() => evaluate(preset, EMPTY, 0, 0, new Map()))
  const [inspectId, setInspectId] = useState('')
  const draftPreset = useMemo(() => {
    try {
      return parsePreset(text)
    } catch {
      return null
    }
  }, [text])
  const draftChanged = draftPreset ? JSON.stringify(draftPreset) !== JSON.stringify(preset) : true
  const { reduced, sound } = useSensory()
  const energy = useMode((s) => s.energy)
  const canvas = useRef<HTMLCanvasElement>(null)
  const stage = useRef<HTMLDivElement>(null)
  const audioPicker = useRef<HTMLInputElement>(null)
  const [fullscreen, setFullscreen] = useState(false)
  const latestFrame = useRef(EMPTY)
  const appearance = draftPreset?.visual ?? preset.visual
  const displayedPreset = useMemo(
    () => ({ ...preset, visual: { ...preset.visual, kind: appearance.kind, color: appearance.color } }),
    [preset, appearance.kind, appearance.color],
  )
  const input = useRef<AudioInput | null>(null)
  const [visualInput, setVisualInput] = useState<AudioInput | null>(null)
  const abort = useRef<AbortController | null>(null)
  const previousAudio = useRef<{
    input: AudioInput | null
    abort: AbortController | null
    source: 'demo' | 'file'
    time: number
    audible: boolean
    repeat: { start: number; end: number } | null
  } | null>(null)
  const releasePrevious = () => {
    previousAudio.current?.abort?.abort()
    previousAudio.current?.input?.stop()
    previousAudio.current = null
  }

  const effectiveSound = useRef(false)
  const time = useRef(0)
  const memory = useRef(new Map<string, number>())
  const stop = useCallback(() => {
    abort.current?.abort()
    abort.current = null
    input.current?.stop()
    input.current = null
    setVisualInput(null)
    setRunning(false)
    setPaused(false)
    setRepeat(null)
    setStarting(false)
    setMeasurement(null)
    setSnapshotMeasurement(null)
  }, [])
  const paint = useCallback(
    (f: Frame, t: number, dt: number, render = true) => {
      const out = evaluate(preset, f, t, dt, memory.current)
      latestFrame.current = f
      if (render && canvas.current) draw(canvas.current, displayedPreset, out.scale, out.energy)
      return out
    },
    [preset, displayedPreset],
  )
  useEffect(() => {
    paint(latestFrame.current, time.current, 0)
  }, [paint])
  useEffect(() => {
    const element = canvas.current
    if (!element) return
    const resize = () => {
      const bounds = element.getBoundingClientRect()
      const ratio = Math.min(window.devicePixelRatio || 1, 2)
      element.width = Math.max(1, Math.round(bounds.width * ratio))
      element.height = Math.max(1, Math.round(bounds.height * ratio))
      paint(latestFrame.current, time.current, 0)
    }
    const observer = new ResizeObserver(resize)
    observer.observe(element)
    const changed = () => setFullscreen(document.fullscreenElement === stage.current)
    document.addEventListener('fullscreenchange', changed)
    resize()
    return () => {
      observer.disconnect()
      document.removeEventListener('fullscreenchange', changed)
    }
  }, [paint])
  useEffect(() => {
    effectiveSound.current = audible && sound
    input.current?.setAudible(effectiveSound.current)
  }, [audible, sound])
  useEffect(() => {
    const onHidden = () => {
      if (document.hidden) {
        input.current?.pause?.()
        setRunning((wasRunning) => {
          if (wasRunning) setPaused(true)
          return false
        })
      }
    }
    document.addEventListener('visibilitychange', onHidden)
    return () => {
      document.removeEventListener('visibilitychange', onHidden)
      abort.current?.abort()
      input.current?.stop()
      previousAudio.current?.abort?.abort()
      previousAudio.current?.input?.stop()
    }
  }, [stop])
  useEffect(() => {
    if (!running) return
    let raf = 0
    let previous = 0
    let lastUi = 0
    function tick(now: number) {
      const dt = previous ? Math.min((now - previous) / 1000, 0.1) : 1 / 60
      previous = now
      time.current =
        source === 'file' ? (input.current?.position?.().seconds ?? time.current + dt) : time.current + dt
      const f = source === 'demo' ? demoFrame(time.current) : (input.current?.read() ?? EMPTY)
      const result = paint(f, time.current, dt, !reduced)
      if (now - lastUi > 250) {
        setFrame(f)
        setMeasurement(input.current?.measurement?.() ?? null)
        setOutput(result)
        lastUi = now
      }
      raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [running, reduced, source, paint])

  useEffect(() => {
    if (!running || source !== 'file') return
    const timer = window.setInterval(() => {
      const value = input.current?.position?.()
      if (value) setPosition(value)
    }, 500)
    return () => window.clearInterval(timer)
  }, [running, source])

  function pausePlayback() {
    const active = input.current
    if (source === 'demo') {
      setRunning(false)
      setPaused(true)
      return
    }
    if (!active?.pause) return
    active.pause()
    const current = active.position?.()
    if (current) setPosition(current)
    setRunning(false)
    setPaused(true)
  }
  async function resumePlayback() {
    const active = input.current
    if (source === 'demo') {
      setPaused(false)
      setRunning(true)
      return
    }
    if (!active?.resume || starting) return
    setStarting(true)
    setError('')
    try {
      await active.resume()
      if (input.current === active) {
        if (document.hidden) active.pause?.()
        setPaused(document.hidden)
        setRunning(!document.hidden)
      }
    } catch (e) {
      if (input.current === active) setError(e instanceof Error ? e.message : 'Could not resume playback.')
    } finally {
      if (input.current === active) setStarting(false)
    }
  }
  function changeRepeat(range: { start: number; end: number } | null) {
    const active = input.current
    if (!active?.setRepeat) return
    try {
      active.setRepeat(range, () => {
        memory.current.clear()
        time.current = active.position?.().seconds ?? 0
      })
      setRepeat(range)
      const current = active.position?.()
      if (current) setPosition(current)
      setFrame(EMPTY)
      setOutput(paint(EMPTY, time.current, 0))
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Repeat section unavailable.')
    }
  }
  function seekPlayback(seconds: number) {
    const active = input.current
    if (!active?.seek) return
    if (repeat) {
      active.setRepeat?.(null)
      setRepeat(null)
    }
    active.seek(seconds)
    const current = active.position?.()
    if (current) {
      setPosition(current)
      time.current = current.seconds
    }
    memory.current.clear()
    setFrame(EMPTY)
    setOutput(paint(EMPTY, time.current, 0))
  }

  async function revealView(next: 'Watch' | 'Learn' | 'Create') {
    if (document.fullscreenElement) {
      try {
        await document.exitFullscreen()
      } catch {
        setError('Exit fullscreen to open this panel.')
        return
      }
    }
    setView(next)
    requestAnimationFrame(() => {
      const target = document.getElementById(
        next === 'Learn'
          ? 'visualizer-explanation'
          : next === 'Create'
            ? 'visualizer-create'
            : 'visual-engine',
      )
      target?.focus()
      target?.scrollIntoView?.({ block: 'start', behavior: 'instant' })
    })
  }
  async function start() {
    if (abort.current || running) return
    setError('')
    setNotice('')
    setFinished(false)
    setPosition({ seconds: 0, duration: 0 })
    if (source === 'demo') {
      setRenderer('graph')
      sample()
      setRunning(true)
      return
    }
    if (!file) {
      setError('Choose a local audio file first.')
      return
    }
    const ctl = new AbortController()
    abort.current = ctl
    setStarting(true)
    try {
      const opened = await openAudio(file, false, ctl.signal, () => {
        if (abort.current === ctl) {
          const last = input.current?.position?.()
          if (last) setPosition({ seconds: last.duration, duration: last.duration })
          stop()
          setFinished(true)
        }
      })
      if (abort.current !== ctl || ctl.signal.aborted) {
        opened.stop()
        return
      }
      input.current = opened
      setVisualInput(opened)
      const loadedPosition = opened.position?.()
      if (loadedPosition) setPosition(loadedPosition)
      if (document.hidden) opened.pause?.()
      opened.setAudible(effectiveSound.current)
      setPaused(document.hidden)
      setRunning(!document.hidden)
    } catch (e) {
      if (!ctl.signal.aborted) setError((e as Error).message || 'This audio file could not be played.')
    } finally {
      if (abort.current === ctl) {
        setStarting(false)
        if (!input.current) abort.current = null
      }
    }
  }
  function sample() {
    time.current =
      source === 'file' ? (input.current?.position?.().seconds ?? time.current) : time.current + 0.25
    const f = source === 'demo' ? demoFrame(time.current) : (input.current?.read() ?? EMPTY)
    setOutput(paint(f, time.current, 0.25))
    setFrame(f)
    const measured = input.current?.measurement?.() ?? null
    setMeasurement(measured)
    setSnapshotMeasurement(measured)
    setSampleNumber((n) => n + 1)
  }
  function resetDemo() {
    releasePrevious()
    stop()
    setMeasurement(null)
    setSnapshotMeasurement(null)
    setSource('demo')
    setFinished(false)
    setPosition({ seconds: 0, duration: 0 })
    time.current = 0
    memory.current.clear()
    setSampleNumber(0)
    setFrame(EMPTY)
    setOutput(paint(EMPTY, 0, 0))
  }
  async function startLesson(settings: ToneSettings) {
    if (starting) return
    if (source !== 'lesson') {
      input.current?.pause?.()
      previousAudio.current = {
        input: input.current,
        abort: abort.current,
        source,
        time: time.current,
        audible,
        repeat,
      }
    } else {
      abort.current?.abort()
      input.current?.stop()
    }
    input.current = null
    setVisualInput(null)
    const ctl = new AbortController()
    abort.current = ctl
    setSource('lesson')
    setRunning(false)
    setPaused(false)
    setStarting(true)
    setAudible(false)
    setFinished(false)
    setError('')
    setMeasurement(null)
    setSnapshotMeasurement(null)
    try {
      const opened = await openTone(settings, ctl.signal)
      if (abort.current !== ctl || ctl.signal.aborted) {
        opened.stop()
        return
      }
      input.current = opened
      setVisualInput(opened)
      opened.setAudible(effectiveSound.current)
      if (document.hidden) opened.pause?.()
      setPaused(document.hidden)
      setRunning(!document.hidden)
    } catch (e) {
      if (!ctl.signal.aborted) setError((e as Error).message)
    } finally {
      if (abort.current === ctl) setStarting(false)
    }
  }
  function returnAudio() {
    const previous = previousAudio.current
    if (!previous) return
    previousAudio.current = null
    stop()
    input.current = previous.input
    abort.current = previous.abort
    setVisualInput(previous.input)
    setSource(previous.source)
    time.current = previous.time
    setAudible(previous.audible)
    setRepeat(previous.repeat)
    setPosition(previous.input?.position?.() ?? { seconds: 0, duration: 0 })
    setPaused(!!previous.input || previous.source === 'demo')
    setRunning(false)
    memory.current.clear()
    setMeasurement(null)
    setSnapshotMeasurement(null)
    setNotice('Previous audio restored, paused at its saved position. Press Resume when ready.')
  }
  function apply() {
    try {
      const next = parsePreset(text)
      setOutput(evaluate(next, latestFrame.current, time.current, 0, new Map()))
      setPreset(next)
      setError('')
      setNotice('Preset applied. Playback continues from the same position.')
      memory.current.clear()
    } catch (e) {
      setError(`${(e as Error).message} The last working preset is still active.`)
    }
  }
  function save() {
    try {
      const library = readLibrary(localStorage)
      const existing = library.items.find((x) => x.id === savedId)
      const id = existing?.id ?? crypto.randomUUID()
      const item = {
        id,
        name: existing?.name ?? preset.name,
        favorite: existing?.favorite ?? false,
        preset: { ...preset, name: existing?.name ?? preset.name },
      }
      writeLibrary(localStorage, {
        ...library,
        active: id,
        items: existing ? library.items.map((x) => (x.id === id ? item : x)) : [...library.items, item],
      })
      setSavedId(id)
      setCollectionVersion((v) => v + 1)
      setNotice('Applied preset saved in this browser. Audio is not saved.')
      setError('')
    } catch {
      setError('Browser storage is unavailable. Use Export preset to keep your work.')
    }
  }
  function download() {
    const url = URL.createObjectURL(new Blob([JSON.stringify(preset, null, 2)], { type: 'application/json' }))
    const a = document.createElement('a')
    a.href = url
    a.download = 'visualizer.visual.json'
    a.click()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  }
  useEffect(() => {
    if (view === 'Learn' && inspectId) document.getElementById('visualizer-explanation')?.focus()
  }, [view, inspectId])
  return (
    <div className="grid gap-4">
      <div>
        <Link to="/playground">← Coding playground</Link>
        <h1 className="text-xl font-semibold mt-2">Audio visualizer lab</h1>
        <p className="text-sm text-muted">
          See how changing a sound signal changes a picture. Start with the silent demo; no audio file or
          coding is needed.
        </p>
      </div>
      <nav aria-label="Visualizer views" className="flex flex-wrap gap-2">
        {(['Watch', 'Learn', 'Create'] as const).map((name) => (
          <Button
            key={name}
            variant={view === name ? 'primary' : 'outline'}
            aria-pressed={view === name}
            onClick={() => void revealView(name)}
          >
            {name}
          </Button>
        ))}
      </nav>
      <p className="text-sm">
        Start demo runs silent synthetic levels. Open audio prepares a local file; playback starts only when
        you press Play.
      </p>
      {energy <= 2 && (
        <p className="text-sm">
          Short version: keep the silent demo and use Next sample for a still view. The guided lesson is
          optional.
        </p>
      )}
      <div className="grid gap-4">
        <div className="grid gap-4 self-start min-w-0">
          <Card className="grid gap-3">
            <div ref={stage} className="bg-card p-2 rounded grid gap-2">
              <div className="relative">
                <canvas
                  ref={canvas}
                  width={720}
                  height={320}
                  className="w-full h-[clamp(220px,42vh,540px)] rounded border border-line"
                  aria-label="Audio-reactive visual preview"
                >
                  Visual preview. Numeric feature levels are listed below.
                </canvas>
                {renderer === 'milkdrop' && view === 'Watch' && (
                  <RendererBoundary
                    onFailure={(message) => {
                      setRichError(message)
                      setRenderer('graph')
                    }}
                  >
                    <Suspense fallback={<p className="absolute top-2 left-2">Loading rich visual…</p>}>
                      <Milkdrop
                        key={visualInput?.visualizerId ?? 'idle'}
                        input={visualInput}
                        running={running}
                        reduced={reduced}
                        selected={richPreset}
                        snapshot={sampleNumber}
                        onFailure={(message) => {
                          setRichError(message)
                          setRenderer('graph')
                        }}
                      />
                    </Suspense>
                  </RendererBoundary>
                )}
                {renderer === 'milkdrop' && view === 'Watch' && !visualInput && (
                  <p className="absolute inset-0 flex items-center justify-center p-8 text-white bg-black/70">
                    Open audio and press Play, or start a test signal in Learn, to drive this visual.
                  </p>
                )}
              </div>
              <div className="flex flex-wrap gap-2">
                <Button
                  variant="outline"
                  onClick={() => {
                    void (
                      document.fullscreenElement
                        ? document.exitFullscreen()
                        : stage.current!.requestFullscreen()
                    ).catch(() => setError('Fullscreen is unavailable in this browser.'))
                  }}
                >
                  {fullscreen ? 'Exit fullscreen' : 'Fullscreen'}
                </Button>
                <Button variant="outline" onClick={() => void revealView('Watch')}>
                  Choose visual
                </Button>
                <Button variant="outline" onClick={() => void revealView('Learn')}>
                  Learn how it works
                </Button>
                <Button variant="outline" onClick={() => audioPicker.current?.click()}>
                  Open audio
                </Button>
              </div>
              <AudioControls />
              <p className="text-sm">
                Sound: {source === 'demo' ? 'silent synthetic demo' : audible && sound ? 'on' : 'off'} ·
                Motion:{' '}
                {reduced
                  ? source === 'demo'
                    ? 'still image; use Next sample to update the picture'
                    : 'still image; use Capture current picture to update it'
                  : 'enabled'}
              </p>
              <div className="flex gap-2 flex-wrap">
                <Button
                  onClick={() => void (paused ? resumePlayback() : start())}
                  disabled={
                    running ||
                    starting ||
                    (source === 'lesson' && !paused) ||
                    (source === 'file' && (!file || file.size > 100 * 1024 * 1024))
                  }
                >
                  {starting
                    ? 'Opening audio…'
                    : paused
                      ? source === 'file'
                        ? 'Resume file'
                        : source === 'lesson'
                          ? 'Resume test signal'
                          : 'Resume demo'
                      : source === 'lesson'
                        ? 'Use Start test signal in Learn'
                        : source === 'file'
                          ? audible && sound
                            ? 'Play file with sound'
                            : 'Play file silently'
                          : 'Start demo'}
                </Button>
                <Button variant="outline" onClick={pausePlayback} disabled={!running || starting}>
                  {source === 'file'
                    ? 'Pause file'
                    : source === 'lesson'
                      ? 'Pause test signal'
                      : 'Pause demo'}
                </Button>
                <Button variant="outline" onClick={stop} disabled={!running && !starting && !paused}>
                  Stop
                </Button>
                <Button variant="outline" onClick={resetDemo}>
                  {source !== 'demo' ? 'Switch to silent demo' : 'Reset demo'}
                </Button>
                <Button
                  variant="outline"
                  onClick={sample}
                  disabled={source !== 'demo' && !running && !paused}
                >
                  {source !== 'demo' ? 'Capture current picture' : 'Next sample'}
                </Button>
              </div>
              {source === 'file' && (
                <p className="text-sm">
                  Pause keeps your place. Stop ends playback; the next Play starts at the beginning.
                </p>
              )}
              <p role="status" className="text-sm">
                {starting
                  ? 'Opening local audio'
                  : running
                    ? source === 'file'
                      ? `Playing ${audible && sound ? 'with sound' : 'silently'} · ${reduced ? 'picture stays still until you capture it' : 'picture follows the audio'}`
                      : source === 'lesson'
                        ? 'Test signal running — locally measured'
                        : 'Demo running'
                    : paused
                      ? 'Paused. Resume continues from this position.'
                      : finished
                        ? 'File finished. Play starts again from the beginning.'
                        : source === 'file'
                          ? file
                            ? `Selected: ${file.name}. Press Play to start from the beginning.`
                            : 'Choose an audio file to enable Play.'
                          : source === 'lesson'
                            ? 'Test signal stopped. Restart it in Learn or return to your audio.'
                            : 'Demo stopped. Next sample changes the picture.'}{' '}
                ·{' '}
                {renderer === 'milkdrop' && view === 'Watch'
                  ? 'MilkDrop artistic preset (separate from graph)'
                  : `Active preset: ${preset.name}`}
              </p>
              {error && (
                <p role="alert" className="text-sm">
                  {error}
                </p>
              )}
            </div>
            {view === 'Watch' && (
              <section className="grid gap-2" aria-label="Choose visual">
                <label>
                  Visual engine
                  <select
                    className="block border rounded bg-card p-2"
                    id="visual-engine"
                    value={renderer}
                    onChange={(e) => {
                      setRenderer(e.target.value as 'graph' | 'milkdrop')
                      setRichError('')
                    }}
                  >
                    <option value="graph">Explainable graph</option>
                    <option value="milkdrop">MilkDrop — artistic effects</option>
                  </select>
                </label>
                {renderer === 'milkdrop' && (
                  <>
                    <label>
                      Rich visual
                      <select
                        className="block border rounded bg-card p-2"
                        value={richPreset}
                        onChange={(e) => setRichPreset(Number(e.target.value))}
                      >
                        <option value={0}>Geiss — 3 layers</option>
                        <option value={1}>Geiss — Tunnel Mix</option>
                        <option value={2}>Geiss — Planar Mix</option>
                      </select>
                    </label>
                    <div className="flex gap-2">
                      <Button variant="outline" onClick={() => setRichPreset((i) => (i + 2) % 3)}>
                        Previous visual
                      </Button>
                      <Button variant="outline" onClick={() => setRichPreset((i) => (i + 1) % 3)}>
                        Next visual
                      </Button>
                    </div>
                    <p className="text-sm">
                      These artistic presets use their own calculations. Learn and Create show the explainable
                      graph instead.{' '}
                      {source === 'demo'
                        ? 'Open an audio file for a sound-reactive rich visual; the silent demo does not feed this renderer.'
                        : ''}
                    </p>
                  </>
                )}
                {richError && <p role="status">{richError}</p>}
                <details>
                  <summary className="cursor-pointer">Your saved visuals</summary>
                  <PresetLibrary
                    key={collectionVersion}
                    preset={preset}
                    onSaved={setSavedId}
                    onLoad={(p, id) => {
                      setSavedId(id)
                      setPreset(p)
                      setText(JSON.stringify(p, null, 2))
                      memory.current.clear()
                      setRenderer('graph')
                      setNotice('Saved visual loaded. Undo draft recovers the previous editor settings.')
                    }}
                  />
                </details>
              </section>
            )}
            <label>
              Input
              <select
                className="block w-full bg-card border border-line rounded p-2"
                value={source}
                onChange={(e) => {
                  releasePrevious()
                  stop()
                  setSource(e.target.value as 'demo' | 'file')
                  memory.current.clear()
                  setFrame(EMPTY)
                  setOutput(paint(EMPTY, 0, 0))
                  setPosition({ seconds: 0, duration: 0 })
                  setFinished(false)
                  setError('')
                }}
              >
                <option value="demo">Silent demo — synthetic levels</option>
                <option value="file">Local audio file</option>
                {source === 'lesson' && <option value="lesson">Local test signal</option>}
              </select>
            </label>
            <label hidden={source !== 'file'}>
              Audio file
              <input
                ref={audioPicker}
                className="block w-full"
                type="file"
                accept="audio/*"
                onClick={(e) => {
                  e.currentTarget.value = ''
                }}
                onChange={(e) => {
                  const selected = e.target.files?.[0]
                  if (!selected) return
                  releasePrevious()
                  stop()
                  setSource('file')
                  setFile(selected)
                  setPosition({ seconds: 0, duration: 0 })
                  setFinished(false)
                  setFrame(EMPTY)
                  memory.current.clear()
                  setOutput(paint(EMPTY, 0, 0))
                  setError('')
                }}
              />
            </label>
            {source === 'file' && (
              <>
                <p className="text-sm">
                  1. Choose an audio file from your computer. 2. Choose whether to hear it. 3. Press Play
                  above. Choosing a file only prepares its waveform; it does not start playback.
                </p>
                {file && (
                  <>
                    <p className="text-sm font-medium">Selected: {file.name}</p>
                    <details>
                      <summary className="cursor-pointer">Waveform and frequency overview</summary>
                      <AudioWaveform
                        key={`${file.name}-${file.lastModified}-${file.size}`}
                        file={file}
                        seconds={position.seconds}
                        reduced={reduced}
                      />
                    </details>
                  </>
                )}
                <label className="flex gap-2">
                  <input
                    type="checkbox"
                    checked={audible}
                    disabled={!sound || starting}
                    onChange={(e) => setAudible(e.target.checked)}
                  />
                  Hear audio at half volume
                </label>
                {!sound && (
                  <p className="text-sm text-muted">
                    Sound is off in <Link to="/preferences">Preferences</Link>. The file can play silently so
                    you can explore its picture.
                  </p>
                )}
                <p className="text-sm text-muted">
                  Audio stays in this browser tab. No upload or recording. Other apps’ audio is not captured.
                </p>
              </>
            )}
            {reduced && (
              <p className="text-sm text-muted">
                Reduced motion is on: the picture stays still even while a file plays. Use Capture current
                picture for a snapshot during playback (Next sample in the silent demo). Enable motion in{' '}
                <Link to="/preferences">Preferences</Link> for continuous visuals.
              </p>
            )}
            {source === 'file' && (
              <p className="text-sm">
                Playback position: {position.seconds.toFixed(1)} s /{' '}
                {position.duration
                  ? `${position.duration.toFixed(1)} s`
                  : 'playback duration not available yet'}
              </p>
            )}
            {source === 'file' && (
              <label className="grid gap-1 text-sm">
                Playback timeline
                <input
                  type="range"
                  min={0}
                  max={position.duration || 1}
                  step={0.1}
                  value={Math.min(position.seconds, position.duration || 1)}
                  disabled={(!running && !paused) || !position.duration || starting}
                  aria-valuetext={`${position.seconds.toFixed(1)} seconds of ${position.duration.toFixed(1)} seconds`}
                  onChange={(e) => seekPlayback(Number(e.target.value))}
                />
                <span className="text-xs text-muted">
                  After Play, drag or use arrow keys to move through the file. Seeking clears the current
                  picture. Resume playback first; in still-image mode, then choose Capture current picture.
                </span>
              </label>
            )}
            {source === 'file' && (
              <RepeatSection
                key={file ? `${file.name}-${file.lastModified}-${file.size}` : 'none'}
                duration={position.duration}
                enabled={(running || paused) && !starting}
                active={repeat}
                onChange={changeRepeat}
              />
            )}
            {repeat && (
              <p className="text-sm">
                Repeating {repeat.start.toFixed(1)}–{repeat.end.toFixed(1)} s. Moving the playback timeline
                turns repeat off.
              </p>
            )}
            {file && source === 'file' && file.size > 100 * 1024 * 1024 && (
              <p role="alert">Choose a file smaller than 100 MiB to play it.</p>
            )}
            <p className="text-sm">
              Graph · Manual sample: {sampleNumber} · Output size: {output.scale.toFixed(2)} · Output energy:{' '}
              {output.energy.toFixed(2)}
            </p>
            <details>
              <summary className="cursor-pointer">Sound measurements (optional)</summary>
              <p className="text-sm my-2">
                Synthetic levels in demo mode; measured levels for a playing file. These are not
                transcription, instrument detection or a saved report.
              </p>
              <dl className="grid grid-cols-4 gap-2 text-sm">
                {Object.entries(frame).map(([key, value]) => (
                  <div key={key}>
                    <dt>{key}</dt>
                    <dd>{value.toFixed(2)}</dd>
                  </div>
                ))}
              </dl>
            </details>
            <p className="text-xs text-muted">
              Bars are artistic output, not a frequency-spectrum chart. Band values are approximate normalized
              levels, not loudness measurements.
            </p>
          </Card>
        </div>
        <div className="grid gap-4 self-start min-w-0">
          <div id="visualizer-create" tabIndex={-1} hidden={view !== 'Create'}>
            <Card className="grid gap-3">
              <CardTitle>Create a visual</CardTitle>
              <details>
                <summary className="cursor-pointer">Choose an example</summary>
                <div className="grid gap-2 mt-2">
                  {examples.map((example) => (
                    <div key={example.title}>
                      <Button
                        variant="outline"
                        onClick={() => {
                          setText(JSON.stringify(example.preset, null, 2))
                          setInspectId('')
                          setNotice(
                            'Example loaded into the draft. Apply when ready; saved work is unchanged.',
                          )
                        }}
                      >
                        Load {example.title}
                      </Button>
                      <p className="text-sm text-muted">{example.description}</p>
                    </div>
                  ))}
                </div>
              </details>
              <PresetControls
                text={text}
                onChange={setText}
                onInspect={(id) => {
                  setInspectId(id)
                  setView('Learn')
                }}
              />
              {inspectId && (
                <a
                  className="text-sm underline"
                  href="#visualizer-explanation"
                  onClick={() => void revealView('Learn')}
                >
                  Read explanation for {inspectId} below
                </a>
              )}
              <div className="flex flex-wrap gap-2">
                <Button variant="outline" onClick={history.undo} disabled={!history.canUndo}>
                  Undo draft
                </Button>
                <Button variant="outline" onClick={history.redo} disabled={!history.canRedo}>
                  Redo draft
                </Button>
              </div>
              <p className="text-xs text-muted">
                Undo restores valid draft checkpoints; incomplete JSON edits are not retained.
              </p>
              {draftPreset && (
                <BlockAuthoring preset={draftPreset} onChange={(p) => setText(JSON.stringify(p, null, 2))} />
              )}
              <details>
                <summary className="cursor-pointer">Import or reset draft (optional)</summary>
                <div className="grid gap-3 mt-3">
                  <p className="text-sm">
                    Import accepts browser preset JSON up to 16,000 bytes. Choose a file to validate it, then
                    replace the draft explicitly. Applied and saved settings stay unchanged.
                  </p>
                  <label className="grid gap-1 text-sm">
                    Choose preset JSON file
                    <input
                      type="file"
                      accept=".json,application/json"
                      onChange={async (e) => {
                        const file = e.target.files?.[0]
                        const generation = ++importGeneration.current
                        setImportDraft(null)
                        setImportError('')
                        if (!file) return
                        try {
                          const candidate = await readPresetFile(file)
                          if (generation === importGeneration.current) setImportDraft(candidate)
                        } catch (err) {
                          if (generation === importGeneration.current) setImportError((err as Error).message)
                        }
                      }}
                    />
                  </label>
                  {importError && (
                    <p role="alert">{importError} Your draft and working picture are unchanged.</p>
                  )}
                  {importDraft && (
                    <div className="grid gap-2">
                      <p>
                        Ready to import: {importDraft.name} · {importDraft.nodes.length} blocks.
                      </p>
                      <Button
                        variant="outline"
                        onClick={() => {
                          setText(JSON.stringify(importDraft, null, 2))
                          setImportDraft(null)
                          setInspectId('')
                          setNotice(
                            'Imported into the draft. Apply when ready. Undo draft restores your previous valid draft.',
                          )
                        }}
                      >
                        Replace draft with imported preset
                      </Button>
                    </div>
                  )}
                  <p className="text-sm">
                    Reset replaces draft edits with the currently applied picture settings. It does not load a
                    factory example or alter the saved preset.
                  </p>
                  <Button
                    variant="outline"
                    disabled={!draftChanged}
                    onClick={() => {
                      setText(JSON.stringify(preset, null, 2))
                      setNotice(
                        'Draft reset to applied settings. Undo draft restores the previous valid draft.',
                      )
                    }}
                  >
                    Reset draft to applied settings
                  </Button>
                </div>
              </details>
              <div className="border border-line rounded p-3 grid gap-2">
                <p className="text-sm" role="status">
                  {!draftPreset
                    ? 'Fix the preset error or load an example before applying.'
                    : draftChanged
                      ? 'Appearance previews now. Apply to use and save all draft settings.'
                      : 'The preview matches your settings.'}
                </p>
                <div className="flex flex-wrap gap-2">
                  <Button variant="primary" onClick={apply}>
                    Apply preset
                  </Button>
                  <Button variant="outline" onClick={save} disabled={draftChanged}>
                    Save applied preset
                  </Button>
                  <Button variant="outline" onClick={download} disabled={draftChanged}>
                    Export applied preset
                  </Button>
                </div>
                <p className="text-xs text-muted">
                  Apply updates graph connections without restarting playback. Shape and color preview
                  immediately; Undo draft restores them. Save keeps these settings in this browser. Export
                  downloads a preset file.
                </p>
              </div>
              <h3 className="font-medium">Explore how it works (optional)</h3>
              <p className="text-sm text-muted">
                Follow the connections, or walk through one fixed sample to see each calculation.
              </p>
              <details name="visualizer-explore">
                <summary className="cursor-pointer">Signal flow diagram</summary>
                {draftPreset && (
                  <ConnectionEditor
                    preset={draftPreset}
                    onChange={(p) => setText(JSON.stringify(p, null, 2))}
                    onInspect={(id) => {
                      setInspectId(id)
                      setView('Learn')
                    }}
                  />
                )}
                <div className="mt-3">
                  {draftPreset ? (
                    <SignalFlow
                      preset={draftPreset}
                      draft={draftChanged}
                      selected={inspectId}
                      onInspect={(id) => {
                        setInspectId(id)
                        setView('Learn')
                      }}
                    />
                  ) : (
                    <p>
                      Fix the draft JSON or load an example to see its connections. The applied visual is
                      unchanged.
                    </p>
                  )}
                </div>
              </details>
              <details name="visualizer-explore">
                <summary className="cursor-pointer">Walk through one sample</summary>
                {draftPreset ? (
                  <SampleTrace key={JSON.stringify(draftPreset)} preset={draftPreset} />
                ) : (
                  <p>Fix the draft JSON or load an example before starting a walkthrough.</p>
                )}
              </details>
              <details name="visualizer-explore">
                <summary className="cursor-pointer">Advanced: edit preset JSON</summary>
                <p className="text-sm my-2">
                  These are the same settings as the controls above. You do not need to edit code to use this
                  lab.
                </p>
                <label htmlFor="visual-preset">Preset JSON</label>
                <textarea
                  id="visual-preset"
                  spellCheck={false}
                  maxLength={16000}
                  className="w-full min-h-72 font-mono text-sm p-3 bg-card border border-line rounded"
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                />
              </details>
              {notice && (
                <p role="status" className="text-sm">
                  {notice}
                </p>
              )}
            </Card>
          </div>
          <aside tabIndex={-1} id="visualizer-explanation" hidden={view !== 'Learn'}>
            <Card className="grid gap-3">
              <AudioLessons
                active={source === 'lesson'}
                starting={starting}
                onStart={(settings) => void startLesson(settings)}
                onUpdate={(settings) => {
                  input.current?.updateTone?.(settings)
                  setSnapshotMeasurement(null)
                }}
                onReturn={returnAudio}
                onCreate={() => void revealView('Create')}
              />
              {source === 'lesson' && (
                <label className="flex gap-2">
                  <input
                    type="checkbox"
                    checked={audible}
                    disabled={!sound || starting}
                    onChange={(e) => setAudible(e.target.checked)}
                  />
                  Hear test signal at half volume {sound ? '' : '(sound is off in Preferences)'}
                </label>
              )}
              <LiveMeasurement value={reduced ? snapshotMeasurement : measurement} still={reduced} />
              {reduced && (
                <p className="text-sm">
                  Analysis continues while the picture stays still. Choose Capture current picture to update
                  the plots.
                </p>
              )}
              {measurement && (
                <p className="text-sm" aria-label="Current measured values">
                  {running ? 'Live values' : 'Last measured values'}: RMS {measurement.rms.toFixed(3)} ·
                  strongest bin {measurement.peakHz.toFixed(1)} Hz · sample rate {measurement.sampleRate} Hz.
                </p>
              )}
              {inspectId && draftPreset && (
                <section aria-label="Selected block explanation">
                  <BlockExplanation
                    preset={draftPreset}
                    id={inspectId}
                    values={output.values}
                    draft={draftChanged}
                  />
                  <Button variant="outline" onClick={() => void revealView('Create')}>
                    Back to Create
                  </Button>
                </section>
              )}
            </Card>
          </aside>
        </div>
      </div>
    </div>
  )
}
