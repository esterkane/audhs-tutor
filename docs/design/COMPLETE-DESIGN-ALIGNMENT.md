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


## Tutor composer consolidation — 2026-10-11

Question field precedes Send in DOM/keyboard order. Once content exists the panel
is labelled Ask the tutor rather than Your explanation. Hint/Summary retain their
handlers but share More ways to explain with representations; the initial empty
state retains its help disclosure. The two placements are mutually exclusive.
No prompt, learning-state or narration changes.

Evidence:6 layout journeys pass at320/390/1280 light/dark, including revised input→
Send keyboard order;6 representation/recovery journeys also pass.10 Session tests
verify one help location, retained handlers and draft recovery. Lint/type/build and
code/pedagogy reviews pass. Narrow initial screenshot inspected. Existing large-bundle
warning remains. These checks do not establish human comprehension or full PDF fidelity.

### Next layout contract (not implemented)
The p9 desktop context column/mobile sheet crosses the stateful SessionControls and
SessionBody boundary. Do not duplicate either owner into responsive variants: that
would create two stop/mark mutations and risk losing drafts on resize. Keep lesson
and assessment owners mounted, show compact goal/concept/activity context, keep Pause
and Focus directly reachable, and expose supplementary controls in one responsive
container. A mobile sheet must return focus, close with Escape and preserve state on
resize/navigation; focus mode must retain its explicit exit. Verify idle/running/
failed stop, label undo, assessment drafts and stream continuity before publication.
Activity index is not an invented lesson-step count. The current inline context
remains until this complete responsive contract is implemented and verified.


## Responsive context implementation — 2026-10-11

The previous layout contract now has a bounded implementation: compact persisted
concept/activity context stays with existing Pause/End/Focus/label controls. A single
read-only full context panel occupies the desktop side column (80rem breakpoint),
or an explicitly opened native flyout on narrow screens/in Focus. Unsupported
popover browsers receive inline context. No duplicate mutation owners, remounted
lesson/assessment owner, invented step count or new dependency. Semantic color,
border/radius and existing navigation-width tokens are reused.

Resize closes the flyout and moves focus to the visible title/trigger only when
context held focus; Focus-mode restoration uses its effective layout. Escape and
Close return focus. Tests retain an unsent question through multiple breakpoints
and through open-flyout resizing in Focus mode. Compact/full regions have distinct
accessible labels. The context stays sourced from the recorded active skill.

Evidence:10 final layout/typography browser checks pass across320/390/1280,light/dark
and enlarged text, plus6 earlier Focus/recovery checks.14 Session/context component
tests, lint/type/build and reviews pass. Desktop/sidebar, narrow and dark-flyout
screenshots inspected. The review's hidden-focus resize issue was fixed and tested.
Remaining: actual screen-reader/browser-zoom/human acceptance and broader design
inventory; the flyout is nonmodal, with native light dismissal. Unsupported-browser
inline fallback has source/unit evidence, not a separate real-browser run.


## Focus secondary panels — 2026-10-11

PDF p11: Focus hides plan/energy controls, planner proposals, saved-history panels,
previous reply, Work alongside and coding-workspace launchers without unmounting
them. Current content/notes, help, sources, composer and exits remain available.
The embedded ambient owner stops pending/playing audio while hidden; returning never
autoplays. Its optional timer/state remain mounted. Focus uses the existing896px
reading measure rather than the wider desktop context-grid measure.

Evidence:4 Focus/Alongside browser cases pass, with both Focus cases rerun after
adding the width assertion. They cover retained open panel/draft, Escape/dialog
focus, saving, audio stop, reload/Back, enlarged text and reduced motion.15 component
tests include pending audio stopped during hiding and silent return. Lint/type/build
and code/pedagogy reviews pass. Desktop/narrow Focus screenshots inspected.
The17-route audit found no automated violations/overflow, but incomplete checks and
human/assistive-technology acceptance remain; see the adversarial report.


## Adaptation choice clarity — 2026-10-11

PDF pp11–12: suggestions now distinguish Try for this session, Make this my default,
Not now and suppression, with technical preference details in a collapsed disclosure.
Existing decision payloads, learning policy and undo semantics remain unchanged.
History distinguishes loading, failure, empty and loaded states; failed undo retains
the visible record and offers retry. Decision failures stay beside their proposal.

