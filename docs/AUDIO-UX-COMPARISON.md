# Audio learning tools: UX comparison and implementation

Reviewed 24 September 2026 against official documentation and the tutor's source. This is a documentation/code comparison, not a hands-on usability study of the other applications.

## The underlying confusion

The tutor's Start audio analysis command starts real-time playback through Web Audio. Sound is opt-in; reduced-motion preferences suppress automatic visual updates. Consequently, the file can be progressing silently while the picture stays still. The former interface did not show a file timeline or playback position. “Analysis” also suggested a completed report, transcription or detected musical information, none of which this feature produces.

## Patterns worth adopting

| Tool | Established interaction | Relevant lesson for the tutor | What we should avoid importing |
|---|---|---|---|
| Audacity | Import creates an audio track; playback is controlled separately through transport controls. | Show the selected file before playback, use familiar Play/Stop labels and state whether sound is enabled. | Full multitrack editing, effects menus and recording controls would distract from the teaching objective. |
| Sonic Visualiser | Opening audio provides waveform and time-ruler layers; analysis adds other layers aligned in time. | Distinguish the audio overview from measurements and artistic output. Explain what each representation means. | Advanced layers and transforms should not become the default beginner interface. |
| WaveSurfer | Embeddable waveform, configurable interaction, optional timeline/regions/spectrogram plugins. | Use its local waveform rendering instead of building another bespoke overview. Keep one authoritative playback controller. | Do not automatically add every plugin or turn a waveform click into surprise playback. |

Sources: [Audacity import](https://manual.audacityteam.org/man/importing_audio.html), [Audacity transport](https://manual.audacityteam.org/man/playing_and_recording.html), [Sonic Visualiser reference](https://www.sonicvisualiser.org/doc/reference/5.0.0/en/), [WaveSurfer library](https://wavesurfer.xyz/).

## Implemented flow

1. Choose Local audio file. Explanation makes clear that this is a file on your computer, not microphone or system capture.
2. Choose the file. Its name and waveform appear; nothing starts playing. WaveSurfer 8.0.0 is pinned and bundled locally. Waveform previews are limited to 20 MiB and decoded at reduced sample rate for an overview. Larger files can still use the existing playback path up to 100 MiB.
3. Choose whether to hear audio. The existing sound preference remains authoritative; disabled sound links to Preferences.
4. Press Play file silently or Play file with sound. Both move through the file and measure current sound levels. Elapsed time is visible.
5. In reduced-motion mode, choose Capture current picture to update the still visual. With motion enabled, the picture follows the audio automatically.
6. Stop ends playback. The next Play begins at the start. Natural completion is labeled explicitly.

The waveform is deliberately an overview, not a second player or editable timeline. Decode failure leaves a fallback message and does not prevent trying playback. No audio leaves the browser, no hosted API is involved, and no transcript or analysis report is generated. The decorative rings/bars/orbit remain separate from the waveform and are not scientific spectral charts.

## Recommended later steps

- Implemented after the comparison: pause/resume and a separate accessible seek slider through the same playback controller. WaveSurfer remains overview-only; waveform-click seeking is not implemented.
- Add optional selected-region replay for comparing a short, repeatable section.
- Add a spectrogram only with axes, units and a worked explanation of time versus frequency.
- Validate the resulting tasks with the owner: choose a file, explain whether it is playing, capture a picture, stop, and repeat a section.

A library solves rendering and interaction mechanics. Clear terminology, state transitions and teaching remain application responsibilities. These changes are a bounded audio-flow improvement, not evidence that the complete app's usability is solved.
