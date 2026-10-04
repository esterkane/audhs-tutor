# Design system — Phase 6

2026-10-04. Specification for later prototypes and bounded implementation; production CSS is unchanged. Reuse the existing Tailwind v4 `@theme` in [index.css](../../frontend/src/index.css), shared UI primitives and sensory preferences. There is no new framework, font download or parallel component library. The [information architecture](../ux/UX-ARCHITECTURE.md) defines content priorities; tokens cannot solve unclear learning-state semantics.

## Principles

Clarity before decoration; visible state; predictable controls; context before assessment; easy return after interruption; explicit learner control; optional detail without hidden essentials; accessible behavior across input methods. Do not infer a preferred layout from a diagnosis. Confidence remains optional, bookmarking remains distinct from mastery, and sound/motion remain opt-in where currently required.

## Existing foundation and token contract

These names already exist. Use semantic utilities (`bg-card`, `text-muted`, `border-line`) rather than component-specific color literals. Existing names remain canonical; aliases are unnecessary unless an implementation proves a repeated need.

| Role | Existing token | Light | Dark | Usage |
|---|---|---|---|---|
| Page background | `bg` | `#f7f7f5` | `#15181c` | Page and secondary surface |
| Surface | `card` | `#ffffff` | `#1e2227` | Content/form surfaces |
| Primary text | `fg` | `#1f2328` | `#e6e8eb` | Required instructions, questions, body copy |
| Secondary text | `muted` | `#5b6470` | `#a0a8b3` | Optional metadata, never sole error signal |
| Decorative separator | `line` | `#d9dde3` | `#343a42` | Nonessential boundaries; not sufficient alone to identify all input fields |
| Primary action / link / current focus | `accent` | `#2f5fd4` | `#7ea2ff` | Shared accent, no new per-page palette |
| Text on accent | `accent-fg` | `#ffffff` | `#0f1a33` | Primary action text |
| Success | `ok` | `#1f7a4d` | `#5bc08a` | Actual saved/checked success with words |
| Warning | `warn` | `#a35b00` | `#e0a34a` | Recoverable uncertainty with words |

**Proposed gaps to resolve in Phase 10:** semantic error text/surface treatment; a stronger control-boundary token where shape/border is necessary to identify the control; an inline-code surface token replacing the current light/dark literal pair. Choose and verify their actual values in a component specimen before adoption. Do not recolor every decorative `line` border merely because a control needs stronger contrast. Focus currently uses accent with a 3px outline and 2px offset; retain it until rendered testing establishes a specific gap.

### Measured contrast and limits

[Token measurements](token-contrast.json) calculate opaque sRGB pair contrast from current CSS. Ratios are displayed rounded, but booleans were calculated before rounding. Foreground/background: light 14.73, dark 14.51; muted/card: light 6.00, dark 6.66; accent text on primary button: light 5.66, dark 6.99. Current tested text pairs exceed 4.5:1. Line/card is only light 1.36 and dark 1.39. This identifies a potential control-boundary issue, not a finding that every card border fails accessibility.

Use [WCAG text contrast guidance](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html) and [non-text contrast guidance](https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html) for applicable thresholds and exceptions. These calculations do not cover opacity, hover blends, disabled states, background images, graphs, code syntax or rendered combinations. Required text should meet 4.5:1; essential graphical/control identification should meet its applicable 3:1 threshold. Do not claim conformance from the palette alone.

## Typography and reading

Keep the installed system sans stack; use the existing monospace/code renderer for code and math renderer for notation. No font dependency. Standard body is 1rem, existing body line-height 1.55; long reading uses `.prose` line-height 1.75 and max-width 68ch. Preserve browser zoom and the current 118% large-text option. Do not make small text the only place consequences or errors are explained.

