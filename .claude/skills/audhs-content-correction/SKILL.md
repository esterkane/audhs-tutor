---
name: audhs-content-correction
description: Implement AuDHS Tutor question correction, suspension/replacement, structured editing and source-preserving representations. Use for reported bad content and provenance workflows.
---

# audhs-content-correction

Read current curriculum/assessment/source schemas, accepted ADRs and R5–R6 in docs/AUDIT-IMPLEMENTATION-PLAN.md. Feedback is an explicit report, not automatic model training or mastery evidence.

Model question identity and version separately from eligibility. Design active/suspended/superseded/retired transitions, including explicit restoration policy. Preserve prior answers/evidence. Suspension must cover all future selectors and queued review eligibility, not only hide one component. A learner's report alone must not silently alter mastery.

Before publication present additions, replacements, affected pending reviews and retained historical evidence. Use optimistic version checks and atomic, repeat-safe publication. Exercise these actions with sandbox data; implementation permission does not publish real curriculum.

Structured fields use server-authoritative Pydantic/OpenAPI schemas and field errors. Preserve dirty work across route changes and conflicts; retain advanced JSON as an escape hatch rather than the only editor. Prefer existing controls before adding a form library.

Fresh and cached explanations, hints and alternate representations retain source IDs/versions and citation associations. Show original passages; distinguish missing version from offline/500. A matching quote is not proof that all generated claims follow from it. Retrieved material stays untrusted data.

Test old question exclusion with history retained, already queued cards, same-version retry, concurrent edit conflicts, fresh/cache provenance parity, missing sources and invalid field data. Record unmet source coverage and never substitute unrelated evidence to make a citation appear complete.
