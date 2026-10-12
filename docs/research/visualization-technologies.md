# Visualization technologies and learning representations

Audit/recommendation: 2026-10-12. All thirteen candidates remain in the future content
creation specification, per owner direction. Deferred means not installed now.

## Architecture recommendation before implementation

Reuse React Flow for a first ML information-flow experiment. Retain Mermaid/KaTeX
for static relationships/formulae and the existing audio stack. Add no dependencies
for this prototype. Prototype goal: distinguish fitting preprocessing on training
examples from applying the fitted transform to held-out examples. Change the fitting
scope, observe a deterministic numerical counterexample, then answer a transfer
question. No model call, execution of authored code, curriculum publication or mastery
update. This tests active reasoning, not attraction to animation.

Inspected: ARCHITECTURE.md, VISUAL-LEARNING-QUEUE.md, Complete design alignment,
frontend rules, package.json, BlockCanvas/AudioWaveform/Visualizer, Playground,
kernel/representations.py, LearningObject/Representation, model gateway and existing
evaluation harness. LearningObject already owns skill/goal/sources/success criteria;
Representation is a deletable cache and cannot own immutable authored visual versions.
The current diagram representation is prose; Map renders Mermaid. Audio graphs do
not establish curriculum semantics. The deterministic kernel continues to own learning
state; model proposals go through existing task routing/validation/review.

Likely prototype files: features/visual-learning spec/math/rendering/tests, one lazy
playground route, a Playground link, browser tests. Use existing design tokens and
controls (PDF foundations pp2/5–8), one primary Check action, visible exit, no autoplay.
No changes to selection, grading, FSRS, model routing or backend schema are needed.

## Candidate assessment

All can operate locally when code/assets/fonts are packaged locally. This is not a
claim that their hosted demos, plugins, map tiles, speech or imported media work
offline. Ordinary bounded 2D scenes suit this M4 Pro/48GB machine. Complexity limits
matter more than raw hardware; never infer accessibility or correctness from rendering.
Effort below is relative engineering effort, not a delivery estimate.

