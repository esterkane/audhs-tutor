# Hybrid knowledge authoring

Owner scope: OpenAI authoring with a $5/day application cap; local accepted-material reuse and
periodic factual reviews. Ordinary tutoring/study routing and full histories are preserved.

Implemented: explicit authoring setup, private key entry/storage, separate capped scoped gateway,
provider-labelled research/discussion/drafting, exact saved-reply reuse, accepted local reading,
scheduled bounded public reference snapshots, evidence reports and explicitly requested inactive
update drafts. Source → Research → Write → Review remains the editor workflow. See ADR 0021.

Verification is recorded below after the final test cycle. Hosted network quality/latency is
not established by scripted provider integration tests; a real application API key is required.


## Verification

- Final full backend: 2,313 passed, one intentional skip, three dependency/deprecation warnings.
  Final focused hybrid tests also pass (15), including activating a proposed revision and
  stopping its superseded schedule. Earlier failures exposed a new-table inventory expectation,
  a destructive downgrade order, protocol mocks needing the new scope boundary, and one
  transient lock in an existing visual-worker test. Final full and focused checks pass.
- Ruff check/format: 599 files; strict mypy: 310 application files. Migration/backup/export/wipe
  checks: 23 passed; a populated review export/wipe and scheduler ownership test also passes.
- Full frontend: 773 passed; final affected editor/setup/review tests: 30 passed. TypeScript,
  ESLint and production build pass. Existing large bundle warning remains.
- Four sandbox Playwright journeys pass: English/German source research and persona/language
  navigation at desktop/mobile widths. The new setup/review controls also pass 390px overflow
  and axe checks. Visual inspection retained the existing simple editor steps.
- A disposable browser flow used a scripted OpenAI provider (no hosted network): upload →
  source questions → discuss → draft → Write → save/reload → Review → activate → evidence
  review → unchanged-source skip → open inactive update draft with both research exchanges.
  Browser learning then read the accepted material, submitted a practice attempt, revisited
  the explanation and restored saved notes on reload. All data was synthetic.
- A real bounded HTTPS snapshot succeeded against Python documentation. Older documentation
  URLs now redirect; the fetcher deliberately rejects redirects. Use the final canonical URL.
  Failures show their safe reason and never count as completed reviews.
- Publication review excludes all private state, credentials, databases, uploads and machine
  configuration. The private archive receives no changes.

## Remaining prerequisite

No real OpenAI application key is configured. Enter it in Knowledge material → Authoring setup
on the local machine, then enable OpenAI authoring with the desired daily cap. The owner selected
$5/day; this is a separate authoring preference, with ordinary hosted study routing still denied.
Actual hosted answer quality, latency, account/model access and billing are unverified until that
key is supplied and a live evaluation passes. Scripted integration timings are not model benchmarks.
No real accepted lessons or session histories were used as test fixtures or rewritten.
