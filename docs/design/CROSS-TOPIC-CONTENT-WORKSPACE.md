# Cross-topic question workspace and original learning content

Status: owner requested2026-10-12; architecture/implementation plan. Not delivered.
This adds a clear path for asking across areas and building a reusable local learning
library. It does not replace the learning kernel or remove existing source material.
The accepted owner-only transmission/public-export policy remains a prerequisite.

## Existing implementation to reuse

- `features/programs/StudyTutor.tsx`: explanations, question/chat actions, remembered
  conversations, saved-answer preference, narration/dictation and request recovery.
  It currently requires a learning session. Do not create one silently just to chat.
- `routes/Answers.tsx`, `/api/answers`: learner-scoped saved answers, search/filter,
  source-status disclosure, feedback and linked follow-ups.
- `orchestrator/playground.py`, answer memory/reuse services: source context,
  conservative reuse, existing provenance and saved-answer identities. Reopening
  saved work has no inference/evidence side effects. Retrieval is not validation.
- `visual-learning-binding.md`: validated relationship specification and exact
  source/lesson bindings. Authored lifecycle and lesson rendering are still open.
- Existing local voice, shared controls, diagram/resource curation and UX/reliability
  skills remain authoritative. No additional libraries are needed for the first phase.

## Learner flow

1. Open **Ask the tutor** from Home or the existing tutor entry. Asking does not
   require starting a scheduled lesson or changing the current learning topic.
2. Optional area selection (including All areas); type a question. Debounced local
   suggestions show actual saved questions and clearly identified curated starters.
   Choosing a suggestion fills the composer; it never sends, switches a session or
   generates an answer automatically. Existing relevant answers can be opened directly.
3. Submit once. Show retrieval/generation/checking states, streamed text, Stop and
   honest save status. Give a substantive explanation before any optional questions.
4. Present the answer, concrete worked example, assumptions and limits. Optional
   **Show the method**, **Simpler**, **More detail**, **Ask a follow-up**, **Show visually**
   and **Listen** remain contextual rather than competing initial requirements.
   The method is a useful worked derivation/explanation, not purported hidden reasoning.
5. References identify which claims they support, source type, version/check date,
   and whether they were actually inspected. Include useful free-to-access primary
   docs/resources when available. Never invent links or call them free/open-licensed
   without evidence. Separate source availability from reuse/transmission rights.
6. Save completed replies and follow-ups locally with links to the original question,
   areas, sources, checks, model/prompt versions and lineage. Partial replies stay
   labelled partial; no partial/error result becomes a trusted reuse candidate.
7. Offer a short optional understanding/application question, with a way to answer,
   receive grounded feedback and ask for help. Reading/liking/saving is not mastery.

## Accuracy and reuse contract

- Identify supported claims, contradictions, uncertain/current facts and limitations.
  Deterministic calculations/code checks use bounded local tools when appropriate;
  external facts use inspected supporting sources with dates. A second model pass
  is a model check, not independent factual verification or a guarantee.
- Use task-specific statuses: unchecked, source-supported, calculation-checked,
  model-reviewed, disputed, outdated. Store what was checked and what was not.
- Search before generation; prefer relevant high-quality, current saved answers.
  Exact safe reuse can reopen the original; near matches are offered as related
  material or used with disclosed provenance, not silently substituted for this query.
- Negative feedback, outdated sources, changed question/context and incomplete
  lineage prevent automatic trusted reuse. Preserve history and allow explicit
  fresh generation; never overwrite a reviewed answer silently.
- No model call per keystroke. Scope suggestions to the learner; bound and debounce
  local queries, cancel stale responses, label provenance and use accessible listbox
  behavior. Empty results are not a reason to fabricate previously answered questions.

## Origin/privacy boundary

Only owner-created, explicitly reviewed, version-bound content may leave the local
app for hosted inference/public export. Third-party course material, mixed/unknown
inputs and cached/generated derivatives stay local. Evaluate the complete assembled
request, including prompts, rubrics, sources, code, outputs and conversation history.
A typed owner question does not make its attached context eligible. Do not remove
needed context silently to gain permission. Keep local-first and spending limits.
An answer generated from third-party passages stays source-derived; generation,
paraphrase, attribution or a subscription does not clear that restriction.
External references may be opened/fetched under existing local resource controls;
their text does not become eligible for hosted transmission by being publicly readable.

## Ordered implementation slices

### G0 — Enforce source containment
Follow `material-rights-contract.md`. Gate external provider entry points, fallbacks,
repairs, streaming and direct benchmarking/embedding paths before transmission or
budget reservation. Unknown stays local; no untrusted caller-authorship flag.
Introduce version-bound origin/lineage evidence before enabling owner-only external
requests. Separate private backup/download from an explicitly public export.
Acceptance: zero external calls for third-party/mixed/unknown data, retained complete
local context, clear recoverable policy reason, cache ancestry/revocation tests.

