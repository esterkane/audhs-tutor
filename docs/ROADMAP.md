# Roadmap

The local-first tutor supports knowledge areas, source-based lessons, practice, review, local material import, coding and audio exploration. See README.md for setup and current capabilities. Personal corpus inventories and measured private-course results are not published.

- Shared audio controls: implemented and browser-tested (2026-10-01); physical headphone audibility remains owner verification. See docs/slices/shared-audio-controls.md.

## Task notebook round trip — 2026-10-01
Try can open a section-specific local starter with a CSV, separate inspectable calculation checks, and return checked output to preserved project notes. Edits invalidate success; Back remains available. 177 frontend tests, lint/types/build, isolated real-Pyodide Chromium journey and required code/pedagogy re-review pass. No new backend API or progress claims. See docs/slices/task-notebook-roundtrip.md.

## Inline answer feedback and question audio — 2026-10-01
Think deeper exposes Check my answer using the existing session/tutor routing; question, criteria and worked example are supplied. Selected question, revealed hint/checklist and returned feedback have explicit listening controls. Edits invalidate old feedback; text changes stop/reset speech. 180 frontend tests, lint/types/build, isolated fake-tutor Chromium journey and required reviews pass. Real model correctness and headphone audibility are not certified. See docs/slices/project-answer-feedback.md.

## Local notebook lab from app — 2026-10-01
Notebook workspace can prepare an explicit private bundle, preserve existing edits, install/repair pinned base tools on request and start loopback authenticated Jupyter. No cells execute automatically. Eight backend regressions, 181 frontend tests, lint/build, isolated browser journey and code/pedagogy reviews pass; real launch returned ready and HTTP 200. Course-specific legacy dependencies remain a separate compatibility task. See docs/slices/local-notebook-launch.md.

- 2026-10-01: bounded draw.io text ingestion implemented and reviewed; see docs/slices/diagram-ingestion.md.

- 2026-10-01: archive-member retry preserves completed work; see docs/slices/archive-retry.md.

- 2026-10-01: current tutor explanation controls implemented; Q2 remains partial, including model adherence. See docs/slices/tutor-explanation-controls.md.