Evidence:3 component tests, targeted lint and production/type build pass;2 browser
journeys at390/1280 cover keyboard disclosure/choice, failed undo and successful retry,
and no horizontal overflow. Both screenshots inspected; code/pedagogy reviews clear.
The initial browser locator targeted the summary label span; fixed to focus the native
summary and reran successfully. No learning-policy change or new dependency.
Remaining: complete adaptation-dialog blueprint, dark/large-text acceptance for this
slice, human comprehension and assistive-technology review; not full PDF conformance.


## Practice feedback evidence order — 2026-10-11

PDF p10: Session assessment feedback now groups existing passed criteria under What
was right, then unmet criteria under What to reconsider, then the existing explanation
and qualified misconception under Why. Empty groups are omitted rather than inferred;
absent criteria receive an explicit no-breakdown notice. Grader evidence stays verbatim.
The mastery estimate moves into the existing collapsed grading-details disclosure;
review date stays visible. No grading, scheduling, save/recovery or progression changes.

Evidence:2 baseline recovery journeys and2 final390/1280 keyboard/responsive journeys
pass;13 Session/evidence component tests, targeted ESLint and production/type build pass.
Desktop/narrow screenshots inspected; code/pedagogy reviews found no blockers/majors.
Synthetic browser grading checks presentation only; the mismatched fixture assessment
ID was rejected by the existing guard, corrected, and the journeys rerun.

Remaining: PDF outcome-based Try again/Next and the full secondary help choices require
an explicit retry contract: currently Continue advances a block and Try another question
fetches a different item. Do not relabel those as retrying the same answer or silently
change learning evidence. Next inspect assessment retry/idempotency semantics before
implementing that interaction. Source citations and other grading surfaces also remain
to reconcile; this slice does not claim the whole Practice blueprint. Human/AT, dark
and enlarged-text acceptance for this presentation remain open.


2026-10-11: Same-question retry requires an explicit assisted-practice contract: current new attempts update competency and FSRS, and hint count alone does not change competency weighting. Runtime unchanged; next implementation boundary and recovery/evidence gates documented in docs/design/PRACTICE-RETRY-CONTRACT.md. Two backend replay/concurrency tests pass (local deterministic fixtures, no model calls).


2026-10-11: Revision provenance foundation implemented (ADR0020): new attempts record stable content identity; nullable original-attempt relationship and read-only root validator added.32 migration/recovery/root and19 backup tests pass; mypy/Ruff and reviews clear. Legacy provenance stays null. No revision endpoint/UI or changed evidence policy yet; next connect serialized application and replay before exposing controls.


2026-10-11: Explicit revision application saves immutable linked attempts/feedback without a new competency/FSRS update; replay and failed-commit recovery covered, experiment metrics exclude flagged revisions.57 backend,13 component,2 browser checks and types/lint/build/reviews pass. Missing-parent classification and retry UI remain; details in docs/design/PRACTICE-RETRY-CONTRACT.md.


2026-10-11: Omitted-parent repeats now classify server-side under the write lock; concurrent requests create one original and one revision, preserving raw recovery identity.1141 backend tests pass; shared notices across result surfaces, component/browser/type/lint/build/review gates pass. Retry editing/actions remain next. See docs/design/PRACTICE-RETRY-CONTRACT.md.


2026-10-11: Assessment selections use semantic accent-tint plus the existing pressed
ring, leaving Check my answer as the filled primary action (PDF pp2/10). Other
Choice uses remain unchanged. Two real-API revision browser journeys pass at390
light/1280 dark, with keyboard/edit/reload/cancel/submission checks; screenshots
inspected.10 Session tests, lint/type/build and code/pedagogy reviews pass. Existing
large-chunk warning remains. Full secondary feedback-help controls and broader
Practice/Progress design acceptance remain open; grading is unchanged.

## Progress inspectability in progress — 2026-10-11

PDF p10 evidence inspection: records previously said Linked assessment attempt with
no route to inspect it. A learner-scoped read-only join now exposes an optional saved
answer ID, and Progress links to its existing saved-assessment page. Missing records
are explicitly unavailable; no level, independence or competency policy changes.
Three backend tests and two320/1280 browser journeys pass, covering owner isolation,
cardinality, keyboard-focusable link, missing records, pagination error/retry and
concept Back navigation. Backend/frontend types and lint pass; code review clear.
Still pending: destination navigation verification, visual inspection/build and final
pedagogy review/publication. Inherited acquisition changes remain outside this slice.


