# ADR-0015: Knowledge areas across courses and explicit question feedback

Status: Accepted — owner requested cross-course organization and chose editable topic areas (2026-09-24).

## Decision

Organize learning primarily by editable knowledge areas. Courses remain source provenance and retain
existing source-role controls. An area may draw on several courses, and a document may support several
areas. Metadata matches are candidates, not verified semantic equivalence or prerequisites.

Generate bounded unpublished drafts locally. Show actual sampled courses and evidence gaps. Retain
old drafts and active lessons when generating a fresh version. Publication remains an explicit review
step; all imported material is not automatically converted into a complete, verified curriculum.

Store learner-owned, version-bound question ratings with reason labels and optional notes. Deduplicate
counts by question content. Offer visible, reversible preferences derived from labels, applied only
after acceptance. Keep freeform notes out of model instructions. Ratings do not alter mastery or FSRS,
fine-tune a model or assign a fixed learning-style category.

## Consequences

Initial areas use editable lexical matching and small evidence samples; later coverage expansion and
semantic grouping need separate evaluation. A user can create a new area draft after editing matching
terms or accepting preferences. Existing course drafts/history remain available. Automatic replacement
of active questions, full-corpus synthesis and proven learning effectiveness are outside this slice.
