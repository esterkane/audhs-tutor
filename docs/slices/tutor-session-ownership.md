# Tutor session ownership

QA01 prerequisite: answer-producing HTTP routes must resolve sessions for the current local owner before reading tutor context, generating a response or recording representation preferences. Reuse one deterministic session lookup. Foreign and absent session IDs return indistinguishable not-found errors; streaming retains its existing SSE error contract. No new login system, migration, UI or learning event.

Applies to buffered/streamed tutor turns and representation render/prefer. Playground and voice already have ownership guards; retain their tests. This is a bounded boundary fix, not certification of every application endpoint and not implementation of saved-answer persistence.

Verification: four route cases failed before the change; 425 backend tests and full lint/types passed after it. Targeted ownership cases also pass with seeded curriculum and a ready fake model. Independent code/pedagogy review found no blockers or majors. Verified cases: normal owner flow preserved; foreign/missing sessions denied before model calls, tutor traces, events or checkpoint writes.
