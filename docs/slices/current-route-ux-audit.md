# Current-route UX audit and hosted-model guidance

## Reproduced issue and bounded scope

The opt-in audit omitted newer learner routes (Ask, Learn, Practice, Progress, Explore, Search, Sources, visual learning, task review and corrections). Extend its route inventory rather than infer their accessibility from the older screen set. Historical design prototype tests remain separate.

The backend-failure snapshot for Models exposed contradictory guidance: it told learners hosted benchmarks make paid requests after key setup. Current source_policy.deny_external rejects hosted inference; source-transport-containment.md documents this intentional restriction. Key configuration and registry readiness do not authorize source transmission.

Correct the Models guidance, retaining key-setup information, existing registry/actions and historical cost records. No policy, routing, provider, learning decision or scheduling change. Files: Models.tsx, its existing component test, and the opt-in UX inventory. No new library or styling.

## Evidence

Initial opt-in run: 11 scenarios pass, including two interrupted-learner checks, 17 routes at four widths and five backend-failure snapshots. All initial inventory JSON files were inspected: no reported axe violations or horizontal overflow at390/800/1280/1920. Failure pages retain retry/recovery controls. These are sampled states, not conformance certification.

Re-entry retains the draft across same-context Pause/reload and preserves the server checkpoint in a fresh context; a fresh context has no browser-local draft. Bookmark/Undo does not advance the checkpoint. This is automated behavior evidence, not human comprehension or week-long retention.

Expanded inventory: 27 existing routes at four widths (108 sampled page states), with zero reported axe violations and no document-level horizontal overflow in the recorded JSON. This does not cover every interactive or content-dependent state. All four inventory runs pass.

Models now explains that hosted inference/benchmarks are blocked, key setup does not authorize transmission, and local models remain the available path. Existing controls and historical cost data are retained. One component test, six Models recovery/reflow browser scenarios and full lint/type checks pass. Independent code and pedagogy reviews found no blockers/majors. The final plain-language refinement is covered by the component test and two reflow checks again; screenshots inspected at390/1280. No backend/model invocation or learning logic changed.

 Physical audio, assistive technology, human interpretation and unvisited content-dependent states remain open.