### G1 — Session-independent Ask workspace and local suggestions
Design one small `/ask` workspace using existing tokens and composer components;
place entry in existing navigation hierarchy, without redesigning unrelated screens.
Define learner-owned conversation/turn identity separate from session/FSRS state.
Preserve optional area/question draft, explicit selection, original request identity,
Stop and recovery. Add a bounded local saved-question suggestions endpoint only if
existing answer search cannot provide the required fields safely. No model typing calls.
Acceptance: no session needed; no current-session change; stale queries, duplicate
submit, reload, denied storage, keyboard/listbox, mobile and no-results all verified.

### G2 — Detailed grounded answer and explicit checks
Reuse orchestration/save paths with full lineage; separate generation from check
records so one failed check retains a usable labelled answer. Support deeper method,
worked examples, follow-up and shared local voice controls. Add inspected free
reference cards and per-claim source links with network failure handling.
Acceptance: poisoned source text, invented citation/link, incorrect numeric example,
conflicting/stale sources, interrupted generation/check/save and no-source answers.
Test factual quality on a small owner-reviewed cross-area question set; disclose
which checks are synthetic fixtures and which use real local models/material.

### G3 — Reuse and content review
Rank saved candidates by relevance, scope, source currency and explicit quality
feedback. Show original date and why reused; retain correction/supersession history.
Add reviewable question/answer library across areas; do not conflate quality votes
with assessment results. Measure time to first useful answer, exact-cache hit rate,
false-reuse rate, factual/source defects and local/hosted cost against fresh answers.

### G4 — Visual explanations linked to the answer
Complete authored lifecycle before attaching validated visual specifications to
answer/objective versions. Begin with existing deterministic renderers and text
alternatives. Provide editable parameters, worked predictions and a checked question.
Never execute arbitrary generated JavaScript/Python to render a diagram. Bind visual
claims to sources and check mathematical/conceptual correctness, not just parsing.

### G5 — Build original lessons and replace dependencies deliberately
Promote reviewed answers into draft learning objects with objectives, prerequisites,
examples, exercises/rubrics and source lineage. Explicit learner review/activation
remains required. Track replacement coverage by objective and tested project tasks;
retain links to historical evidence. Do not delete course material automatically.
Only remove a local dependency after replacement content passes quality/coverage
review and the owner explicitly approves removal.

### G6 — Optional explanatory video
Use reviewed local storyboards/validated scene specifications, deterministic rendering
where possible, cached artifacts keyed by content/renderer versions, captions,
transcript and reduced-motion/static alternatives. Rendering must be stoppable and
must not block text learning. No arbitrary model-generated executable scene scripts.
Evaluate existing animation candidates already retained in the research specs;
do not install all libraries. A video is not automatically more educational than
an interactive diagram. Measure understanding and transfer with an actual task.

## Verification and handoff

Use audhs-learning-ux, audhs-state-reliability, audhs-tutor-evidence,
audhs-resource-curation and audhs-visual-specs for their relevant slices. Follow
feature-slice code/pedagogy reviews. Each slice reproduces its problem first, runs
relevant unit/integration/browser checks, inspects visuals and keyboard/responsive
behavior, and records open human/AT gates. Preserve existing source acquisition work.
Batch paired publication after verified slices; both repositories remain private.

Current evidence: repository audit only. No new question workspace, reference-fetch
provider, automated fact checker, generated video or content deletion is implemented
by this plan. Next: G0 containment, then G1; reuse existing capabilities rather than
introducing another generic chat backend.

2026-10-12 checkpoint: G0a model-provider transport containment implemented; see
../slices/source-transport-containment.md. G0 remains open for image/speech paths
and origin/export evidence; G1 has not started.

2026-10-12 follow-up: G0b image/speech endpoint containment delivered; see
../slices/media-source-containment.md. All new Ask work must remain local; hosted
owner-only eligibility and public-export rights are still unavailable. G1 is next.

2026-10-12 current checkpoint (supersedes earlier status): G1 independent Ask is
implemented, migrated and pushed separately to both private variants. See
../slices/ask-workspace.md for validation and limitations. G2 is in progress:
../slices/ask-grounding.md describes the exact answer/passage check contract.
Claim binding is not factual validation; no G2 UI or automated checker is live yet.
G0 version-bound hosted/public origin eligibility and G3–G6 remain incomplete.

2026-10-12: G2a bounded local passage review is verified and locally migrated; see
../slices/ask-grounding.md. Explicit selection, local model claim proposals,
unchanged/historical bindings, newer-version disclosure, saved review/recovery and
source trust/displayed-text gates are implemented. G2 web references, grounded
original generation and broader factual-quality evaluation remain open.

2026-10-12: G2b curated further reading and Home Ask discovery delivered;
G2c explicit local source attachment implemented, with exact snapshots and separate
model-review labels. See ../slices/ask-further-reading.md and
../slices/ask-selected-sources.md. External-source snapshots and broader factual-quality
acceptance remain open; a synthetic conflict case still showed unsupported inference.

2026-10-12: G2d explicit local reference copies implemented. Further reading now
supports Save/Refresh, plain-text preview, then separate Add to local library.
Fixed documentation URLs only; no question-derived requests, no credentials,
no automatic indexing or learning evidence. Third-party text remains local.
See ../slices/reference-snapshots.md for transport, integrity, review and test evidence.
Broader factual-quality acceptance and G3–G6 remain open. Both repository variants remain private.
