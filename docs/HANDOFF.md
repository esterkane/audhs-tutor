# Local operational notes

Personal inventories, execution logs and handoff history are kept outside the public repository.

## Chunked session reading — 2026-10-01
Completed explanations support section/full reading, recoverable notes with inspectable citations, and optional reasoning requests preserving drafts. Versioned prompt supports readable sections; navigation and large-text layout improved. Backend378/frontend168, lint/types/build and three isolated browser journeys pass. Independent review found no remaining blockers/majors. Model compliance, actual microphone and learner outcomes remain unmeasured. No runtime data or private sources included.

## Silent video outcomes — 2026-10-01
Optional ffprobe checks MP4/M4V/MOV/MKV/WebM/AVI before speech decoding. Confirmed video-only streams become no_content; unknown/malformed/failed probes retain decoder behavior. Original assets unchanged. 390 backend tests and full lint/types pass; independent review no blockers/majors. Other video suffixes keep prior behavior. Existing running worker is deliberately not restarted; historical run errors remain intact, new workers use the improved classification.

## XML project configuration — 2026-10-01
Non-caption XML now imports as validated source code, retaining existing TTML behavior and source provenance. DTD/entity declarations rejected; obvious credential fields redacted; originals unchanged. 396 backend tests/lint/types pass, independent review no blockers/majors. Selective local recovery imported 110 documents and indexed 276 nonduplicate chunks; generated/oversized/unsafe files remain flagged. Existing bulk process remains running with its original loaded code.

## Shared audio controls — 2026-10-01
Global and inline volume/mute/speed controls plus explicit sound test. System-selected output guidance; no automatic microphone activation. Voice rate retained across delayed chunks until a new response; media speed live; analysis remains independent of output gain. 173 frontend tests, 396 backend tests, full lint/types/build and isolated Chromium audio journey pass. Independent review major fixed, re-review no blockers/majors. Hardware Bluetooth audibility is unverified. See docs/slices/shared-audio-controls.md.

## Task notebook round trip — 2026-10-01
Try can open a section-specific local starter with a CSV, separate inspectable calculation checks, and return checked output to preserved project notes. Edits invalidate success; Back remains available. 177 frontend tests, lint/types/build, isolated real-Pyodide Chromium journey and required code/pedagogy re-review pass. No new backend API or progress claims. See docs/slices/task-notebook-roundtrip.md.

## Inline answer feedback and question audio — 2026-10-01
Think deeper exposes Check my answer using the existing session/tutor routing; question, criteria and worked example are supplied. Selected question, revealed hint/checklist and returned feedback have explicit listening controls. Edits invalidate old feedback; text changes stop/reset speech. 180 frontend tests, lint/types/build, isolated fake-tutor Chromium journey and required reviews pass. Real model correctness and headphone audibility are not certified. See docs/slices/project-answer-feedback.md.

## Local notebook lab from app — 2026-10-01
Notebook workspace can prepare an explicit private bundle, preserve existing edits, install/repair pinned base tools on request and start loopback authenticated Jupyter. No cells execute automatically. Eight backend regressions, 181 frontend tests, lint/build, isolated browser journey and code/pedagogy reviews pass; real launch returned ready and HTTP 200. Course-specific legacy dependencies remain a separate compatibility task. See docs/slices/local-notebook-launch.md.

## Diagram text ingestion — 2026-10-01
Bounded decoding of compressed/plain draw.io files preserves labels, explicit connector endpoints and attached labels. HTML headings are retained; scripts, entities and expansion bombs are rejected or excluded. Visual/arrow semantics are explicitly not inferred. 418 backend and181 frontend tests, lint/types and required re-review pass. No runtime data or private acquisition sources included.
