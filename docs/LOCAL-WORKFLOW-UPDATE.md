# Local tutor and authoring update

The local runtime now supports personal knowledge material from notes or optional
uploads through Source → Research → Write → Review. Research questions are editable;
the learner records findings, selects earlier personal notes, discusses findings
with the local tutor, and explicitly accepts a section before lesson activation.
Saved source excerpts and tutor exchanges remain separate from accepted reading.

Local inference uses structured response validation, logged correction attempts,
retrieved personal context, and bounded context sizing. Faster Whisper replaces
the platform-specific transcription adapter where configured. Notebook launch
supports the local Python environment and restored files.

Accuracy checks are deliberately scoped. For example, the neutral-observation
contract rejects observed unsupported association and attribution claims; it is
not a general factual verifier. Explicitly rejected quoted wording is preserved,
without exempting other claims or rewriting saved prose. Variable model generation
time and semantic repetition remain open quality issues.

Runtime databases, uploads, personal notes, notebook outputs, credentials and
machine-specific configuration are excluded from this code release. Historical
publication review is separate from checking a new commit's index.

Owner authorization on 2026-10-21 permits ongoing commits and pushes of reviewed,
tested code and sanitized documentation. The separate private archive remains
private. Publication of this repository requires resolving historical exclusions;
a clean current tree alone does not certify its history.

Release verification: 2232 passed, 1 skipped, 3 warnings in 434.69s (0:07:14). Frontend unit suite, TypeScript production
build, frontend/backend lint and strict backend mypy pass. The isolated browser
workflow covers upload, editable questions, personal-memory selection, local
discussion and section drafting, explicit acceptance, save, API restart/resume,
retained raw history and evidence, Review and lesson activation. The final
neutral-source replies used one attempt each; this does not establish a
general latency or factual-accuracy guarantee.
