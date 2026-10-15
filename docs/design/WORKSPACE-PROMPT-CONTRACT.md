# Workspace prompt contract reconciliation

Status: bounded implementation and local evaluation completed2026-10-15; see ../slices/workspace-policy-contract.md for evidence and limits.

## Concrete problem

`playground.messages` concatenates `prompts.base_policy()` and `prompts.playground_task()`. The shared pedagogy.v2 prefix requires naming a representation at the start and encourages a hint/next step followed by learner action. The workspace task forbids representation prefixes unless requested and unsolicited quizzes in explicit mode. Saying the task specializes the base leaves competing same-role instructions in the actual packet.

Local Gemma samples produced representation prefixes and unsolicited quizzes. This is consistent with the conflicting prompt, but does not prove causality. Quantity-role reasoning failures are separate and must not be claimed fixed by presentation-policy reconciliation.

## Smallest coherent next experiment

Prepare a versioned workspace-specific policy composition with one unambiguous instruction for each behavior, retaining untrusted-data boundaries, source honesty, no unsupported execution/mastery claims, and selected explicit/Socratic controls. Do not change the shared policy for session tutoring or grading to solve a workspace issue. Preserve byte-stable caching and include the new effective policy version in saved-answer identity so old answers are not silently presented as newly checked output.

Inspect all callers and saved-answer version bindings before editing. Prefer a dedicated cached workspace base over brittle runtime string removal; avoid copying learner-specific profile details into a generic policy. Existing task rules already express the intended interaction, so no new learning rule or routing decision is proposed.

## Acceptance

- Inspect assembled packets for conflicting prefix/quiz rules in grounded and ungrounded requests.
- Regression tests: explicit vs Socratic, hints, requested full solutions, source-free/cited contexts, stale output and saved-answer identity separation.
- Replay a bounded synthetic local sample comparing identical requests; distinguish instruction compliance from arithmetic, factual fidelity and pedagogy.
- No production routing or scheduling changes. No broad accuracy claim from a passing sample.
- Independent code and pedagogy review before publication.

Do not expand this into a general prompt rewrite or model-provider migration. If the experiment fails, retain the evidence and do not call it a fix.
