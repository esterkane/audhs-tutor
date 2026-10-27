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
2. Continue Library/search consolidation and vocabulary alignment; six-destination primary navigation and grouped secondary links are implemented, with bookmarks and recovery scopes retained.
3. Reconcile the scoped authoring cap/status with ordinary hosted-study settings; keep separate permissions and budgets truthful.
4. Verify the draft preview, pluralisation, browser titles, area/upload linking, confidence visibility, comfort dismissal, and other copy/heading findings against live states.
5. Design a low-effort material path without automatic activation or loss of the optional research workflow.
6. Reduce repeated explanatory caveats at decision points without suppressing provenance or uncertainty.
7. Review progress/recap language and visible evidence thresholds without rewriting historical learning evidence.

The broader information-architecture redesign and the entire review are not marked complete. This slice does not change kernel grades, mastery formulas, histories, model routing, hosted budgets or automatic adaptation policy.


## Navigation and session composition continuation

Primary navigation now has six labelled destinations: Home, Library, Progress, Projects, Ask and Settings. Library groups authoring, saved answers and source access; Progress links the knowledge map and area exploration; Settings groups advanced setup and optional tools. The palette retains secondary destinations with one entry per URL. Existing routes, browser history, learner IDs, saved-writing keys and bookmarks stay intact. Visual-learning and task-review browser titles are explicit.

The session puts lesson context, plan/energy controls, optional code work, alongside work and experiment links under one More session tools disclosure. Native details keep content mounted, preserve writing and avoid restarting work on toggle. The view remembers its open state for that session in the tab; new sessions begin closed. Optional alongside activity is inactive while the disclosure is closed. Critical pause/end controls, the active reader/check, real request-recovery notices and timer actions remain reachable outside that tools disclosure. This is a composition change, not a curriculum, grading or model policy change.

Remaining work includes broader authoring/Library consolidation, one search, fewer repeated caveats, quick material creation, scoped hosted-settings clarity and the other findings above. The lesson's optional AI-help and notes composition still warrants further review; do not describe the entire usability review as completed.
