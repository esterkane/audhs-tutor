# Knowledge areas and question feedback

Organize study by editable knowledge areas across imported courses, retaining original citations.
Create a reviewable draft for every area with eligible source evidence; use local generation only and report coverage/gaps honestly.
Learners rate active or draft questions with reason labels and a note; feedback is version-bound and reversible.
Offer explicit question preferences based on labels, applied to later generation; never alter mastery/FSRS from ratings or infer a fixed learning style.
Areas, coverage and feedback use a keyboard-accessible focused screen; detailed course-source management stays available.
Keep drafts unactivated until reviewed. Do not silently replace published questions or discard existing drafts.

## Acceptance and evidence

- [x] Editable topic areas combine source candidates across courses; exclusions, latest versions,
  trust and deduplication apply. Course context alone does not enter generation.
- [x] Local-only bounded draft generation; missing evidence is explicit, stop retains work,
  new selected-area drafts preserve history, CAS writes protect manual edits.
- [x] Draft/active question ratings retain content snapshots and support withdrawal; deduplicated
  reasons propose reversible preferences. Learner export/wipe includes feedback.
- [x] Source links, actual sampled courses, coverage limits and hidden review answers are visible
  in the appropriate views. Area goals take precedence over course goals.
- [x] Grader receives the bounded, escaped expected answer and evidence excerpt; it is absent
  from the unanswered assessment view. Exercise success criteria are not used to grade a different question.

Verification: 366 backend /59 frontend tests, lint and 9 browser journeys; `test_areas_feedback.py` covers multi-course
citations, excluded sources, bad quotes/IDs, local-only routing, recovery, concurrent manual edits,
version/ownership checks and export/wipe. Component tests verify intentional reason selection,
feedback undo, opt-in preference application and reversal. Browser journey exercises editing,
persisted preferences and area goal precedence on an isolated database.

Real local evaluation (Gemma 3 12B, private database copy): the first RAG attempt exposed a bundled
billing FAQ as false topic evidence. Passage-level topic matching excluding the ingestion header,
an explicit prompt constraint and a regression now reject that example. The repeated RAG draft
contained one architecture question grounded in a RAG source (64 seconds). A Python sample produced
type-conversion and conditional questions. These are focused smoke checks, not a factual correctness
or complete learning-effectiveness gate. Earlier unrelated tutor evaluation limitations remain open.

## Review fixes and limits

Independent code and pedagogy reviews: fixed CAS on every generation write, exposed all cited sources,
added explicit retry/new-draft action, and connected labels to visible optional preferences.
Review also caught the missing grading-reference connection; fixed with prompt/public-view regression.

Default areas are editable curated suggestions. Up to twelve topic-matching prose passages, balanced
across courses, support at most three concepts per draft. No exhaustive corpus coverage, automatic
prerequisite inference, source conflict resolution or active-question replacement is claimed.
A bad rating alone does not quarantine content; it remains reviewable feedback. Preferences affect
future area drafts, not every tutoring turn. Draft-job progress is process-local; saved drafts survive
restart, but no background daemon restarts work automatically. A stopped untouched scaffold is retryable.


## Live completion

All 16 areas have unpublished starting drafts with 29 questions across their latest versions.
21 local Ollama calls (initial batch plus bounded retries) used $0 of hosted API budget. Thirteen
areas obtained model drafts; LangChain, MCP and prompt design still failed evidence validation.
Three source-reviewed drafts were therefore authored from inspected ingested passages and reviewed
separately, with explicit preparation metadata. They compare state versus ingestion, MCP graph
connections versus operational claims, and concrete prompt specification across course sources.
No model-output quality gate was relaxed, and no lesson was activated. Earlier failed drafts remain.
These 29 questions are a starting sample, not full coverage of 21,689 imported documents.
