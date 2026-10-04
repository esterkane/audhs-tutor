# Source capture and direct return contract

## Observed problem — 2026-10-04

The four existing Library source browser journeys pass. Sources.tsx resolves the passage only from the current search's eight hits; a durable saved link must not depend on retrieval ranking or an available embedding service. SourceViewer is an inline region reused by lessons, answers, representations and draft review, not a modal. It has no explicit capture target. The global capture classifier therefore attaches a surrounding supported context or no context. Merely adding another global DOM marker risks selecting the wrong one when several source regions are open.

## Next bounded implementation

1. Add a typed source context (version, label, validated chunk_id) to the existing optional capture union. Keep legacy entries unchanged. Retain the existing immutable-context request fingerprint and database column; no new storage or learning state.
2. Provide a direct read-only source destination independent of search results, using the existing chunk endpoint and SourceViewer. Preserve existing search result URLs and Back/Forward. Missing chunks explain removal/re-ingestion and offer source search. Transient failure offers bounded retry and must not claim deletion. Encode/validate IDs; do not store or navigate arbitrary private paths or URLs.
3. Provide an explicit capture action beside the displayed source. Pass its resolved identity to the shared capture flow rather than allowing document order to choose among multiple viewers. Preserve an existing unfinished thought and its original context; never silently replace it. Do not duplicate the save mutation or retry state machine.
4. Saved thoughts open the exact chunk read-only, closing the capture dialog and focusing a meaningful destination. Reading a source neither advances a lesson nor awards completion, and never starts audio or opens the external original automatically.

Likely files: capture_context.py, generated api-types.ts (additive sanitized delta only), parking/context.ts, ParkingLotButton.tsx or an extracted shared capture entry, SourceViewer.tsx, curriculum/api.ts, Sources.tsx and route registration if needed. Relevant unit/API/browser tests and this contract accompany implementation. No new library, model, backend endpoint or learning-kernel change is needed.

## Acceptance gates

- Save from an explicitly selected source while another viewer is open; return to that exact chunk after navigation and reload.
- Return still works when search returns no hits or the retrieval service fails.
- An existing unsaved thought retains text and original context when source capture is requested; the interface explains what will be saved.
- Deleted chunk, transient failure, timeout, retry and stale completion have distinct truthful recovery.
- Existing source report, guarded original-file link, search query, browser history and focus restoration remain functional.
- Keyboard operation, desktop/narrow layout, text zoom, no horizontal overflow, visual inspection and no unintended learning writes.
- Validate source identity persistence and keyed replay; no source content or private paths added to distribution fixtures.

## Evidence and remaining work

Baseline: `pnpm exec playwright test e2e/library-sources.spec.ts` passed all four journeys on 2026-10-04. These cover390/1280 layouts, keyboard read/close and focus, refresh, Back/Forward,200% text sizing, search failure/retry, empty/missing results, late responses and no writes. The390px screenshot was inspected. This is baseline evidence, not proof of saved-source return; that implementation and its acceptance tests remain next. C6 and C7 remain incomplete.