| Candidate and primary source | Learning uses / subject reuse | Architecture, offline hardware, effort | Access and correctness; existing overlap / activation criterion |
|---|---|---|---|
| [Mafs](https://github.com/stevenpetryk/mafs) | Function parameters, vectors, derivatives; math/physics/ML | React-native SVG; local CSS/fonts; low–medium adapter effort | Native form controls/text table needed alongside draggable points; author motion off. Test coordinates, units and reference calculations. Existing KaTeX explains formulas but not interactive plots. Activate for several coordinate-based lessons. |
| [JSXGraph](https://github.com/jsxgraph/jsxgraph) | Geometric constructions, transformations, calculus | Imperative board wrapped with React lifecycle cleanup; SVG/canvas; medium effort | [ARIA/keyboard facilities](https://jsxgraph.org/home/documentation/accessibility/) still require semantic descriptions and non-drag controls. Test construction invariants. Prefer over Mafs only for constrained geometry needs. |
| [React Flow](https://github.com/xyflow/xyflow) | Pipelines, causal hypotheses, prerequisite relationships across computing/science | Already pinned12.11.6; React/TS DOM+SVG; lazy reuse, low incremental effort | [Keyboard/ARIA support](https://reactflow.dev/learn/advanced-use/accessibility); text relationship list and no animated edges. Test edge meaning independently of layout. Reuse existing library, not audio-domain schema. Chosen now. |
| [Cytoscape.js](https://github.com/cytoscape/cytoscape.js) | Large networks, graph algorithms, biological/social networks | Imperative canvas adapter; CPU layouts bounded; medium–high effort | Canvas needs accessible parallel list, controls and static layout option. Test graph algorithms and seeded layouts. Overlaps React Flow/Map; activate when large-network analysis is required. |
| [Plotly.js](https://github.com/plotly/plotly.js) | Distributions, residuals, uncertainty, scientific notebook results | React wrapper/custom lifecycle; Python can emit validated figure data; partial builds, medium effort | Data table, labeled axes, keyboard alternatives; disable transitions. Validate traces, units, aggregation and misleading scales. No comparable full scientific plotting component now. Activate for notebook-to-lesson chart reuse. OSS library is distinct from commercial hosted products. |
| [D3.js](https://github.com/d3/d3) | Custom statistical/algorithm views across subjects | Use individual scale/shape modules, React owns DOM; medium–high authoring effort | Accessibility/motion entirely application responsibility. Test transforms against independent numeric oracles. Smaller custom renderer possible; avoid whole D3 solely for basic charts. |
| [Manim Community](https://github.com/ManimCommunity/manim) | Derivations, geometry, algorithm explanations | Python authoring/build-time render; CPU/render storage, optional TeX/FFmpeg; high pipeline effort | Reviewed cached video/stills with transcript, captions and pause/seek; not live learner manipulation. Test keyframes/math before publication. Choose for Python/math author workflow, never execute generated scripts in host runtime. |
| [Motion Canvas](https://github.com/motion-canvas/motion-canvas) | Narrated stepwise explanations, code/data-flow animation | TS authoring/editor plus render pipeline; medium–high effort | Controlled playback and transcript/still sequence; authored animation is not React lesson state. Test scene timeline and assertions. Alternative authoring backend to Manim, not another mandatory learner runtime. |
| [wavesurfer.js](https://wavesurfer.xyz/) | Audio segmentation, listening, waveform timing | Already pinned8.0.0; Web Audio/media, memory bounded by decoding; low reuse effort | Keep existing HTML controls/text transcript; waveform is not spectrum. Test timing/seek/known audio fixtures. Reuse rather than duplicate player. |
| [Butterchurn](https://github.com/jberg/butterchurn) | Creative audio exploration, aesthetic mappings | Already2.6.7; WebGL2/GPU and curated presets; existing fallback | Keep motion opt-in, existing pause/fallback, text alternatives. Imported effects do not explain signal processing. Validate signal measures separately; preset licensing separate from engine. Preserve existing Watch experience. |
| [p5.js](https://github.com/processing/p5.js) | Creative coding, simulations, generative patterns | Imperative canvas/WebGL instance cleanup; medium effort, bounded frame rate | [describe/text equivalents](https://p5js.org/tutorials/writing-accessible-canvas-descriptions/), native controls, noLoop when paused. Seed randomness/test numerical model. Activate for reviewed creative exercises in a sandbox, not arbitrary model code in main page. |
| [Three.js](https://github.com/mrdoob/three.js) | Spatial transforms, molecular/physical structures, 3D geometry | GPU scene lifecycle and resource disposal; high effort | Camera keyboard controls, equivalent2D/text, static fallback; avoid motion as prerequisite. Test matrices/projections and resource limits. Activate only when depth materially aids learning;2D usually cheaper. |
| [LiaScript](https://github.com/LiaScript/LiaScript) | Portable authored interactive lessons across subjects | Separate Markdown interpreter, export/PWA; high integration effort | Keyboard/text/quiz/TTS require per-template audits; offline assets must be bundled. Existing app already owns quiz/voice/progress. Prefer import/export subset first; reject executable macros/scripts in untrusted imports. Do not introduce a second progress authority. |

## License, maintenance and package evidence

Retrieved npm publisher metadata on2026-10-12 (registry.npmjs.org); dates below are
latest package release timestamps, not a security audit or proof of active support.
Unpacked size is NOT browser bundle/gzip size and excludes transitive dependencies.
Measure the selected route build separately. No candidate packages were installed.

| Package | Latest observed / release date | License | Unpacked MB |
|---|---|---|---:|
| mafs |0.21.0 /2024-10-20|MIT|0.45|
| jsxgraph |1.14.0 /2026-10-05|MIT OR LGPL-3.0-or-later|74.84|
| @xyflow/react |12.12.0 /2026-09-24|MIT|1.22|
| cytoscape |3.34.3 /2026-09-07|MIT|5.70|
| plotly.js |4.1.2 /2026-10-05|MIT|98.39|
| d3 |7.9.0 /2024-03-12|ISC|0.87|
| @motion-canvas/core |3.17.2 /2024-12-14|MIT|0.87|
| wavesurfer.js |8.0.2 /2026-10-07|BSD-3-Clause|1.57|
| butterchurn |2.6.7 /2019-03-12|MIT|0.73|
| p5 |2.3.4 /2026-09-25|LGPL-2.1|17.43|
| three |0.186.1 /2026-09-24|MIT|20.44|

Mafs/Motion Canvas/Butterchurn release age warrants compatibility testing before
expansion; mature D3 modules can be stable without frequent umbrella releases.
Manim Community: MIT, current official docs show0.22.0; separate Python/native
installation size not measured. LiaScript: BSD-3-Clause per repository LICENSE;
`@liascript/core` registry lookup failed, so no invented npm version/size. Resolve
its pinned export build before integration. Keep engine and authored-content licences
separate; retain notices. Authoring tool maintenance is not evidence of lesson quality.

## Unified representation proposal

Versioned `visual.v1` envelope attached to exact LearningObject ID/version, skill ID
and objective/success-criterion IDs. Discriminated kinds: relationship, coordinate,
data_plot, signal, spatial, reviewed_animation. Each kind has a bounded typed payload,
explicit units/domains, deterministic initial state, allowed interaction IDs and a
text equivalent. No eval, arbitrary functions, HTML/SVG strings or remote loaders.

Provenance includes source document/version/chunk/hash references, authored synthetic
fixture designation when applicable, creator/reviewer, model_call/prompt version only
if generated, renderer version and content hash. Never fabricate source IDs for demos.
For cached animations include reviewed script hash, toolchain version, seed, asset
hashes and captions/stills; regenerate explicitly, never on learner page load.

Validate server-side with strict Pydantic plus client renderer checks: unknown kinds
fail to text fallback; finite numbers, node/edge/sample limits, endpoints, units and
kind-specific semantics. Cycles can be meaningful; do not enforce DAG on every graph.
Source currency invalidates eligibility for reuse without deleting authored history.
Keep immutable authored versions separate from deletable Representation caches.

Assessments record explicit answer/criterion/version only through existing kernel
paths after integration; clicking, watching or moving controls is not mastery. This
prototype supplies deterministic practice feedback without persisting competency.
Compare text-only with interactive versions using matched transfer questions and
learner comprehension; time on screen and attractive screenshots do not prove gains.

## First prototype contract

React Flow, fixed train/test information-flow graph with selectable fitting scope.
Synthetic train values2,4 and held-out values10,12: training mean3, combined mean7.
Changing held-out values must not change a training-only mean. This is mean-centering,
not full StandardScaler or a measured accuracy experiment. Explain fit versus transform.
Transfer check asks where to learn an imputation statistic on a new medical dataset;
feedback addresses information leakage, not button matching. Source: the
[scikit-learn common-pitfalls guide](https://scikit-learn.org/stable/common_pitfalls.html#data-leakage).

Prototype is independent of live curriculum, clearly synthetic, no invented skill IDs.
Later integration binds the same envelope to real learning objects after review.
Required evidence: numeric invariants, malformed-spec fallback, interaction/assessment,
keyboard, narrow/desktop, reduced-motion, visual inspection, build/chunk size and
code/pedagogy review. Human screen-reader/comprehension acceptance remains separate.
