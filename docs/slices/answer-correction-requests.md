# Explicit proposed corrections

A learner can choose Request a proposed correction when continuing a saved answer. Prepare
correction request fills an editable template only if the draft is empty; choosing the request
type preserves existing text. No model work starts before Send. Purpose and draft survive reload;
the frozen retry retains its original parent/question/purpose. Default follow-up identities retain
the old fingerprint shape for existing pending requests.

The server validates purpose, records it beside the immutable answer lineage, and supplies current
saved feedback as untrusted historical context. Fixed prompt instructions ask the tutor to examine
the objection, explain a supported change or defend the earlier reasoning, and identify missing
evidence. They forbid invented execution/source checks and verified/replaced claims. The result
and reopened answer are labeled proposed corrections. Unsaved feedback is not supplied; the UI
says to save edited reports first. No original rewrite, feedback update, mastery change, new model
route, dependency or migration. Prompt version advanced to playground.tutor.v10.

## Verification and limits

Owner/source/report preservation and purpose-sensitive idempotent replay/conflict are tested with
fake providers. Frontend tests cover explicit send, preserved draft, reload purpose and proposal
labeling; desktop/narrow journeys cover preparing, sending and reopening. Required code and
pedagogy reviews found no blockers/majors. Backend592/frontend276, lint/types/build and two
desktop/narrow browser journeys passed. Sanitized focused backend5/frontend10 passed. Existing
build chunk warning remains.

This does not establish live model correction quality. No paid inference or private material was
used. A proposed correction remains unverified history; it cannot automatically replace its parent.
Next: explicit learner-reviewed preferred replacement, reversible state, conflict handling and
reuse exclusion across all selectors. Preserve source snapshots and historical evidence.
