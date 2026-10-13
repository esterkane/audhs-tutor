# Ask reference coverage expansion

Add three curated official pages to the existing Further reading catalog and fixed
server download allowlist. Match topic terms locally, retaining the three-card cap;
all six topics remain manually selectable. No question-derived requests, automatic
fetch/indexing, hosted calls, new dependencies or learning-state changes.

Inspected without sign-in on 2026-10-13:
- [Python data structures](https://docs.python.org/3/tutorial/datastructures.html): lists, tuples, dictionaries and examples.
- [pandas tabular data](https://pandas.pydata.org/docs/getting_started/intro_tutorials/01_table_oriented.html): DataFrame and Series introduction.
- [scikit-learn model evaluation](https://scikit-learn.org/stable/modules/model_evaluation.html): scoring/metrics reference.

License information inspected at Python's /3/license.html, pandas getting_started/
overview.html (License section), and scikit-learn stable/about.html. Cards retain
third-party/reuse cautions; no automatic public-export or hosted permission granted.
Rolling docs may differ from the installed version; cards tell learners to match it.

## Verification

Existing transport/extraction loaded all three pages in a temporary directory:
26,063 / 4,709 / 114,703 extracted characters respectively. No owner DB writes.
22 reference transport/cache tests and two catalog tests pass. Topic matching does
not invent a generic fallback; fixed URLs contain no user input. Browser checks
cover explicit topic selection, visible save controls and zero external requests
while browsing cards. The first browser run used an incorrect test-only button
label; corrected to the actual Save a local reading copy text before rerunning.

## Limits

These are further-reading recommendations, not evidence already used to check an
answer. Six topics are not comprehensive cross-area coverage. Local copies require
explicit selection/import and remain third-party. No generated answer is certified.

Final checks: both affected browser journeys passed; narrow screenshot inspected.
Full lint/mypy/TypeScript and build passed (existing bundle warning). Code/pedagogy
review found no blockers/majors. Private SQLite snapshot verified unchanged.
