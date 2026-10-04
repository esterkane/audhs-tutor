# C4 Library source discovery

## Problem

Learners could reopen saved answers in Library, but finding source passages required Manage → Inspect retrieval, a technical search alongside ingestion and trust controls. This mixed reading with administration.

## Implementation

Library now contains Saved answers and Sources. `/sources` searches the existing local retrieval index on an explicit query; it does not crawl the web, generate tutor answers or modify learning progress. The existing read-only POST is bounded by the shared read deadline, aborts when its query is abandoned and remains isolated by query key. Search terms and selected passage live in the URL. Up to eight passages have readable previews/citations; opening one uses the existing source viewer, provenance, guarded original link and explicit report action. Close returns keyboard focus, including after reload.

No backend/schema/routing-provider changes or new libraries. Import, removal, trust settings and technical score inspection remain in Manage. Saved-answer filters/search remain unchanged. Relevance and trust are not equated with verification. Both input and deep-linked query lengths are bounded to 500 characters before search.

## Evidence

15 component tests across Sources, shell and saved answers pass. Six browser journeys at390/1280 cover Library discovery, keyboard search/read/close, focus after reload, query/passage history, empty/error/retry, late search isolation, saved-answer regression and 200% text reflow without page overflow. Desktop/narrow screenshots inspected; search-field affordance corrected using semantic tokens. Equivalent tests run in the sanitized variant. Lint, TypeScript and production build pass; existing spectrogram worker and bundle-size warnings persist.

Independent code/state and pedagogy reviews found no blockers/majors. Incorporated bounded deep links, precise relevance wording and nontechnical recovery first. Initial browser failures were test navigation-label assumptions; a duplicate React key warning and refreshed-detail focus gap were fixed before final checks. Headless development StrictMode can start then abort a duplicate read; tests assert payload/no learning mutations rather than claiming one physical network request.

## Limits and next step

Search covers indexed passages only and still depends on the configured local retrieval/embedding services. The browser fixtures verify interaction, not live corpus coverage or relevance quality. SourceViewer is reused unchanged; its underlying passage request has its existing lifecycle. No notes/collections, licensing guarantees, source completeness or human-usability pass are invented.

C4 bounded Library/source discovery and area map are implemented; owner comprehension remains open. Next C5: inspect the current companion lifetime and document explicit cross-route target, draft, partial-response, stop and focus contracts before moving it into a persistent panel. Do not merely remove its route key.
