# Usability review: verified actions and remaining work

The owner-supplied review of the focused static capture is a usability input. Verify findings against current code and visible browser states before changing behavior. Counts extracted from serialized DOM can include hidden panels; they do not by themselves measure visible cognitive load. Clinical research summaries in the review are not individual learner facts or validated evidence of a product benefit.

The immediate priorities are a single active learning task, low-effort help before grading, clear start/skip decisions, one shared audio-settings surface, and consistent names. Preserve explicit learner control, saved writing, full histories, factual provenance and meaningful grading evidence.

## Implemented in this slice

- Explicit uncertainty such as “I don't know” offers help without submitting an assessment. Writing stays intact. The learner can focus the hint controls or explicitly check the answer as written; short substantive answers remain checkable.
- Earlier blocks passed over by the recorded start are labelled skipped at start. The current activity states which block was started. Do not invent a “nothing due” reason when the stored reason is a chosen later start.
- Reader/voice widgets use shared audio settings instead of duplicating the panel in the session. Playback controls remain available. Device guidance uses system settings rather than assuming macOS.
- Initial submission progress does not display the lost-submission recovery panel. Recovery identities and actual failed/lost-result controls remain intact.

## Remaining priorities

1. Continue refining optional AI-help and notes inside the lesson; secondary tools are now grouped under More session tools, with critical recovery retained outside.
2. Continue integrating imports and saved-work browsing into Library and aligning vocabulary; six-destination navigation and canonical three-group Library search are implemented, with legacy URLs and recovery scopes retained.
3. Authoring setup is shared between Settings and the writing workspace, replacing the duplicate generic switch/cents slider. Both views explain that distinct permissions/caps count the same app-wide hosted usage. Further authoring simplification remains open.
4. Verify the draft preview, pluralisation, browser titles, area/upload linking, confidence visibility, comfort dismissal, and other copy/heading findings against live states.
5. Design a low-effort material path without automatic activation or loss of the optional research workflow.
6. Reduce repeated explanatory caveats at decision points without suppressing provenance or uncertainty.
7. Review progress/recap language and visible evidence thresholds without rewriting historical learning evidence.

The broader information-architecture redesign and the entire review are not marked complete. This slice does not change kernel grades, mastery formulas, histories, model routing, hosted budgets or automatic adaptation policy.


## Navigation and session composition continuation

Primary navigation now has six labelled destinations: Home, Library, Progress, Projects, Ask and Settings. Library groups authoring, saved answers and source access; Progress links the knowledge map and area exploration; Settings groups advanced setup and optional tools. The palette retains secondary destinations with one entry per URL. Existing routes, browser history, learner IDs, saved-writing keys and bookmarks stay intact. Visual-learning and task-review browser titles are explicit.

The session puts lesson context, plan/energy controls, optional code work, alongside work and experiment links under one More session tools disclosure. Native details keep content mounted, preserve writing and avoid restarting work on toggle. The view remembers its open state for that session in the tab; new sessions begin closed. Optional alongside activity is inactive while the disclosure is closed. Critical pause/end controls, the active reader/check, real request-recovery notices and timer actions remain reachable outside that tools disclosure. This is a composition change, not a curriculum, grading or model policy change.

Remaining work includes broader authoring/Library consolidation, one search, fewer repeated caveats, quick material creation, scoped hosted-settings clarity and the other findings above. The lesson's optional AI-help and notes composition still warrants further review; do not describe the entire usability review as completed.


## Canonical Library search

Library now has one local query box and three result groups: My material (personal drafts and active lesson titles), Saved answers, and Source passages. Recent personal drafts appear before searching. Source inspection keeps the result/query state mounted and restores keyboard focus on close; legacy search/source URLs redirect with their query and passage identifiers intact. The command palette uses the same canonical search and no longer lists duplicate search destinations.

Results retain independently retryable errors and explicitly marked cached data. Retired project-guide manifests are not queried. Project/notebook edits, unsaved writing and the web are outside this search scope, stated in the optional details. Long result citations are shortened for scanning while full citation and context remain in the viewer; long unbroken filenames wrap without horizontal page overflow. Imports and specialist saved-answer views remain under the secondary disclosure. This is search consolidation, not a claim that every personal data store is indexed.


## Authoring and hosted-spend clarity continuation

Settings uses the existing shared authoring form instead of exposing a second generic authoring switch
and raw cents slider. The writing workspace keeps the same form. Saving a key remains a separate
explicit action and does not enable a provider or spend money. Models labels the ordinary-study cap
and links to Settings; both surfaces explain that caps count the same app-wide hosted usage, not
additive allowances. Existing permissions, accounting, saved credentials and histories are unchanged.
An unavailable setup read displays unknown status with retry, rather than implying local mode or
zero spending. Reads have a bounded deadline; cached settings are labelled stale on failure and
writes stay disabled until a successful read. A stored zero cap displays zero and remains zero when
local authoring is selected. This is not a broad model-quality or billing-system redesign.


## Learning-evidence continuation

The owner's [supplied evidence review and seven-point audit](2026-10-31-LEARNING-EVIDENCE-AUDIT.md)
are reconciled in ADR 0022. Optional maintenance plans, explicit next-start cues and condition
observations extend the existing stable interfaces; they do not add automatic diagnosis, sensory
activation, shame mechanics or inferred treatment effects. Historical progress and preferences
remain intact. Actual controlled sensory comparisons and human accessibility/learning outcomes are
still open; the supplied review is not presented as a blanket clinical certification.