2026-10-11: Progress evidence now links to owned saved assessment feedback; unavailable
records are explicit. Read-only learner-scoped joins preserve pagination/counts.3
backend tests,4 final browser checks (Progress320/1280 plus assessment history),
types/lint/build and reviews pass. Keyboard link navigation opens saved feedback;
browser Back returns to the selected concept. Narrow full-page screenshot inspected.
Existing large-chunk warning remains. Historical help-selector test updated to the
new Explain the difficult part label. No competency or independence interpretation
changed. Broader human/AT and Progress evidence-level design acceptance remain open.

2026-10-11 Explore inspection: current /areas is authoring-first, conflicting with
PDF p10's concept/outcome-first learner navigation. Two baseline browse-area journeys
pass (390/1280), confirming browsing is separate from learning selection. Recorded
route/data/dirty-edit invariants in EXPLORE-LEARNER-CONTRACT.md before structural
changes. Next inspect exact activated-concept membership and implement the learner
entry without replacing the authoring workflow. No runtime changes in this step.

2026-10-11 follow-up: five shell/header navigation checks pass after the Explore route
change. Global Browse area still had a small native summary target; switched only
that summary to the existing DisclosureSummary primitive, retaining its details owner,
open state, browse store and authoring-specific destination. Two updated390/1280
browser checks pass with measured >=44px row and keyboard opening/navigation. Lint
and TypeScript pass. Final visual/build/review/publication remain for this small
shared-component adoption; no learning logic changes.


2026-10-11: Global Browse area now uses the shared44px DisclosureSummary without
changing its native details owner/navigation.2 keyboard/responsive browser checks,
types/lint/build and code/pedagogy reviews pass; narrow open-state screenshot inspected.
5 preceding shell/header checks passed. Existing chunk warning remains. Screenshot
uses fixture area IDs without real concepts and honestly shows its loading-error
recovery; real concept/error flows were separately checked in the Explore slice.
Broader shared-control adoption and human/AT acceptance remain open.


2026-10-11: Saved-answer history now adopts the shared44px disclosure summary
(PDF pp5–7) for seven historical-context/detail controls. Native details owners,
collapsed defaults, saved content and source/grade caveats remain unchanged. Two
baseline assessment-history journeys and four final history/keyboard journeys pass
at390/1280 (light/dark); measured targets are >=44px, navigation/filter retention and
read-only reopening checked. One assessment-history unit test, lint, TypeScript and
production build pass; both screenshots inspected. Code review caught import casing,
fixed before passing build; pedagogy review clear. Existing bundle-size warning and
fixture feedback-loading error remain explicit. Other feature-owned disclosures,
real browser zoom, screen-reader and human acceptance remain open. No learning-policy
or model changes.


2026-10-11: Completed shared disclosure adoption for saved-answer correction,
reply lineage and unfinished-reply controls (PDF pp5–7). Same native owners/lazy reads,
explicit correction preference and recovery state retained. Enlarged-text test found
an actual320px page overflow: auto grid tracks and the request-type select imposed
intrinsic width. Explicit single-column tracks and a bounded select fix reflow without
clipping content. Four baseline journeys, seven final browser checks and17 component
tests pass; lint/types/build and code/pedagogy reviews pass. Keyboard open/reopen,
correction/undo, lazy reads, refresh recovery and request identity checked. Desktop
and320px/200% root-text screenshots inspected; saved-answer dark390/1280 checks retained.
Root-text testing is not actual browser zoom. Enlarged bottom-navigation labels remain
cramped at320px; record this as the next shell readability issue, not a conformance pass.
Human/AT acceptance and the existing bundle-size warning remain open.


2026-10-11: Shell enlarged-text readability (PDF pp6–8): mobile navigation wraps
whole destination labels into rows instead of breaking words in five fixed columns.
Tools/Preferences also wrap without fragmenting labels. A cleaned-up ResizeObserver
reserves measured fixed-navigation height plus spacing; scroll padding protects content
from its variable height. Same five links/order/current state, no learning logic changes.
Three baseline shell journeys, eight integrated shell/saved-followup journeys and three
final shell checks pass (320/390/1280, keyboard, Back/Forward, Tools/Escape,200% root
text, size restoration). All labels stay single-line with >=44px targets; padding covers
nav height. A320x568 enlarged-text check confirms scrolled content remains above the
fixed bar; screenshot inspected alongside narrow layout. Lint/types/build and both
reviews pass. Root text is not browser zoom; actual zoom, screen-reader and human
acceptance remain open. Existing bundle-size warning remains.
