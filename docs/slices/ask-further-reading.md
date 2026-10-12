# G2b — Curated official further reading

Bounded link-discovery slice, not web grounding or automated claim verification.
Saved Ask answers expose an optional Further reading disclosure. Matching runs
locally against a three-entry catalog, with explicit topic selection and honest
no-match state. No library, backend, model call, grading or scheduling changes.

## Inspected primary sources — 2026-10-12

- [Python tutorial](https://docs.python.org/3/tutorial/): programming-language
  fundamentals; assumes basic programming knowledge. Page footer identifies PSF
  License v2 and additional Zero Clause BSD terms for examples. Rolling version;
  the card asks learners to match their installed interpreter.
- [NumPy basics](https://numpy.org/doc/stable/user/absolute_beginners.html): array
  creation, shape, indexing and basic operations. Stable documentation changes;
  redistribution rights have not been assessed in this slice.
- [scikit-learn preprocessing](https://scikit-learn.org/stable/modules/preprocessing.html):
  scaling, encoding and transformations. Not evidence of fairness or correctness
  of a particular cleaning decision; redistribution rights unassessed here.

All three pages were readable without sign-in during inspection. This observation
is dated, not a promise of future availability. Cards contain short original topic
descriptions and links, not copied document bodies or generated citations. Opening
a link sends ordinary browser navigation to that site, with noreferrer/no-referrer;
question text is never inserted into URLs. No embedding, prefetch, autoplay or import.

## Verification

Two unit tests: whole-term/no-match selection and fixed outbound URLs independent
of private input. Targeted Chromium journey: explicit topic selection, empty match,
no external requests before opening a link, protective link attributes and390px
reflow. Screenshot inspected; type checking and ESLint pass. Production build
passes with existing chunk-size warning. Required code/pedagogy review reports no
blockers/majors. External-tab navigation itself and broad assistive-technology/zoom
acceptance are not tested by this journey. Existing app-level checks remain valid
for unchanged code; no backend suite rerun for frontend-only metadata.

Remaining: broader subject coverage, owner-reviewed resource curation, optional
safe fetch with source/version snapshots, claim-grounded original generation and
references that support exact claims. These links are explicitly suggested reading,
not proof that a generated answer is correct. G2 remains incomplete.

## Ask discoverability follow-up

Owner could not find Ask. Live Home inspection confirmed the entry was a plain
text link below the session card. It is now an existing secondary Button/Link in
the Home header with a session-preservation description; the primary Start/Continue
action and all learning logic remain unchanged. No new styles or dependencies.

Four affected Chromium journeys pass, including390/1280px viewport visibility,
accessible description, focus/Enter navigation, follow-ups/session preservation,
interrupted retry and Further reading. Both Home screenshots inspected. Typecheck,
targeted ESLint and production build pass (existing chunk warning). Bounded code
and pedagogy review found no blockers/majors. Owner discoverability and screen-reader
acceptance remain unverified; no claim of full UX acceptance.
