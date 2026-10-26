# Research workflow coherence

Bounded follow-up to a read-only navigation/research usability review. Codex verified the
findings against the components; external review is advisory, not human usability acceptance.

- Navigation calls the authoring page **Knowledge material**, matching its heading and scope.
- When source notes no longer contain the linked passage, explain which actions are paused,
  display the original passage and offer an explicit restore action. Restoration appends the
  original passage to the current notes; it does not replace edits or change research provenance.
  Questions, findings, sections and saved replies remain intact.
- Screen-reader region names match the actual local or OpenAI authoring tutor. Missing findings
  explain how to enable tutor actions, including when the findings field is on the Research step.
- Adopting exactly the proposed paragraph does not falsely claim that its evidence changed.
  Other changes to findings, evidence, source, question or selected memories still mark it stale.
  This is presentation logic; server reuse signatures and saved histories are unchanged.
- Sticky save/navigation controls sit above the measured mobile navigation height; a browser
  regression reproduces the previous overlap and checks the controls remain unobscured.
- Add-section actions appear in Write, where the editable section is visible.
- Ambiguous adjacent inline-code spans defer the whole calculation question. Explicit comma,
  English and German conjunction separators remain supported; literal code bytes are unchanged.

Verification: 74 affected calculator/research backend cases; formatter, Ruff and mypy.
Frontend tests, lint/build and isolated responsive browser flows are recorded with release
verification. Browser journeys cover tutor drafting, source restoration, writing, saving,
reload, reading, feedback, recap, navigation and session continuation. Component checks include
axe and truthful accessible names. No real learner records are used for these checks.

Question-edit follow-up: clearing a question now keeps a temporary empty value, including after
browser reload. Inline accessible validation and save/tutor guards require its replacement before
submission. Browser recovery explicitly allows this unfinished state; default validation and the
server schema remain strict. Findings and histories stay intact; no old prompt is substituted.

Remaining work: Exact reuse at
the research-history cap and imported calculation provenance require separate server regression
work. Broader local answer quality and decoding throughput remain open. Human usability,
Firefox/Safari and screen-reader acceptance are not certified by these automated checks.
