# V4 portable visualizer contract — proposal

Status: proposed, pending owner acceptance. No export/import schema migration has been applied. Browser v1 remains operational. This document is the concrete schema decision for a subsequent owner-invoked ADR; it does not silently accept or amend an existing decision.

## Proposed decision

Introduce a portable envelope with `format: "audhs.visualizer.portable"`, `version: 1`, `featureProfile: "audhs.browser-normalized.v1"`, and `preset` containing the existing bounded browser graph. Distinct identity avoids the incompatible research native `schemaVersion: 1` example, whose shader passes cannot be rendered by the browser. Keep the existing internal Preset type and localStorage key initially. Export the new envelope only after acceptance; explicitly recognize and import existing unwrapped browser v1 files. Display format/profile before replacing a draft.

Reserve `audhs.visualizer.native` for future native-specific graphs; do not claim or implement that full format now. A native runtime may implement the portable subset without supporting native shader passes.

## Conversion and diagnostics

- Legacy browser v1 → portable envelope: lossless, after strict validation. No automatic persistence migration.
- Portable envelope → current internal graph: lossless only for supported format/version/profile, five node types and rings/bars/orbit.
- Research/native input with passes, shaders, custom expressions, extra feature types or unrecognized fields: reject with the unsupported field/capability path and an explanation. Do not strip fields and report success.
- Reject mixed envelopes, unknown identities/versions, missing profile and mismatched payload version. Legacy input with native-only fields is not legacy browser data. Strict checks precede the existing parser, which currently normalizes recognized fields and would otherwise discard extras.
- Untrusted JSON remains data. No code, shader, imports, remote URLs or process capture are executed by conversion. No audio or external API calls.
- Preserve current 16,000-byte import envelope bound and 32-node bound. Existing legacy valid files retain their legacy import path; new export must check envelope size and give actionable diagnostics if overhead exceeds the limit. Ranges, IDs and cycles retain existing validation.

## Feature and evaluator profile

Inputs: dimensionless finite `rms`, `bass`, `mid`, `treble` in [0,1], explicit frame time in seconds and delta seconds. The accepted portable ingress must reject missing/nonfinite feature inputs before evaluator invocation; no guessed native substitution. This validation is a future contract requirement, not current browser behavior (which clamps invalid feature values). Current fixtures contain complete finite frames.

The current browser measurement uses analyser FFT size 2048 and smoothingTimeConstant 0.5. RMS is sqrt(mean(sample squared)), clamped [0,1]. Bands average per-bin clamp((dB+80)/60,0,1), with bin frequency i*sampleRate/fftSize and low inclusive/high exclusive regions: bass20–250 Hz, mid250–4000 Hz, treble4000–min(16000,Nyquist) Hz. Empty bands are zero. This is an approximate normalized display feature, not calibrated loudness or energy. Native vDSP windowing/scaling cannot be declared equivalent without matching measurement fixtures. Initial cross-runtime fixtures start at the normalized feature-frame boundary only.

Dependencies are evaluated topologically. Feature values clamp [0,1]; constants are [-100,100]. Map input endpoints must increase; normalized input ratio is clamped [0,1], then mapped to output endpoints [-100,100]. Smooth starts at zero for missing memory: old + (target-old)*(1-exp(-dt/tau)); rising target selects attack, otherwise release; tau milliseconds converted to seconds; dt clamped [0,0.25]. Smoothing memory is independent per runtime/session and reset for fixtures. LFO: (sin(seconds*2*pi*frequencyHz)+1)*0.5*amplitude, frequency/amplitude [0,2]. Node results clamp [-100,100]. Visual size clamps [0.1,2], energy [0,1]. Rings ignores energy but the binding must still exist. Temporary canvas positions are not graph semantics and are not serialized.

Raw native peak/centroid/flux/onset/beat/confidence/tempo/spectrum fields are not portable features. No automatic conversion or beat claims. Missing capabilities produce a rejection, not zero values.

## Fixtures and native entry points

`frontend/src/features/visualizer/fixtures/portable-evaluation-v1.json` is platform-neutral JSON containing four independent arithmetic references: direct feature, clipped mapping, smoothing step, oscillator peak. Each case has preset, frame, seconds, dt, initialMemory and expected node/visual outputs; absolute tolerance1e-6. `portable-fixtures.test.ts` verifies the browser evaluator. Native N0/N2 should copy these as read-only fixtures into its test target and implement an independent consumer. Passing browser tests establishes browser conformance only, not native compatibility or DSP equivalence. Add multi-step attack/release, dt edge cases and rejection fixtures when implementing the accepted contract.

## Alternatives and effects

Reusing bare schemaVersion1 is ambiguous and unsafe. Renaming every existing browser field creates unnecessary migration. An explicit envelope preserves the existing graph, adds a feature profile, and leaves native-specific features honestly unsupported. Cost: strict ingress validator and converter, larger export envelope, explicit version/profile maintenance.

## Remaining acceptance work

Owner schema decision → strict discriminator/converter and diagnostics → legacy/portable round-trip and rejection tests → reviewer check → native fixture consumer. No accepted architecture decision or native project is claimed yet.
