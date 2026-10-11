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
| 14px UI /16px prose,13px code, p5 | Existing body inherits browser16px, prose line-height1.75 | Not exact: migrate semantic role tokens deliberately; preserve118% preference and do not globally shrink reading |
| 48px header,240/48px navigation, five mobile destinations + Tools, p6 | Current grouped navigation and multirow header | Incomplete; prototype/verify responsive shell against target with all destinations retained |
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
The current application lacks dedicated Practice/Progress entries; implement
the documented state-aware routes before replacing shell labels. Home baseline
passed at390/1280px. No new shell behavior is claimed yet.
