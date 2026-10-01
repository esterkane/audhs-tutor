# Diagram text ingestion

Import labels and explicit connector endpoints from local draw.io XML or .drawio files, including compressed pages.
Keep original files and normal document provenance; this is a text representation, not a visual reconstruction or interpretation of arrows.
Decode locally with bounded decompression and XML/entity rejection; never fetch embedded links, images or execute markup.
No learner events, model calls, UI, mode, energy or accessibility changes; extracted text uses the existing readable corpus flow.
Verify compressed/uncompressed pages, HTML labels, missing endpoints, corrupt payloads, size limits and existing XML/transcript behavior.

## Evidence

Current loader rejects compressed diagram XML as minified source. Synthetic compressed-diagram regression reproduces the missing support.
Format reference: https://www.drawio.com/docs/reference/diagram-generation/ . Implementation is original; no copied library or new dependency.

## Verification

418 backend tests, 181 frontend tests, full lint/type checks pass. Synthetic regressions cover both XML suffixes, compressed and plain pages, HTML headings, edge labels, malformed/oversized data, duplicate IDs and existing transcript/XML paths.

Code and pedagogy review found two majors: heading-only HTML labels disappeared and separate edge labels lost their association. Both are fixed with regressions; re-review found no remaining blockers or majors.

Scope: labels and explicit connector endpoints only. Geometry, images, styling, arrow semantics and linked resources are not reconstructed. A blank graph yields no content. Private source re-ingestion is a separate operation; parser readiness alone does not establish corpus coverage.
