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

## Live validation — 2026-10-25

The configured OpenAI authoring model was tested through the real application gateway with
synthetic learner material. Six focused cases passed manual semantic review: string immutability
versus allocation/identity/equality; odd/even sample median calculations without a symmetry
claim; Python string/integer concatenation versus mixed numeric addition; German responses over
English evidence; refusing unmeasured speed/causal claims; and a complete knowledge section.
Arithmetic and built-in Python results were also checked deterministically. This is bounded
qualification evidence, not a guarantee that arbitrary model responses are factual.

Fresh endpoint wall times were 1.382–3.593 seconds, median 1.832 seconds. All six unchanged
research requests reused their saved reply without another provider call in 22–24 milliseconds.
These are local observations for these inputs, not a general SLA or controlled cross-model
speed comparison. No model substitution or prompt weakening was needed.

Real German and English browser flows passed: upload → source-based model questions → discuss
→ draft → Write → save/reload → Review → activation → fresh public-reference review → unchanged
source skip. Generated discussions/drafts took 1.516–2.002 seconds in those flows. Subsequent
learning sessions preserved exact accepted reading, practice feedback, revisiting and saved
notes across reload. A separate planted false fresh-allocation guarantee was identified against
[Python's data model](https://docs.python.org/3.14/reference/datamodel.html), producing an inactive
correction draft; only explicitly activating that draft changed the current lesson.

Fifteen real provider attempts conservatively counted $0.004843 using registry pricing, under
the owner's $5/day cap. A small allowance was held in the main daily ledger while isolated
tests ran, then released and replaced with per-attempt usage traces (no test material imported).
The amount is app accounting, not a provider invoice. Credentials were neither displayed nor
copied into the isolated data. Real learner progress and full histories were preserved.

The live setup exposed two practical failures: a dormant WSL instance made the save request
unreachable, and an existing private key directory's ownership prevented writing. The runtime
was restored and directory ownership corrected locally; the already-entered key was then saved
without extracting its value. Product fixes add an explicit Save API key button, an unsaved-key
indicator, immediate configured feedback and a safe actionable storage-error response. Saving
the credential independently changes neither provider selection nor daily cap and makes no
inference request. Failed saves retain the unsaved field and never claim success.

Final affected backend tests: 16 passed. Full frontend: 775 passed; TypeScript, ESLint, production
build, Ruff and strict mypy pass. A mobile keyboard browser regression verifies explicit key
save without a real credential or provider call. Existing large-bundle/dependency warnings remain.
The prior complete backend and GitHub CI remain green; unchanged backend logic reuses that
evidence. Private backups, acquired materials, local configuration and credentials stay unpublished.
