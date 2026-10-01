# Unsupported numeric citation disclosure

Actual local evaluation produced an invented `[1]` citation in workspace guidance with no retrieved sources.
The final workspace response now preserves all generated content and adds an explicit readable/listenable unverified-source note when prose contains numeric reference-like markers.
Common inline/fenced code and indexing expressions remain unchanged. Raw model text is retained in saved metadata; displayed/spoken/saved response text is identical.
No extra model call, grading evidence, mastery change or automatic source verification. All modes share the same disclosure. Bump prompt version so exact reuse cannot bypass the new response path.

This is a conservative presentation guard, not a complete Markdown parser or citation verifier. Standalone numeric lists can trigger a note; nonnumeric citations, links and complicated code delimiters may not be detected. It does not correct false factual claims. The underlying model-quality gate remains open.

Verification: 453 backend tests, lint/types passed. Independent code/pedagogy review found no blockers/majors. Replaying the six recorded v4 outputs through the disclosure flags the invented numeric citation and preserves all six original outputs. This is deterministic presentation verification, not new model-quality evidence.
