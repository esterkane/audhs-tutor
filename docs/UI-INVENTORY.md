# UI inventory — 2026-10-03

Current source inventory, not a claim of usability or accessibility clearance. Entry and shell:
`frontend/src/app/App.tsx`. Routes below are verified there; no separate login screen or Electron layer.

| Route(s) | Purpose and main implementation | Next UX evidence needed |
|---|---|---|
| `/` | Home: session resume/start and goal selection; `routes/Home.tsx` | One obvious resume and no unrelated topic fallback |
| `/areas`, `/map` | Cross-course areas and skill graph | Area readiness, selection and graph text equivalent |
| `/programs` | Project guide, task notebook, full course notebooks; `Programs`, `GuidedSection`, `TaskNotebook`, `NotebookWorkspace`, `LocalNotebookLab` | Orientation slice implements current step, saved place, notebook distinction/return; owner comprehension still open |
| `/session`, `/review`, `/recap` | Learning blocks, due reviews, next-session recap | Stop/resume terminology, failure and return paths; rating recovery verified separately |
| `/playground` | Code experiment with tutor and local execution | Starter/task/output relationship, honest checks, follow-up |
| `/playground/visualizer` | Watch/Learn/Create audio visualization | Source/playback/analysis clarity and sensory controls |
| `/answers`, `/answers/:answerId` | Saved tutor questions/answers, provenance and correction | Search, original context, reuse eligibility explained |
| `/corpus`, `/curriculum` | Import/source inspection and lesson drafting | Material vs active lesson, import failures, explicit activation |
| `/models`, `/preferences` | Local/optional hosted model routing and learner preferences | Readiness, price/provider disclosure, reversible settings |
| `/experiments`, `/vocab`, `/together` | Optional experiments, vocabulary and co-working | Clarify purpose, low-capacity/skip paths and active topic |

## Shared components already present

- `frontend/src/index.css`: Tailwind theme colors (`bg`, `fg`, `muted`, `card`, `line`, `accent`,
  `accent-fg`, `ok`, `warn`), font family, dark/system themes, focus ring, reduced motion, reading width
  and prose styling. Font scale and density connect to sensory preferences. These are existing assets.
- `components/ui/button.tsx`: primary/secondary/ghost/outline and size variants; native button default type.
- `components/ui/{card,choice,textarea}.tsx`: shared containers, choice controls and text input.
- `components/Markdown.tsx`, `OptionalConfidence`, `ParkingLotButton`: reading, optional self-report and capture.
- `features/audio/AudioControls`, `features/voice/{ReadAloud,DictationButton}`,
  `features/programs/{StudyTutor,LearningCompanion,SavedContextAnswers}`: shared audio/tutor/history.

Audit items, not automatic rewrites: utility names without tokens (`bg-surface`, `border-border`),
fixed-height long-label buttons at enlarged text, shell title/current navigation, repeated audio controls,
multiple tutor choices before first reply, inaccessible/ambiguous loading/empty/failure states.

## Execution prompt for the component pass

Choose one inventory journey from the owner-prioritized UX ledger. Record the actual route/component and
rendered failure before editing. Inspect declared tokens and every affected state in light/dark/system
themes. Reuse existing primitives; fix missing/mismatched tokens locally before proposing global API changes.
Verify focus, keyboard exit, 320px reflow, 200% text, semantic names and actual contrast. Keep model
routing/provider disclosure and saved work intact. Run component/browser checks and required reviews.
Do not infer conformance or real-user comprehension from a scanner score.