| Role | Proposed use of existing scale | Rule |
|---|---|---|
| Page title | `text-2xl font-semibold` | One meaningful h1 per page/state; not an h2 styled larger |
| Major section | `text-xl font-semibold` | h2 under the page title |
| Card/subsection | `text-lg font-semibold` | Heading level follows document structure, not card appearance |
| Body/instructions | `text-base` | Readable primary learning text |
| Controls/metadata | `text-sm` | Concise labels; wrap instead of clipping |
| Secondary fine detail | `text-xs` sparingly | Never required instructions, primary action or sole status explanation |

Current prose heading ratios (1.65em/1.35em/1.15em) can remain for authored content; distinguish content heading hierarchy from app page hierarchy. Current CardTitle hard-codes h2: later contextual heading support should preserve callers and semantics. Use bold for short emphasis, not whole paragraphs; errors and correctness use explicit words rather than color alone.

## Spacing, surfaces and responsive rules

Reuse Tailwind's spacing scale: 1/2/3/4/6/8 steps (0.25/0.5/0.75/1/1.5/2rem). Default control gap2; related content gap3–4; distinct sections gap6; card padding4, increasing to6 only where a prototype shows benefit. These are composition defaults, not mandates to pad every nested container.

Use existing rounded-md controls and rounded-lg cards, `shadow-sm` only for a real surface boundary. Avoid stacking cards inside cards for every explanatory paragraph. Retain reading max-width and wider notebook/visualizer workspaces; a single global width is inappropriate. Long URLs/code/tables need deliberate wrapping or contained horizontal scrolling. Main page should reflow at narrow widths; never hide functional columns to eliminate overflow.

Current compact mode changes all descendant main grids to gap0.5rem and main width56rem. This broad selector is an implementation risk: scope later changes to known layout primitives with before/after checks, not an unsolicited global CSS rewrite. Fixed Park or audio controls must not obscure text/focus; reserve space or move into normal flow based on measured behavior.

## Interaction-state contract

| State | Required presentation and behavior |
|---|---|
| Default | Clear action verb and target; links navigate, buttons act. One visually primary action per local activity. |
| Hover | Subtle existing surface/opacity treatment; no information available only on hover. Recheck resulting contrast. |
| Keyboard focus | Visible offset outline, not clipped or covered; logical order and return after dialogs. Focus is not selection. |
| Active/pressed | Momentary pointer activation distinct from persistent selection; avoid motion as the only feedback. |
| Selected | Text/semantic state plus visible emphasis; `aria-pressed` for toggles, appropriate native/ARIA pattern for exclusive choices. |
| Disabled | Actual disabled state and nearby reason when needed; do not disable the only exit/recovery action. Current opacity50 is not an excuse for unclear availability. |
| Loading | Name the operation, keep existing content/draft where appropriate; prevent duplicates; show stop when operation supports it. Never show loading indefinitely for a terminal failed read. |
| Error | Explain what failed, what is retained and the next safe action; technical detail optional. Failed response does not prove no server change. |
| Empty | Only after a successful empty read; explain a useful next step, distinguish unavailable service. |
| Saved | Name what and where: browser draft, saved answer, checkpoint or recorded result. Generation finishing is not content verification or learning success. |

Status announcements should be scoped and concise (`role=status` for nonurgent updates; alert for actionable errors), without rereading all streamed text. A pending control's label and recovery must remain understandable without a spinner.

## Component rules

