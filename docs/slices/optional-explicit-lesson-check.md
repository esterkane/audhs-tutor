# Optional checks in explicit project lessons

The imported explicit-delivery contract permits an application check when useful. Its generic lesson guard nevertheless required a question on every answer. A complete explicit explanation could therefore trigger a hosted repair solely to add an unwanted or repetitive check.

In a request-scoped explicit lesson, absence of a check is now valid. A supplied check still passes the existing question guards. Socratic lessons, exams and exploration keep their question requirements. An explicit no-quiz request still rejects an unwanted question. No factual, citation, SQL, tool or other guard is removed, and response text/history are not rewritten by this change.

This implements the existing explicit-delivery contract and the Explain-before-questioning principle in `docs/design/LEARN-TOGETHER-CONTRACT.md`; it does not disable retrieval practice or alter assessment evidence.

Verification: 389 scoped tests pass, including retained factual findings, optional/required modes, no-quiz behavior and scope reset. English and German isolated hosted browser workflows pass through complete responses, sources, no-quiz follow-up, save/resume and budget refusal. Both used four successful hosted calls and no question-only repair. Their browser test times were 15.6 and 20.8 seconds; these small samples are not decoding-speed guarantees.

Broader answer accuracy remains open: the German vector follow-up still contradicted itself about negative-inner-product ordering. This change does not claim to correct that factual error or qualify unrestricted generation. It eliminates an unnecessary guard-triggered repair without editing explanations or weakening factual checks.
