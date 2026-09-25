import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { Button } from '../components/ui/button'
import { Card, CardTitle } from '../components/ui/card'
import { useSensory } from '../features/sensory/useSensory'
import { useMode } from '../stores/mode'
import { openAudio, type AudioInput } from '../features/visualizer/audio'
import {
  demoFrame,
  evaluate,
  initial,
  parsePreset,
  type Frame,
  type Preset,
} from '../features/visualizer/engine'
import { draw } from '../features/visualizer/render'

import { GuidedExperiments } from '../features/visualizer/GuidedExperiments'
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

const STORAGE = 'audhs:visualizer:preset:v1'
const EMPTY: Frame = { bass: 0, mid: 0, treble: 0, rms: 0 }
function restore(): Preset {
  try {
    return parsePreset(localStorage.getItem(STORAGE) ?? JSON.stringify(initial))
  } catch {
    return initial
  }
}
const lessons = [
  {
    title: '1. Follow the signal',
    explanation:
      'The demo produces made-up feature levels, without sound. A feature node selects bass. Smooth makes rises and falls gradual. Map turns a level between 0 and 1 into a visual size.',
    task: 'Keep the demo stopped for comparisons. Use Next sample twice. Follow signal → soft → size in the graph.',
    hint: 'Start with the feature node, then follow each input name.',
    picture:
      'Audio → frequency analysis → feature levels → preset graph → image. The image is a chosen representation of sound; it is not a measure of musical quality.',
  },
  {
    title: '2. Change one mapping',
    explanation:
      'A map node changes a number’s range. Mapping [0, 1] to [0.4, 1.4] gives size 0.4 at zero input and 1.4 at full input. A different range changes the visual response, not the audio.',
    task: 'Predict what happens if size.outputRange becomes [0.8, 1.1]. Edit that range and Apply preset. This resets the demo. Compare the same manual sample number before and after.',
    hint: 'Compare the difference between the two output endpoints.',
    picture:
      'This is the same input → transformation → output pattern used in creative coding and workflow tools. Keeping one change at a time helps you explain cause and effect.',
  },
  {
    title: '3. Compare frequency regions',
    explanation:
      'Bass represents lower frequencies; mid and treble represent higher regions. These are approximate normalized band levels, not isolated instruments. RMS measures overall waveform amplitude. No beat or tempo detector is present.',
    task: 'Change signal.feature from bass to treble. Predict which visual movement will change. Reset the demo and compare the same manual sample number before and after. You can also choose a local audio file.',
    hint: 'Keep the mapping unchanged so you are comparing only the selected feature.',
    picture:
      'One instrument can contribute to several frequency bands. A response to bass is not proof that a kick drum or a beat was detected.',
  },
]

