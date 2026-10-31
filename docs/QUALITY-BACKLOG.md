# Tutor quality: outstanding work and open questions

Current working backlog, reviewed 2026-10-26. A passing example or bounded calculation is not
acceptance of the whole tutor. Preserve full saved histories, accepted material, local study
routing and the separately authorized hosted-authoring cap during every experiment.

## Outstanding tasks, in priority order

| Task | Current position | Next acceptance requirement |
| --- | --- | --- |
| Broader factual accuracy | Bounded code calculations and selected reference answers are checked; open-ended prose still makes unsupported claims. | Held-out code, numeric, causal and statistical cases must retain all required distinctions and avoid invented causes, source attribution or learner diagnoses. |
| Fresh generation and decoding time | Prompt locality improved; unchanged model decoding remains dominant. Checked calculations can avoid generation. | Demonstrate a compatible runtime/model strategy with actual activation, measured decode timing and no factual/coverage regression; do not repeat rejected settings unchanged. |
| Complete, non-repetitive answers | Contracts reduce some repetition, but examples still omit requested numeric results or repeat conclusions. | Evaluate multi-point questions, numeric outputs and inline uncertainty together; fewer words alone is not success. |
| Socratic consistency | Specific mode/format cases pass; broader question quality remains unqualified. | Open, non-leading questions; one step at a time; no answer leakage or silent change from the selected mode. |
| Language and persona coverage | Optional personas and English/German research flows work in tested cases. | Broader discussion, drafting, lesson and Socratic matrix across sources/courses; preserve literal code and quotations. |
| Browser and accessibility acceptance | Chromium keyboard, axe, reduced-motion and responsive checks cover affected flows. | Firefox, Safari and human screen-reader acceptance remain unverified. |
| Notebook support during learning | Local environment, synthetic kernel and static readiness checks work. | Diagnose actual runtime issues when encountered. Original-course exercise completion/training is not certified and remains learner-owned. |
| Release regression tracking | Local slice tests and publication guards precede release. | Check the exact published commit's GitHub results; pending CI is never reported as green. |

Optional follow-ups are separate from normal-use blockers: human voice-quality testing needs
representative recordings; any future CanvasUI package needs its licence/API and contention
evaluation. The current dependency-free Frost/Liquid/Off designs already exist. They do not
require installing CanvasUI.

## Concrete follow-ups from the current review

- Temporary empty research-question editing: implemented with browser-only recovery and strict
  save/tutor validation; verify the published commit's CI before closing release tracking.
- Exact reply reuse at the 12-reply history limit: implemented for authenticated unchanged
  replies, with a dedicated UI action and caps retained for new answers. Track release CI; see
  [verification scope](slices/research-reuse-limits.md).
- Imported calculation provenance: reproduced and removed unsupported certification from
  calculation/reference history labels, preserving writing. Durable server-owned receipts remain
  a separate improvement; see [scope and limits](slices/research-history-provenance.md).
- Page/content coherence: continue bounded review of next actions, recovery guidance and truthful
  saved/loading states. Human usability acceptance remains separate from code-based review.
- Longitudinal learning outcomes: fixture tests do not establish the older planned two-week
  experiment's real benefit. This needs real learner observations, not manufactured evidence.

Lower-priority work remains optional historical recovery and older roadmap reconciliation (for
example PDF glossary import status). Do not reopen completed encryption or voice-runtime setup
from superseded Mac-era notes. Ordinary notebook execution/training remains learner-owned.

## Open engineering questions

1. Which open-ended tasks can the current local model answer reliably, and which should use
   reviewed material, checked computation or the already authorized hosted-authoring route?
2. Can this runtime improve decoding throughput without reducing reasoning, context capacity,
   target quality or validation? A supported flag alone is not evidence of a speed improvement.
3. How should evidence distinguish a missing detail, a disproved claim and a causal conclusion
   that is logically impossible? Current prose sometimes confuses those strengths.
4. How can the tutor cover every requested result without redundant recaps or extra hypotheses?
5. Does the existing daily hosted-authoring allowance suffice for ordinary learning use? Assess
   measured usage before proposing a budget change; the current cap remains authoritative.

No new owner decision is required for the current accuracy/performance work. A concrete future
proposal that changes spending, hardware, an optional graphics dependency or requires human
voice/accessibility acceptance may need a separate decision. Existing completed authoring,
save/resume, source provenance and notebook-setup work should not be re-listed as missing.


## 2026-10-31 concurrency slice

The Supabase incident tutor now covers reported 40001 serialization failures and 40P01 deadlocks
with reviewed bilingual recovery explanations, preserving full transaction boundaries and refusing
invented SQL/root causes. Synthetic local probes improved from one 47.4-second unanswered baseline
to 22–27 ms reviewed replies with no generation. This is narrow answer reuse, not a new decoding
throughput result. See [scope and verification](slices/supabase-concurrency-reuse.md). Broader
open-ended factual coverage, unknown/mixed conditions and genuine model decoding remain open.
