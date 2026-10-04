# Review loading recovery

Review-card reads now share the bounded read primitive used by session loading: a 15-second deadline covers response parsing, query cancellation aborts transport and ignored aborts cannot deliver stale results. Failed reads require explicit retry.

Initial errors retain rating recovery controls and offer Retry, Home and Stop. Initial loading offers Home. Background refresh errors keep the existing card, reveal and rating controls mounted, with an explicit warning and retry. Missing data cannot be presented as “Review done”; that state requires a loaded queue. Existing server content versions still protect ratings on changed cards.

Unit coverage asserts initial failure is not completion and revealed DOM identity survives failed refresh and successful retry. Shared read tests cover timeout, ignored abort/late delivery and cancellation. Browser coverage checks desktop/narrow keyboard retry. Final verification: 407 frontend tests, four review/session desktop/narrow browser journeys, lint/types and production build passed. Independent code review found no majors. Initial parallel verification failed with worker/server startup timeouts; rerunning serially with two test workers passed.

Remaining: session-state failure handling within review and complete integrated learning acceptance; physical audio and owner comprehension remain separate gates. No model, backend or schema change.