| Component | Existing base / proposed rule | Required verification |
|---|---|---|
| Buttons | Reuse `ui/button.tsx` primary/secondary/ghost/outline and sm/md/lg. Keep default secondary. Label the consequence. Allow growth/wrapping for long labels rather than fixed-height clipping. | Keyboard Enter/Space; disabled/pressed distinction; long localized labels; zoom; applicable target size. |
| Cards | Reuse `ui/card.tsx`; group a task, not every sentence. Correct heading semantics separately from styling. | Heading navigation, reading order, nested cards on mobile. |
| Inputs/selects/textarea | Native controls plus existing Textarea; explicit labels, units and described errors; no placeholder-only instructions. | Error association, saved values, contrast of required boundary, keyboard and zoom. |
| Choices | Preserve existing controlled values; audit each Choice caller before changing toggle groups to radio semantics. | Exclusive-choice arrow behavior when using radio pattern; checked/pressed labels and existing value callbacks. |
| Navigation | Existing links/disclosures and route titles; proposed groups from Phase5. | Current-page semantics, deep links, Back/Forward, skip link and main focus. |
| Dialogs | Reuse installed Radix where applicable; title, clear close, focus return. | Escape, Tab containment, background interaction, narrow/zoom. |
| Tooltips | Supplemental only, never sole instructions or adaptation scope. Prefer visible descriptions for essential details. | Keyboard/touch equivalent; no hover-only help. No new tooltip library needed. |
| Banners | Inline to relevant task, factual, dismissible when nonessential; do not steal focus. | Retry and retained drafts; persistent urgent state not dismissed into invisibility. |
| Progress | Separate activity position, saved state and competency evidence. Text equivalent; no decorative reward percentage. | Actual metric meaning and HR-01 review, screen-reader labels. |
| Tabs/disclosures | Real tabs only for peer panels; existing details for optional material. Preserve state across views when promised. | Correct keyboard pattern, selected state, no accidental work reset or hidden audio. |
| Learning content | Context/example before assessment, primary next action beside work, reachable pause/help. | Wrong-answer recovery, replay, narrow context, optional confidence. |
| Feedback | Factual result and next option; preserve original submission identity and source. | Correct/incorrect/uncertain/staged outcomes, double submit, no invented praise. |
| Settings sections | Group by task, human labels and true effect timing; raw keys optional advanced detail. | Days/minutes units, unchanged API values, current/next/trial timing, save failure. |

Current button heights are 2rem/2.5rem/3rem. This is not proof of every target's accessible size: measure final targets and spacing. Consult [WCAG target-size guidance](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html), including exceptions; do not assume a universal 44px requirement or that compact text links must become oversized buttons.

## Motion and modality

Keep existing system reduced-motion CSS and preference class. CSS suppression does not stop every canvas/audio process: those require their existing feature controls and explicit tests. Motion should explain state, not decorate success. Avoid automatic scrolling of entire replies or focus theft. Audio is optional, with visible playback/recording status and stop/speed/volume controls. Restoring a view must not restart sound/microphone. Voice and visualizer behavior remain separate from design tokens.

## Adoption and acceptance

Phase7 prototypes reuse this foundation and the same IA; they may explore hierarchy, not duplicate backend logic. Phase10 should introduce only the missing semantic tokens and necessary primitive fixes, then migrate bounded callers with relevant tests. Preserve assessment, mastery, FSRS, adaptations and routing. No library addition is justified by this specification.

Before accepting a component: light/dark/system; standard/large text; comfortable/compact; keyboard; narrow 320/390px and desktop; zoom; reduced motion; loading/error/empty/saved combinations; visual review and assistive semantics. Verify actual interaction, not only compilation. Keep the known opaque-metric, model-content and delayed-return issues separate; styling cannot close those gates.

This phase inspected CSS and Button/Card/Choice/Textarea implementation, computed 20 token-pair ratios, and documented gaps. It does not claim a new browser run or complete WCAG audit. Existing Phase4 screenshots remain baseline evidence. Production styles are intentionally unchanged until prototype comparison and bounded implementation stages.

## Adoption update — 2026-10-04

Phase10 Stage1a now implements `control` (light#697380/dark#8993a0) for shared Textarea and `code` (light#eef0f3/dark#2a3038) for inline-code surfaces, including system dark mode. The opening specification describes the pre-adoption baseline. See [measured slice](../slices/design-control-code-tokens.md); error-role adoption, other native controls and broader primitive/layout work remain open.
