# G2d — Explicit local reference snapshots

Implemented bounded G2d slice. Previously Further reading cards contained links only;
Ask source attachment could not inspect or use them until they were locally ingested.
Reuse the existing HTML parser and ingest_source boundary rather than a web agent.

Plan: a fixed curated catalog, explicit bounded HTTPS fetch and content-addressed
local snapshots; then a separate explicit Add to local library action using the
existing importer. Opening a card/answer, querying status or changing topic must
not fetch. No user question, course content, cookie, credential or proxy is sent.
Fetches accept no caller URL and follow no redirects. Resolve/check all addresses,
pin a public address for the TLS connection, verify the original hostname, bound
bytes and wall time, and do not fetch page assets or execute markup.

Snapshot metadata preserves requested URL, hash, fetched date, extraction version,
license reference and third-party origin. No factual-verification or owner-authorship
claim. Raw HTML remains in ignored local storage; render extracted text only.
Import uses trust tier1, normal instruction-pattern flags and local index routing.
Index failure retains the reading copy and reports that library import failed.
No learning-state writes or automatically scheduled refresh/indexing.

Likely changes: new knowledge reference service/transport, thin API/schema, default
cache-path configuration, Further reading actions, generated API types, focused
transport/storage/import tests and sandbox browser journeys. No database migration
or new dependency is planned. Preserve the separate untracked source_registry.py.

License references inspected2026-10-12:
- Python: https://docs.python.org/3/license.html (PSFv2; examples also0BSD).
- NumPy: https://numpy.org/doc/stable/license.html (BSD notice).
- scikit-learn: https://scikit-learn.org/stable/about.html (BSD footer).
These notices do not change the owner's third-party-local-only policy or authorize
public exports. Retain the original downloaded pages locally, including notices.


## Implementation and acceptance

- Three fixed documentation pages; explicit Save/Refresh, text-only preview, and
  separate Add to local library. Status GET never downloads. No new dependency,
  migration, model-generation call or learning-state write.
- Exact raw HTML hash, requested URL, fetch timestamp, extraction version and
  license-reference URL retained in local cache. The importer preserves document
  URL/content version and chunk provenance; trust tier remains 1. Raw snapshots
  are ignored local data, not repository assets. Third-party policy is unchanged.
- 22 focused backend tests cover explicit fetch, cache corruption, failed refresh,
  idempotent import, index failure, URL input rejection, private/mixed DNS,
  original-host TLS with a pinned public IP, redirects, byte limits, compression,
  truncation and cancellation before connection.
- Browser reference journeys passed: no implicit external request, explicit
  download/import, keyboard activation, failed-import retry, failed-refresh preview
  retention, literal markup display and 390px overflow check. Mobile screenshot
  inspected: readable wrapped provenance and separate controls, no horizontal overflow.
- Component regression proves duplicate-click suppression and ignoring a download
  response arriving after Stop waiting. Stop does not claim server cancellation.
- Live temporary-directory fetch succeeded for all three fixed official pages:
  Python 7,414; NumPy 47,591; scikit-learn 47,733 extracted characters. No owner DB
  import, private question, model call or paid service involved in that smoke test.
- Required code and pedagogy/provenance reviews found no blockers or majors.

## Remaining limits

This is a curated-page importer, not arbitrary web discovery or a whole-site mirror.
Python's tutorial landing page does not include every linked chapter. Only UTF-8
HTML is supported; linked assets, scripts, PDFs and subpages are not fetched.
Refresh is explicit. Cache metadata is local, not a new DB provenance/rights schema.
Per-card locks protect the current single-worker app, not multiple backend workers.
After Stop waiting the server may finish; reload to inspect its stored copy, or
retry import idempotently. No automatic attachment to an Ask answer occurs: select
imported passages through Attach local sources. No factual-correctness, rights or
mastery guarantee follows from importing. Full G2 factual-quality acceptance,
origin/export eligibility, G3 quality-aware reuse and G4–G6 remain open.
Owner comprehension, screen-reader and physical audio acceptance remain unverified.

Final regression checks: full backend 1,424 tests passed; full frontend 652 tests
passed plus the new late-response component test (1). Full ruff/format/mypy,
TypeScript and ESLint passed; production build passed with the existing large-chunk
warning. No dependency added. The initial broader Ask browser attempt timed out
starting its sandbox before any scenarios ran; focused reference journeys had
already passed. Retry after the terminated startup passed all 12 Ask browser scenarios (21s).
Live backend local-status GET returned HTTP 200 without fetching a page.
