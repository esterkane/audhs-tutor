---
name: audhd-ux
description: AuDHD-centred UX invariants and review checklist for any screen, component, notification, timer or adaptation logic. Claude loads this whenever it builds or changes UI in frontend/ or session/planner behaviour that the learner sees.
user-invocable: true
---
# AuDHD UX invariants

Grounding (from `docs/research/audhd-learner-report.md`): autonomy support over extrinsic gamification (SDT); monotropism-aware single-task flow; executive-function offloading; explicit, literal communication; no covert adaptation; learner-selectable state.

## Checklist
- [ ] **One task per screen.** Secondary info collapsed by default.
- [ ] **State mode + energy** chosen by the learner on Home (Novelty / Steady / Low-capacity; energy 1–5). Components read from the Zustand store `useMode` (`frontend/src/stores/mode.ts`); nothing auto-switches.
- [ ] **Minimum-viable path** exists (review: capped subset; session: blocks 1+6) and is offered first on low energy.
- [ ] **Parking lot** button always visible; capture ≤ 2 interactions; item linked to current node.
- [ ] **Soft timers only**: wind-down prompt with "save & stop" / "5 more minutes" / "finish block". Never a hard cut.
- [ ] **Adaptation log**: any change the system makes (item order, difficulty, mode suggestion) writes `adaptation_log{what, why, reversible}` and shows an undo affordance.
- [ ] **Sensory settings** respected: motion, sound, notifications, density, theme. `prefers-reduced-motion` honoured by default.
- [ ] **Feedback wording**: literal, specific, no shame, no praise filler. Lapses recover without penalty.
- [ ] **Game mechanics** opt-in only, default off; if on, mastery-based, no streaks.
- [ ] **Choice architecture**: 2–3 concrete options, not open prompts. "Which next?" not "What do you want?".
- [ ] **Body-doubling / co-working** mode is a presence screen, optional ambient audio, no tracking.
- [ ] **Keyboard-first**, WCAG 2.2 AA, focus ring ≥ 3:1 contrast, axe test passes.
- [ ] **Behavioural signals** (latency, drop-off) are shown to the learner as hypotheses in the experiment dashboard, never as hidden scores.
