# Complete design-system alignment — 2026-10-11

## Authority

The owner explicitly requires the newly supplied complete design-system PDF to guide
implementation. Treat it as the current consolidated target alongside the earlier
owner-approved design uploads. Where older local recommendation/rejection notes conflict
with this target, they are historical, not permission to substitute another design.
Preserve functional, accessibility, offline and learning-state requirements; document a
specific conflict instead of silently departing from the PDF. Embedded source audit
claims are historical evidence, not proof about the current application.

Original PDF remains local, outside the public repository. Source: owner-supplied
AuDHS_Tutor_Complete_Design_System.pdf,13 pages; SHA-256: b4208265baae9e4b9f1583346d682b708494672e3950a1f5d39305d67340ffdb.
Read all extracted pages and visually inspected typography/layout/component pages5–7.

## Current implementation versus target

| Specification | Inspected implementation | Status / next acceptance |
| --- | --- | --- |
| Light/dark semantic palette, pp3–4 | frontend/src/index.css and brand foundation | Core palette/supporting tokens implemented; per-component use and contrast still require checks |
| Inter / Roboto Mono, p5 | Local font-face assets and provenance | Implemented; retain local delivery |
| 22px page title,16px panel title,896px page measure,2px focus, pp5–8 | Existing shared CSS tokens,56rem page bound,focus rule | Foundations exist; audit adoption, not just token existence |
| 14px UI /16px prose,13px code, p5 | Shared UI/prose/code role tokens in index.css | Foundation aligned with118% preference; representative evidence and remaining per-screen acceptance in TYPOGRAPHY-ALIGNMENT.md |
| 48px header,240/48px navigation, five mobile destinations + Tools, p6 | Five-destination sidebar/rail/bottom navigation and compact header implemented | Bounded browser evidence in HEADER-CONTEXT-CONTRACT.md; full human/assistive-technology acceptance remains open |
| Sole Home ResumeCard, p6 | Duplicate header/menu links removed | Shell aligned; Home and contextual recovery retained, see ../slices/single-shell-resume.md |
| Shared44px Disclosure,40px visual controls/44px targets, pp5–7 | Shared Disclosure in two lesson controls; existing Button | Partial: see ../slices/shared-disclosure.md; remaining disclosure/raw-control adoption open; shared Button sizing verified in ../slices/button-target-plan.md |
| ContextBar, goal→concept→step,Pause/Focus and anchored tutor, pp6/9 | Existing session cards, persistent tutor and pending goal/explanation consolidation | Partial; pending layout is an incremental reading-order fix, not completed Learn blueprint |
| Evidence labels rather than false precision, pp8/10 | Existing learning evidence and mixed progress views | Map words to real evidence; never infer demonstrated understanding from exposure or bookmarks |
| Reversible adaptation and explicit Focus exit, p11 | Existing preferences and session controls | Verify complete journey before claiming alignment |
| Motion/shadow/spacing values marked unknown, p13 | Existing tokens/source files | Do not invent source values or present recommendations as recovered specification |

## Execution order and change gates

1. Finish the pending lesson reading-order slice with retained goal,narration,Pause/End,
   keyboard and320/390/1280 layout checks. Do not call this complete design adoption.
2. Reconcile shared Button/Disclosure/Panel and typography role tokens with pp5–8.
3. Implement the shell/navigation/ContextBar direction from p6, including sole Home
   resume entry, all existing destinations and focus-mode escape. Preserve saved context.
4. Continue Home,Preferences,terminology and evidence presentation in the PDF's p12
   order; reuse implemented behavior rather than duplicate it.
5. Every affected screen needs light/dark,large-text,reduced-motion,keyboard,responsive,
   error/loading/saved-state checks. Human comprehension and screen-reader acceptance
   remain separate gates. No new learning-policy or provider changes follow from styling.

All new visual work should cite the relevant PDF page/section in its slice record and
list outstanding deviations. Use semantic tokens and existing components; introduce no
new design library merely to imitate the reference. Keep one dominant primary action,
plain factual copy,opt-in audio and visible learner exits.

Navigation implementation contract: [five-destination route map](SHELL-ROUTE-CONTRACT.md).
Practice, dated Progress evidence and state-aware Learn routes are implemented.
Five-destination navigation and the compact global header are verified in bounded
journeys; Learn ContextBar and Focus remain next. See HEADER-CONTEXT-CONTRACT.md.


## Learn content-first slice — 2026-10-11

PDF p9 requires current content before TutorInput. Browser regression confirmed
the completed explanation followed the composer. Move the existing response and
alternative content before the composer/history, without changing prompts, handlers,
state ownership or assessment transitions. Keep initial Start explanation, received
partial text, explicit Stop/retry, narration and saved drafts. Deeper-question copy
must point down to the composer. The three-action row and contextual side column
remain separate incomplete requirements; this ordering change does not complete p9.

Verified:10 isolated browser checks (320/1280, light/dark, root-text enlargement,
keyboard deeper-prompt focus with draft retention, retry/reload, partial answer,
Focus). A long pending stream confirms Stop precedes growing text and keyboard
abort retains80 paragraphs and the draft.10 Session component tests, lint and
production build pass (existing large-chunk warning). Narrow/light and desktop/dark
screenshots inspected. Code/pedagogy reviews passed after fixing Stop placement.
Streaming status/Stop remain above content; composer stays below. Physical audio,
screen-reader and owner comprehension are not established by these checks.


## Learn tutoring actions — 2026-10-11

PDF p9: current content now leads into Explain differently, Give me an example,
and Let me try (Return to your question when one exists), before the composer.
The first opens existing representation choices; the second uses the allowed
worked-example representation; the third preserves the assessment handler.
More ways to explain keeps all original representations/activity switching, and
full solutions remain a separate explicit action. Loading/unavailable/error states
are visible. A synchronous request lock rejects accidental duplicate representation
requests; failures keep content and drafts. Assessment stays available during a
stalled optional render (review finding resolved).

Evidence: prior representation flow passed before edits;11 relevant browser cases
passed, with the two representation cases rerun after expanded failure→retry→success
and duplicate-request coverage.10 Session tests pass including an indefinitely held
example that does not block assessment. Lint/build pass; narrow action screenshot
inspected; code/pedagogy reviews clear. No backend, prompt or grading changes.
Remaining: in-place replacement versus appended representations, contextual desktop
column/mobile sheet, composer/secondary-action consolidation and human acceptance.
Existing representation requests have no cancellation/deadline; this slice keeps
assessment navigation available rather than expanding the networking architecture.


## In-place explanation view — 2026-10-11

PDF p9: alternate representation now occupies the reading area instead of stacking
beneath the original. Native labelled radios switch between original and current
alternative. Both content owners stay mounted; original reading position/notes and
composer drafts survive. Hidden narration is unmounted/inactive. New tutor requests
and retries show the original response view; an intent counter prevents a late
representation from overriding a newer view/request choice. Sources, saved-answer
links and existing explicit preference comparison remain.

Evidence:6 browser cases pass for source/recovery flows; the two view cases rerun
with a held-response/manual-selection race at390/desktop and pass. Keyboard radio
switching restores notes/drafts, only one explanation is exposed, errors retain
content, and late responses retain the selected original view.29 component tests
(Session, LessonReader, ReadAloud), lint/type/build and reviews pass. Narrow screenshot
inspected. Physical audio and assistive-technology checks remain unverified.

Only the current alternative is offered in this local view switch; older saved
versions remain in answer history. This is not a new version archive. Context-column/
mobile-sheet layout and consolidation of composer/secondary controls remain open.
