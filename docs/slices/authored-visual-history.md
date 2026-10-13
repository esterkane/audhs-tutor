# Private authored visual retrieval — G4

The learner can retrieve document revisions, immutable versions and past presentation
reviews for the forthcoming inline Ask workspace. Reads never generate content,
write learning evidence or update review status. Existing mode, energy, curriculum,
grading and scheduling remain unchanged; this slice has no new screen.

## API and semantics

GET /api/authored-visuals lists active documents (archived=true selects the archive).
GET /api/authored-visuals/{document_id} supplies the current revision for explicit
commands. Versions and reviews have separate paginated endpoints, at most 50 rows
per request, with deterministic ordering. Each route resolves owner scope, including
the document/version relationship. Multi-query reads use a dedicated SQLite read
transaction; they never commit caller drafts.

Version detail includes the validated spec, stored generation origin (null if missing
or invalid), exact hashes and a current grounding observation. Malformed or hash-
mismatched specs are not renderable. Missing private snapshots, changed targets or
sources, and excluded sources have distinct states. Source-free remains ungrounded.
Raw source snapshots are not returned. Derived visual content remains private.

Review records are explicitly historical presentation reviews, not current truth,
learning evidence or permission to transmit/export. An old acceptance remains in
history when grounding changes. Read observations are not durable approvals; the
command transaction revalidates acceptance. Archived history remains retrievable.

The API retains existing local single-owner access, not multi-user authentication.
No migration, library, paid request or provider routing change. Target preview and
inline Ask draft/review controls remain open, including actual browser, keyboard,
zoom, narrow-screen and renderer failure gates. No visual usability claim yet.

## Verification

Disposable route tests cover pagination, archive/history retention, current revision,
foreign owner denial, changed answers/sources/trust/quarantine, missing restored
snapshots, corrupt restored specs, historical review preservation and input privacy.
Code/provenance review found no blockers or majors; tests not independently rerun by
reviewer. Exact final validation is recorded below.

Final verification: 1510 backend tests passed (3 warnings); 14 focused API tests
passed after the origin projection addition. make gen-api and make lint passed
(Ruff/format/mypy/frontend type checking/ESLint). Hosted CI remains externally
blocked by the previously recorded billing issue; no hosted pass claimed.