export function Visualizer() {
  const [preset, setPreset] = useState(restore)
  const history = useDraftHistory(JSON.stringify(preset, null, 2))
  const { text, change: setText } = history
  const [importDraft, setImportDraft] = useState<Preset | null>(null)
  const [importError, setImportError] = useState('')
  const importGeneration = useRef(0)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [source, setSource] = useState<'demo' | 'file'>('demo')
  const [running, setRunning] = useState(false)
  const [position, setPosition] = useState({ seconds: 0, duration: 0 })
  const [repeat, setRepeat] = useState<{ start: number; end: number } | null>(null)
  const [paused, setPaused] = useState(false)
  const [finished, setFinished] = useState(false)
  const [starting, setStarting] = useState(false)
  const [audible, setAudible] = useState(false)
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
  const [step, setStep] = useState(0)
  const [help, setHelp] = useState<'hint' | 'picture' | null>(null)
  const { reduced, sound } = useSensory()
  const energy = useMode((s) => s.energy)
  const canvas = useRef<HTMLCanvasElement>(null)
  const input = useRef<AudioInput | null>(null)
  const abort = useRef<AbortController | null>(null)
  const effectiveSound = useRef(false)
  const time = useRef(0)
  const memory = useRef(new Map<string, number>())
  const stop = useCallback(() => {
    abort.current?.abort()
    abort.current = null
    input.current?.stop()
    input.current = null
    setRunning(false)
    setPaused(false)
    setRepeat(null)
    setStarting(false)
  }, [])
  const paint = useCallback(
    (f: Frame, t: number, dt: number) => {
      const out = evaluate(preset, f, t, dt, memory.current)
      if (canvas.current) draw(canvas.current, preset, out.scale, out.energy)
      return out
    },
    [preset],
  )
  useEffect(() => {
    memory.current.clear()
    paint(EMPTY, 0, 0)
  }, [paint])
  useEffect(() => {
    effectiveSound.current = audible && sound
    input.current?.setAudible(effectiveSound.current)
  }, [audible, sound])
  useEffect(() => {
    const onHidden = () => {
      if (document.hidden) stop()
    }
    document.addEventListener('visibilitychange', onHidden)
    return () => {
      document.removeEventListener('visibilitychange', onHidden)
      abort.current?.abort()
      input.current?.stop()
    }
  }, [stop])
  useEffect(() => {
    if (!running || reduced) return
    let raf = 0
    let previous = 0
    let lastUi = 0
    function tick(now: number) {
      const dt = previous ? Math.min((now - previous) / 1000, 0.1) : 1 / 60
      previous = now
      time.current =
        source === 'file' ? (input.current?.position?.().seconds ?? time.current + dt) : time.current + dt
      const f = source === 'demo' ? demoFrame(time.current) : (input.current?.read() ?? EMPTY)
      const result = paint(f, time.current, dt)
      if (now - lastUi > 250) {
        setFrame(f)
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
    if (!active?.pause) return
    active.pause()
    const current = active.position?.()
    if (current) setPosition(current)
    setRunning(false)
    setPaused(true)
  }
  async function resumePlayback() {
    const active = input.current
    if (!active?.resume || starting) return
    setStarting(true)
    setError('')
    try {
      await active.resume()
      if (input.current === active) {
        setPaused(false)
        setRunning(true)
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

  async function start() {
    if (abort.current || running) return
    setError('')
    setNotice('')
    setFinished(false)
    setPosition({ seconds: 0, duration: 0 })
    if (source === 'demo') {
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
      const loadedPosition = opened.position?.()
      if (loadedPosition) setPosition(loadedPosition)
      opened.setAudible(effectiveSound.current)
      setRunning(true)
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
    setSampleNumber((n) => n + 1)
  }
  function resetDemo() {
    stop()
    setSource('demo')
    setFinished(false)
    setPosition({ seconds: 0, duration: 0 })
    time.current = 0
    memory.current.clear()
    setSampleNumber(0)
    setFrame(EMPTY)
    setOutput(paint(EMPTY, 0, 0))
  }
  function guidedExample() {
    stop()
    setSource('demo')
    setFinished(false)
    setPosition({ seconds: 0, duration: 0 })
    time.current = 0
    memory.current.clear()
    setSampleNumber(0)
    setPreset(initial)
    setText(JSON.stringify(initial, null, 2))
    setFrame(EMPTY)
    setOutput(evaluate(initial, EMPTY, 0, 0, new Map()))
    setError('')
    setHelp(null)
    setNotice('Guided example applied. Saved presets are unchanged.')
  }
  function apply() {
    try {
      const next = parsePreset(text)
      if (source === 'demo') {
        stop()
        time.current = 0
        setSampleNumber(0)
        setFrame(EMPTY)
      }
      setOutput(evaluate(next, EMPTY, 0, 0, new Map()))
      setPreset(next)
      setError('')
      setNotice(
        source === 'demo' ? 'Preset applied. Demo reset; compare the same sample number.' : 'Preset applied.',
      )
      memory.current.clear()
    } catch (e) {
      setError(`${(e as Error).message} The last working preset is still active.`)
    }
  }
  function save() {
    try {
      localStorage.setItem(STORAGE, JSON.stringify(preset))
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
  const lesson = lessons[step]
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
      <p className="border border-line rounded p-3 text-sm">
        Start here: choose Next sample to see a still picture. Change Visual style or color, then Apply
        preset. Open the learning tools only when you want to explore how it works.
      </p>
      {energy <= 2 && (
        <p className="text-sm">
          Short version: keep the silent demo and use Next sample for a still view. The guided lesson is
          optional.
        </p>
      )}
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1.2fr)_minmax(320px,1fr)]">
        <div className="grid gap-4 self-start min-w-0">
          <Card className="grid gap-3">
            <CardTitle>1. See the result</CardTitle>
            <label>
              Input
              <select
                className="block w-full bg-card border border-line rounded p-2"
                value={source}
                onChange={(e) => {
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
              </select>
            </label>
            {source === 'file' && (
              <>
                <label>
                  Audio file
                  <input
                    className="block w-full"
                    type="file"
                    accept="audio/*"
                    onChange={(e) => {
                      stop()
                      setFile(e.target.files?.[0] ?? null)
                      setPosition({ seconds: 0, duration: 0 })
                      setFinished(false)
                      setFrame(EMPTY)
                      memory.current.clear()
                      setOutput(paint(EMPTY, 0, 0))
                      setError('')
                    }}
                  />
                </label>
                <p className="text-sm">
                  1. Choose an audio file from your computer. 2. Choose whether to hear it. 3. Press Play
                  below. Choosing a file only prepares its waveform; it does not start playback.
                </p>
                {file && (
                  <>
                    <p className="text-sm font-medium">Selected: {file.name}</p>
                    <AudioWaveform
                      key={`${file.name}-${file.lastModified}-${file.size}`}
                      file={file}
                      seconds={position.seconds}
                      reduced={reduced}
                    />
                  </>
                )}
                <label className="flex gap-2">
                  <input
                    type="checkbox"
                    checked={audible}
                    disabled={!sound}
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
            <div className="flex gap-2 flex-wrap">
              <Button
                onClick={() => void (paused ? resumePlayback() : start())}
                disabled={
                  running ||
                  starting ||
                  (source === 'demo' && reduced) ||
                  (source === 'file' && (!file || file.size > 100 * 1024 * 1024))
                }
              >
                {starting
                  ? 'Opening audio…'
                  : paused
                    ? 'Resume file'
                    : source === 'file'
                      ? audible && sound
                        ? 'Play file with sound'
                        : 'Play file silently'
                      : 'Start demo'}
              </Button>
              {source === 'file' && (
                <Button variant="outline" onClick={pausePlayback} disabled={!running || starting}>
                  Pause file
                </Button>
              )}
              <Button variant="outline" onClick={stop} disabled={!running && !starting && !paused}>
                Stop
              </Button>
              <Button variant="outline" onClick={resetDemo}>
                {source === 'file' ? 'Switch to silent demo' : 'Reset demo'}
              </Button>
              <Button variant="outline" onClick={sample} disabled={source === 'file' && !running}>
                {source === 'file' ? 'Capture current picture' : 'Next sample'}
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
                    : 'Demo running'
                  : paused
                    ? 'Paused. Resume continues from this position.'
                    : finished
                      ? 'File finished. Play starts again from the beginning.'
                      : source === 'file'
                        ? file
                          ? 'File selected. Press Play to start from the beginning.'
                          : 'Choose an audio file to enable Play.'
                        : 'Demo stopped. Next sample changes the picture.'}{' '}
              · Active preset: {preset.name}
            </p>
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
            {error && (
              <p role="alert" className="text-sm">
                {error}
              </p>
            )}
            <canvas
              ref={canvas}
              width={720}
              height={320}
              className="w-full rounded border border-line"
              aria-label="Audio-reactive visual preview"
            >
              Visual preview. Numeric feature levels are listed below.
            </canvas>
            <p className="text-sm">
              Manual sample: {sampleNumber} · Output size: {output.scale.toFixed(2)} · Output energy:{' '}
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
          <Card className="grid gap-3">
            <CardTitle>2. Change the picture</CardTitle>
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
                        setNotice('Example loaded into the draft. Apply when ready; saved work is unchanged.')
                      }}
                    >
                      Load {example.title}
                    </Button>
                    <p className="text-sm text-muted">{example.description}</p>
                  </div>
                ))}
              </div>
            </details>
            <PresetControls text={text} onChange={setText} onInspect={setInspectId} />
            {inspectId && (
              <a className="text-sm underline" href="#visualizer-explanation">
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
                    ? 'You have changes to preview. Apply them when ready.'
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
                Apply updates the picture and resets the silent demo; Next sample advances it again. Save
                keeps these settings in this browser. Export downloads a preset file.
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
                  onInspect={setInspectId}
                />
              )}
              <div className="mt-3">
                {draftPreset ? (
                  <SignalFlow
                    preset={draftPreset}
                    draft={draftChanged}
                    selected={inspectId}
                    onInspect={setInspectId}
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
          <aside id="visualizer-explanation">
            <Card className="grid gap-3">
              <CardTitle>Help with this experiment</CardTitle>
              {!inspectId && (
                <p className="text-sm">
                  Start with the preview and change one setting. For a block explanation, open Block controls
                  and choose Explain. For a guided exercise, open the lesson below.
                </p>
              )}
              {inspectId && draftPreset && (
                <BlockExplanation
                  preset={draftPreset}
                  id={inspectId}
                  values={output.values}
                  draft={draftChanged}
                />
              )}
              <details>
                <summary className="cursor-pointer">Try a short comparison experiment</summary>
                <GuidedExperiments />
              </details>
              <details>
                <summary className="cursor-pointer">Guided Bass rings lesson</summary>
                <p className="text-sm">
                  The guide uses the Bass rings example and its signal → soft → size nodes. Apply it
                  explicitly to follow along; your saved preset is kept.
                </p>
                <Button variant="outline" onClick={guidedExample}>
                  Start guided example
                </Button>
                <p className="text-xs text-muted">Built-in explanations · no model request</p>
                <label>
                  Practice step
                  <select
                    className="block w-full bg-card border border-line rounded p-2"
                    value={step}
                    onChange={(e) => {
                      setStep(Number(e.target.value))
                      setHelp(null)
                    }}
                  >
                    {lessons.map((l, i) => (
                      <option value={i} key={l.title}>
                        {l.title}
                      </option>
                    ))}
                  </select>
                </label>
                <p>{lesson.explanation}</p>
                <p className="text-sm font-medium">Try: {lesson.task}</p>
                <div className="flex gap-2 flex-wrap">
                  <Button variant="outline" onClick={() => setHelp('hint')}>
                    One hint
                  </Button>
                  <Button variant="outline" onClick={() => setHelp('picture')}>
                    Bigger picture
                  </Button>
                </div>
                {help && (
                  <p className="text-sm" role="status">
                    {help === 'hint' ? lesson.hint : lesson.picture}
                  </p>
                )}
                <p className="text-xs text-muted">
                  These explanations describe this lab’s implementation. They are not retrieved course claims.
                </p>
              </details>
              <details>
                <summary className="cursor-pointer">Supported building blocks</summary>
                <p className="text-sm mt-2">
                  feature selects rms/bass/mid/treble. constant sets a number. map changes a range. smooth
                  uses separate attack/release times. lfo creates a slow oscillation, independent of the
                  audio. Render modes: rings, bars, orbit.
                </p>
              </details>
            </Card>
          </aside>
        </div>
      </div>
    </div>
  )
}
