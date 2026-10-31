# Learning-evidence review: implementation audit

The owner supplied [this review](../research/2026-10-31-adhd-audhd-adult-learning-evidence.md)
on 2026-10-31 and requested an audit and implementation of gaps. The source is preserved verbatim,
including source links, evidence-strength labels, extrapolations and caveats. Its instructions are
research content, not a replacement for the owner's explicit consent/history/privacy requirements.
No personal data, clinical profile or source corpus is added to the public repository.

## Checks and interpretation

This is a source-code and isolated-workflow audit, not proof of clinical effectiveness or a complete
literature replication. W3C [COGA](https://www.w3.org/TR/coga-usable/) is supplemental design guidance,
not itself a WCAG conformance certification. The linked [2023 free-recall study](https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2023.1301726/full)
concerns whole/section-text recall; do not use that citation as proof of a fixed criterion for every
programming or database skill. Several other claims in the supplied review are secondary or early
work, as the review itself discloses. No medication or mental-health advice is implemented.

| Recommendation | Verified implementation | Gaps / limits |
| --- | --- | --- |
| 1. Variability-first scheduler | Home mode/energy check-in; `kernel/planner.py` scales duration; `kernel/memory.py` retains overdue FSRS items with capped queues; `kernel/competency.py` aggregates evidence across sessions. | Check-in is per session, not mandatory daily reporting. No attendance penalty. Longitudinal benefit still needs real observations. |
| 2. Default retrieval | Planner validates a mandatory retrieval block; `Review.tsx` and review API use item-level cues/feedback and FSRS repeat scheduling. Minimum-viable plan is recall plus recap. | Not every course has enough accepted questions yet. "2–3 recalls" is not adopted as a universal, evidence-validated mastery rule. Confidence remains optional. |
| 3. External time/memory/starting | Soft timers/visible session timing, capture parking lot, saved lesson checkpoints and preloaded activity context already exist. New explicit next-start cue is saved in Recap/Settings and shown on Home. | Cue is optional and saved separately, not an inferred intention or notification. An unset cue is not replaced by invented next-step content. |
| 4. Predictable/explicit/low choice | Six stable navigation destinations, canonical Library, explicit teaching default, Source → Research → Write → Review, secondary session tools in one disclosure, reduced motion/effects opt-in. | Broader lesson help/notes and authoring simplification remain in the usability reconciliation; human screen-reader/Firefox/Safari acceptance still open. |
| 5. No shame mechanics | No streak/leaderboard mechanics; timers offer stop/extend/finish instead of terminating work; neutral feedback and notifications off by default. | API/network safety deadlines still exist and are not learner task timeouts. Historical wording is not rewritten. |
| 6. Personal experiments | Existing `kernel/experiments.py` has assignment/fidelity, delayed recall >=1 day, independent units and uncertainty; engagement is not a retention result. New self-reported condition recording covers noise, presence, movement and timer styles, with later item recall observations. | New condition summaries are observational, not causal N-of-1 results. They never turn on sound, randomize a treatment or recommend a personal winner. Actual sensory-treatment randomization/delivery verification and a defensible personal recommendation require a further slice and real delayed outcomes. |
| 7. Maintenance support | New optional review-only maintenance plans, explicit repeated-energy-decline proposal, logged acceptance/dismissal/undo; no automatic plan rewriting or inferred diagnosis. | A planning aid, not validated burnout detection. No score/absence-based medical inference. Sustained low baseline alone does not establish a decline. |

## Delivered software gaps

See [ADR 0022](../adr/0022-evidence-led-maintenance-and-study-conditions.md): new maintenance plans,
conservative consent-based suggestion, next-start cues and append-only condition observations.
Full histories, grading and mastery rules remain intact. Missing data stays unknown. Generic
experiments, observational summaries and real-world learning effects are separate claims.

## Tutor quality experiment

Actual research-service/native-schema calls compared current sampling with repeat_penalty=1.05,
keeping the model, context, temperature, reasoning and output-token ceiling unchanged. The first
current call included a model load; the apparent wall-time gain did not survive phase analysis.
Causal generation was 8.84 s current versus 9.30 s candidate; Python 9.53 s current versus 9.36 s
candidate. Both Python replies hit the discussion schema's 400-character ceiling mid-example.
Reject the sampling change: no reliable accuracy-preserving decoding gain was established.

The reproduced answer-coverage defect is fixed with a 1,200-character discussion allowance and
versioned brief-but-complete task instructions; saved answers already support 2,000 characters.
A regression preserves complete multi-part answers beyond 400 characters. Two actual fresh
native-schema probes returned complete Python results and retained the earlier-onset/later-event
causal distinction. They took 11.45/11.71 s end to end; this is an answer-completeness improvement,
not a speed improvement. No context, history, validation or output-token budget was cut. Existing
saved replies remain intact; the prompt/schema identity invalidates stale exact-reuse eligibility.

Two early experiment preflights stopped before inference because a copied old test learner had
hosted authoring enabled but no key. They are not timing samples; only that disposable copy was
switched to local. The owner's real key, preferences and five-dollar cap were unchanged.


## Verification scope

- Full backend baseline: 2,571 passed, one skipped, two dependency warnings (469.97 s).
  A final explicit-lesson/maintenance safeguard was then covered by 59 passing affected checks;
  it refuses the new lesson before ending existing work. The unchanged core full-suite results
  are reused rather than describing those 59 checks as a second complete suite.
- Full UI suite: 827 passed; the subsequently added condition-control regression and final
  Home/cue/condition delta pass (14 checks). App and browser TypeScript, full ESLint, build,
  backend Ruff/format (639 files) and strict mypy (330 files) pass.
- Two dedicated Chromium support journeys pass (15.0 s) for explicit maintenance/save/reload/
  revert, unchanged current plan, protected lesson selection, cue save/Home/reload/clear, empty
  observations and axe. Full focused uploaded-source workflow passes (17.0 s), including actual
  condition recording during reading, notes/pause/resume, review/activation/check/recap/Library.
  The assessment uses explicit uncertainty confirmation, not general real-model grading validation.
- The supplied review and code pass publication checks; private learner databases, runtime
  configuration, research notes, keys, model artifacts and browser traces remain excluded.
- The prior completed CI run passed non-browser jobs but its browser job was cancelled; the
  subsequent exact-head run was queued at the initial check. Neither is claimed as all green.
