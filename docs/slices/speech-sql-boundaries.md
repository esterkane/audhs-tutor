# Speech SQL boundaries

The read-aloud guard treated `SELECT privilege; ... from your assumptions` as SQL and regenerated an otherwise correct complete answer. Detect SELECT/FROM within statement boundaries, respecting SQL quotes, dollar strings and comments. Keep URL, fence, diagram, secret and speech-length checks. This is a speech-format heuristic, not a SQL validator or factual verifier; natural-language ambiguities remain possible.

No learner text, stored transcript, provider routing or budget is changed. A deterministic orchestrator regression verifies unchanged complete prose and speech with one model request. Real SQL remains blocked, including multiline queries, qualified names, quoted semicolons, nested comments and quoted statements.

Also update the imported explicit-delivery test to the existing optional application-check policy.

Validation: native integration suite 231 passed / 47 service-dependent skips; host Supabase suite 389 passed. Two isolated hosted browser runs passed setup failure, sourced causal explanations, no-quiz requests, transcript resume and budget refusal. Complete answers were manually checked for cross-row write skew, Serializable dependency cycles, whole-transaction retry and grant/RLS separation. No speech repair occurred; an earlier observed false-positive repair cost 7.279 seconds. New runs took 38.5 and 41.0 seconds in the browser (model/tool variability differs); this is removal of unnecessary regeneration, not evidence of faster model decoding. Experimental hosted transport was confined to test processes and is not part of this release.
