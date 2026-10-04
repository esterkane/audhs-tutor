# Session loading recovery

Reproduced: a failed session GET rendered “Loading session…” indefinitely because the route treated missing data as loading even after an error. A regression test failed before the fix.

The session query now has a 15-second whole-response deadline, follows query cancellation and does not automatically repeat failed reads. Initial failure offers explicit Retry and Home; loading also offers Home. A failed background refresh keeps the existing session body mounted with a retry notice so unfinished answers remain intact. Returning Home does not end the session or claim to save browser drafts to the server.

Verified: 405 frontend tests, lint/strict types, production build and two isolated desktop/narrow keyboard browser journeys. Tests cover an ignored abort and late response, cancellation, initial failure/retry, and DOM identity plus unsaved answer preservation through background failure/retry. Independent code review found no blockers or majors. No backend, model routing, schema or live learning changes. Automated checks do not establish owner comprehension.

Remaining: session reads are shared with review; its complete service-failure UX and the integrated topic→explanation→notebook→feedback journey still need acceptance.
