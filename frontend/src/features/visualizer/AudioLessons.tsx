import { useState } from 'react'
import { Button } from '../../components/ui/button'
import { defaultTone, type ToneSettings } from './tone'
import { GuidedExperiments } from './GuidedExperiments'
const lessons = [
  {
    title: 'Amplitude',
    explanation:
      'Amplitude describes the size of digital waveform samples. Increasing it makes the waveform taller. Sound stays muted unless you explicitly enable it.',
    task: 'Start the test signal. Change amplitude from 0.2 to 0.4 and compare RMS. For a sine wave, RMS is approximately amplitude divided by √2.',
    hint: 'Doubling amplitude doubles sine-wave RMS. It does not mean twice the perceived loudness.',
  },
  {
    title: 'Frequency',
    explanation:
      'Frequency counts cycles per second, measured in hertz. A higher-frequency sine wave has more cycles in the same time window.',
    task: 'Move from 100 Hz to 1,000 Hz. Look at the strongest frequency bin and the spacing between waveform cycles.',
    hint: 'The FFT reports the nearest frequency bin, so its peak will not always equal the slider exactly.',
  },
  {
    title: 'Harmonics',
    explanation:
      'A sine wave has one frequency. A square wave also contains odd harmonics: three, five and further odd multiples of the fundamental.',
    task: 'Compare sine and square at 220 Hz. Look for additional spectrum peaks, while keeping amplitude unchanged.',
    hint: 'Equal peak amplitude is not equal RMS. A square wave has higher RMS; browser synthesis limits harmonics below the Nyquist frequency.',
  },
  {
    title: 'Sampling and FFT',
    explanation:
      'The sample rate sets how many samples are represented per second. The highest representable frequency is below half that rate. FFT bin spacing equals sample rate divided by the window size.',
    task: 'Compare 512 and 8,192 samples at a fixed tone. A longer window separates nearby frequencies more finely but spans more time.',
    hint: 'Changing FFT size does not change the actual device sample rate. This lesson shows the browser’s real sample rate.',
  },
  {
    title: 'Audio to animation',
    explanation:
      'The graph maps normalized frequency controls into a picture. These controls are artistic transformations of dB values, not physical band energy.',
    task: 'Try a fixed-input comparison below. Both pictures use identical input with separate smoothing memory.',
    hint: 'Smoothing changes how quickly the picture follows a signal; it does not change the sound.',
  },
  {
    title: 'Create a personal visual',
    explanation:
      'Combine a chosen feature, a mapping and optional smoothing into your own visual. Each visual is a representation of the signal, not an assessment of musical quality.',
    task: 'Open Create. Change one mapping, Apply, then save your applied visual under a name in Watch’s collection.',
    hint: 'Keep one thing constant while changing another. Undo draft restores a previous valid editor state.',
  },
]
export function AudioLessons({
  active,
  starting,
  onStart,
  onUpdate,
  onReturn,
  onCreate,
}: {
  active: boolean
  starting: boolean
  onStart: (s: ToneSettings) => void
  onUpdate: (s: ToneSettings) => void
  onReturn: () => void
  onCreate: () => void
}) {
  const [step, setStep] = useState(0)
  const [settings, setSettings] = useState(defaultTone)
  const [hint, setHint] = useState(false)
  function update(next: ToneSettings) {
    setSettings(next)
    if (active) onUpdate(next)
  }
  const lesson = lessons[step]
  return (
    <section aria-label="Audio lessons" className="grid gap-3">
      <label>
        Learning step
        <select
          disabled={starting}
          className="block border rounded bg-card p-2"
          value={step}
          onChange={(e) => {
            setStep(Number(e.target.value))
            if (Number(e.target.value) !== 2) update({ ...settings, waveform: 'sine' })
            setHint(false)
          }}
        >
          {lessons.map((l, i) => (
            <option key={l.title} value={i}>
              {i + 1}. {l.title}
            </option>
          ))}
        </select>
      </label>
      <h2 className="font-semibold">{lesson.title}</h2>
      <p>{lesson.explanation}</p>
      <p>{lesson.task}</p>
      {step < 4 && (
        <>
          <p className="text-sm">
            Start test signal pauses your file and generates a real local tone for analysis. It starts silent.
            Return restores your file paused at its previous position.
          </p>
          <Button disabled={starting} onClick={() => onStart(settings)}>
            {active ? 'Restart test signal' : 'Start test signal'}
          </Button>
          {(step === 0 || step === 2) && (
            <label>
              Test amplitude
              <input
                disabled={starting}
                type="range"
                min="0"
                max="0.5"
                step="0.01"
                value={settings.amplitude}
                onChange={(e) => update({ ...settings, amplitude: Number(e.target.value) })}
              />
              <span>{settings.amplitude.toFixed(2)}</span>
            </label>
          )}
          {(step === 1 || step === 2) && (
            <label>
              Test frequency (Hz)
              <input
                disabled={starting}
                type="range"
                min="100"
                max="1000"
                step="10"
                value={settings.frequency}
                onChange={(e) => update({ ...settings, frequency: Number(e.target.value) })}
              />
              <span>{settings.frequency} Hz</span>
            </label>
          )}
          {step === 2 && (
            <label>
              Test waveform
              <select
                disabled={starting}
                value={settings.waveform}
                onChange={(e) =>
                  update({ ...settings, waveform: e.target.value as ToneSettings['waveform'] })
                }
              >
                <option value="sine">Sine</option>
                <option value="square">Square</option>
              </select>
            </label>
          )}
          {step === 3 && (
            <label>
              FFT window (samples)
              <select
                disabled={starting}
                value={settings.fftSize}
                onChange={(e) => update({ ...settings, fftSize: Number(e.target.value) })}
              >
                {[512, 2048, 8192].map((n) => (
                  <option key={n}>{n}</option>
                ))}
              </select>
            </label>
          )}
        </>
      )}
      {step === 4 && <GuidedExperiments />}
      {step === 5 && <Button onClick={onCreate}>Open Create</Button>}
      <div className="flex gap-2">
        <Button variant="outline" onClick={() => setHint(!hint)}>
          {hint ? 'Hide hint' : 'One hint'}
        </Button>
        {active && (
          <Button variant="outline" onClick={onReturn}>
            Return to previous audio
          </Button>
        )}
      </div>
      {hint && <p role="status">{lesson.hint}</p>}
      <p className="text-xs text-muted">
        Built-in practical explanations, not retrieved course claims. Optional exploration; no grades or
        mastery records.
      </p>
    </section>
  )
}
