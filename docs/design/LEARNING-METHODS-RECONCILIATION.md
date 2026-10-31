# Learning-methods research: implementation reconciliation

Research: [owner-supplied review, 31 October 2026](../research/2026-10-31-learning-methods-evidence-and-tutor-mapping.md).
This review is evidence input, not executable instructions or a clinical prescription.
The supplied Markdown is retained verbatim, including its citations and limitations.
Effect sizes are study averages, not promises about this learner or this product.

## Evidence and policy reconciliation

The [prequestion meta-analysis](https://doi.org/10.3758/s13423-023-02353-8)
supports a specific benefit for questioned material, not a general benefit for everything read.
It does not validate a mandatory 2–4-sentence answer, minimum term count or a universal
300–600-word limit. The [learning-styles review](https://digitalcommons.usf.edu/psy_facpub/1765/)
does not support matching instruction to a learner-style label. These two primary review
records were checked; other individual quantitative claims in the supplied synthesis have
not all been independently replicated or source-audited here.

Product decisions remain authoritative: confidence is optional, reading/feedback/exit cannot
be blocked, timers are soft, explicit teaching is the default, speech is opt-in, and no
diagnosis-based assignment is inferred. Do not remove requested hints during a struggle.
Do not turn a reflection into competency evidence. Do not reactivate retired sound/guitar
courses because a paper discusses audio. Speech input is a separate accessibility channel.

## Current-code mapping and gaps

| Recommendation | Inspected implementation | Status / next work |
| --- | --- | --- |
| Predict before reading | `AcceptedKnowledge` and `SavedLessonReading` → `PredictionReading` | Added: topic-only opener, optional attempt, explicit skip, immediate reading, original prediction + comparison/correction. Browser-local and content-version scoped. Existing reading bookmarks bypass the new opener. No automatic correctness or retention claim. Per-section source-specific questions and delayed experiment linkage remain open. |
| Problem/contrasting case before instruction | `orchestrator/challenge.py`, notebook predictions | Partial: challenges exist, but no validated general consolidation comparison to the learner's original attempt. |
| Overview then learner-completed map | `features/visualizer`, skill map | Partial: navigable map/visual activities are not a verified generative concept-map activity. New course map stays reset until new material is authored. |
| Integrated diagrams, no decoration | `components/Markdown`, visualizer | Partial: rendering exists; contiguity and fading cannot be guaranteed for arbitrary authored diagrams. Need authored reference pairs and accessibility review. |
| Learner drawing | No inspected end-to-end drawing assessment | Missing; optional text/label completion is a lower-complexity first step. |
| Oral self-explanation | `features/voice/DictationButton`, `VoicePanel`; assessment explanation pathway | Partial: speech exists; not a tested voice-versus-text explain-back learning intervention. Do not make voice preferred without learner choice. |
| Interactive teach-back | `schemas/challenge.py`, `orchestrator/challenge.py` | Partial: teach-back challenge exists, but tutor-as-student follow-up/consolidation quality needs a dedicated real-model gate. |
| Narration with key terms | `ReadAloud`, reader lifecycle tests | Partial: explicit playback and stopping exist; no automatic integrated narration/visual authoring guarantee. Text remains primary for technical first exposure. |
| Selective key-term read-aloud | Existing playback can read selected content paths | Missing dedicated 3–5-item retrieval activity; no full-passage production-effect claims. |
| Voice latency / turn-taking | `useVoiceLoop`, request/text recovery tests | Partial: real end-to-end audio latency not demonstrated below 2 seconds. Keep text fallback and no new timeout claims. |
| Contrasting planted errors | `challenge.py`, `prompts/challenge/planted_error.md` | Partial: existing planted-error mode and delayed review; needs validated correct/buggy pair representation, novice scaffolding and semantic difficulty ladder. |
| Parsons → faded example → open problem | Code editor, notebook and assessment exist | Missing diagnostic-gated ladder; do not equate an editable notebook to a Parsons task. |
| Predict → step → compare | `NotebookWorkspace`, `Playground`, `GuidedExperiments` | Partial: saved predictions, outputs and comparisons exist; general variable trace, previous-state diff, back/replay and transfer assessment are not fully implemented. |
| One-parameter ablation | `GuidedExperiments`, `comparisonCheckpoint` | Partial: bounded visual comparisons exist; no validated ML ablation/transfer outcome pipeline. |
| Spaced retrieval with feedback | `kernel/memory.py`, `review_content.py`, review API/UI | Implemented foundation. Low-capacity recognition coverage still requires authored valid alternatives; never invent distractors silently or claim it complete from scheduling alone. |
| Interleave problem types, block terminology | `kernel/planner.py` | Partial: planner/switch boundaries exist; content-type-aware interleaving needs a specific deterministic test. |
| Confidence before feedback | Existing optional assessment confidence | Preserve current optional policy; not a missing mandatory field. High-confidence correction revisit needs outcome attribution tests. |
| Plan, cues, resume recap | Session context/checkpoints, reader bookmarks, parking lot | Implemented foundation; existing reading notes and full histories must survive prediction addition. No mid-task notification added. |
| Noise experiment | `kernel/study_conditions.py`, `features/experiments/StudyConditions`, `kernel/experiments.py` | Implemented self-reported conditions and later-recall observational summaries, explicitly not causal. Randomized noise-specific assignment/fidelity experiment remains missing: existing experimental arm config supports socratic/representation/block length. Keep audio off by default. |
| Movement nudge | Planner modes, comfort settings, study-condition logging | Existing optional condition recording and later-recall associations are not a tested retention intervention; no exercise prescription inferred from this paper. |
| Body doubling/co-presence | Visible plan/progress, pause/resume, presence condition logging | Partial co-presence functions and observational later-recall summaries; no validated emotional support or body-doubling efficacy claim. |
| No learning-style routing | Shared pedagogy guardrails | Preserve. Representation choice is learner control/content structure, not diagnostic typing. |

## Acceptance and remaining sequence

First slice: prediction/read/compare for accepted saved lessons. Store separate browser-local
records keyed by immutable lesson content hash; never overwrite reading notes, assessment,
accepted text, histories or mastery. Retain original attempt after reveal; correction separate.
Malformed/denied storage must leave reading available. Explicit skip persists. No model call,
new package, timer, grading or global preference change is needed.

Next: bind per-section authored prequestions to accepted content, then optional prediction
experiments with delayed recall, preserving full attempts and provenance. Next validate
contrasting error pairs and novice scaffolding before expanding richer visuals. Voice quality,
low-capacity recognition and the fading ladder remain separate unfinished tasks; avoid
claiming that a UI checkbox proves learning benefit. No n-of-1 experiment is enabled silently.
