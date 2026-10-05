# Preference effect timing audit

Evidence date: 2026-10-05. AU-08 remains partial. This is an implementation audit, not authorization to change teaching policy.

| Setting | Observed consumer and timing | Safe presentation / remaining work |
|---|---|---|
| Theme, density, font size, reduced motion | `frontend/src/features/sensory/useSensory.ts` updates document attributes/classes from the confirmed query snapshot. OS reduced motion still takes precedence. | Can explain immediate display effect after save, without claiming every canvas honors the setting. |
| Session default mode | `Home.tsx` applies once per Home visit when no local session ID exists. | Preselection for starting; not an active-session mode change. Late preferences versus an explicit early choice still need a race test. |
| Socratic default | Registered and saved, but no Home consumer. `stores/mode.ts` deliberately excludes Socratic mode from persistence; Home sends its per-session choice. | Confirmed mismatch: do not promise that saving this preselects the next session. Resolve the existing preference versus per-session opt-in contract before wiring it. |
| Planner duration/movement/language/guitar/challenge | `api/plan.py::build_plan` reads current preferences for previews/new sessions; `api/sessions.py` persists planned blocks at creation. Explicit energy replanning operates on the stored plan. | Settings do not rewrite an existing plan. Preview query keys omit preference values and saves currently do not invalidate previews; test stale preview versus actual new plan before claiming immediate preview updates. |
| Preferred first representation | `orchestrator/tutor.py` reads preferences per request only when no representation was explicitly requested, mastery is below the threshold and the format is allowed. Experiments may override. | A preference, not a guarantee and not a rewrite of existing explanations. Applies to this session tutor path; other tutor surfaces need individual verification. |
| Question preferences | Current guidance consumer is `orchestrator/area_drafting.py`; `kernel/question_feedback.py` returns enabled guidance. | Labels must explain new area-draft generation scope, not imply all live tutor questions change immediately. Existing questions are not rewritten by saving. |
| Voice recording/early speech | `voice/loop.py::_start` reads values for the voice session; retention is also rechecked during later recording handling. | Do not publish a blanket next-turn/next-session timing statement for all voice controls. Audit privacy and playback settings separately. |

## Runtime reproduction
A disposable Chromium sandbox stored `session.socratic_default=true`, loaded fresh Home, and still displayed Direct explanations. GET confirmed the stored flag remained true and no session had been started. One probe passed, no model call or learner DB mutation. Probe and log are retained in `/tmp/preference-timing-probe.spec.ts` and `/tmp/preference-timing-probe.log`; the probe is outside the committed regression suite because it characterizes a known defect, not desired behavior.

## Next coherent implementation
1. Add verified, per-setting scope text for display, planner and question preferences, using accessible descriptions and existing text tokens. Keep unsupported timing claims absent.
2. Reproduce preview staleness after a planner save, then invalidate only the plan preview on relevant preference saves if confirmed. Assert new preview and existing persisted session plan separately.
3. Document the Socratic contract in the existing session-entry slice before changing it. Preserve explicit per-session control, active sessions, selected-lesson entry, delayed-read user choices and direct explanation defaults; never silently switch a running tutor. Do not merely delete the control or activate questioning globally to conceal the mismatch.
4. Verify desktop/narrow keyboard return and saved values; retain prior grouping/recovery tests. Require bounded code/pedagogy review for any session-entry behavior change.

No application code was changed by this audit. Actual browser zoom, screen reader and human comprehension remain separate open gates.


## Verified implementation — 2026-10-05
Added visible, accessible descriptions for audited display/planner/question/representation/default-mode settings. The Socratic control explicitly says its saved default is not currently applied and points to per-session selection; activation behavior is unchanged. Choice accepts an optional describedBy reference; existing callers are unchanged.

A hook regression reproduced absent plan-preview invalidation after a planner save (one failed/seven passed before). Saves now invalidate only the plan-preview prefix; they neither invalidate nor rewrite existing session data. Nine hook tests pass, including active-preview refresh, non-planner isolation, unchanged cached session plan and prior save/read races. Eight Chromium checks pass across desktop/narrow plus double-root-text320/640/1280: accessible hints, keyboard traversal, exact values/reload, unknown keys and no overflow. Screenshot inspected, full frontend lint/types/build pass with existing chunk warning. Independent code/pedagogy review clear. Logs: /tmp/preference-scope-{before,unit,browser,lint,build}.log.

This closes description/invalidation items1–2 at their stated scope; the existing-session invariant is checked at the client cache boundary and source-reviewed backend behavior, not a new end-to-end assessment of all replanning paths. Socratic contract item3, default-mode delayed-read ordering, physical/assistive acceptance and other track work remain open.


## Explicit Home mode versus late defaults — 2026-10-05
A real390px sandbox journey reproduced an explicit Novelty selection being overwritten by delayed saved Low capacity settings. The Home mode handler now marks its existing per-visit preselection guard before setting the learner's choice. Untouched Home still applies the saved default; no default is rewritten and no teaching-style policy changes.

Three browser journeys pass:390/1280 keyboard choices survive delayed preferences with the saved default unchanged and no session created; untouched Home still preselects Low capacity. Twelve Home component tests, frontend lint/types/build pass (existing chunk warning). Narrow screenshot inspected without overflow. Logs: /tmp/home-late-default-{before,unit,browser,lint,build}.log. This closes the documented late-read/explicit-mode race only; separate active-session and cross-tab semantics are not expanded. Public CI for prior headf1501db/run37369850537 was pending when checked, not claimed green.
