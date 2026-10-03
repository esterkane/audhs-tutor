# Ambient sound ownership

Together's explicit Play brown noise action claims the existing foreground audio lease. Replacing it with another audio activity stops the noise and explains why; it never restarts automatically. The shared controls expose a stop-only ambient activity, starting versus playing status, and retain the existing volume binding. Ambient noise has no meaningful playback-speed control.

Preference off, current start failure, shared stop and unmount close the context and release both ownership and volume bindings. Each context has its own identity: a late resume rejection from an older context cannot stop a newly started noise source.

Verification: Together component suite, 4 tests passed with fake AudioContext only. Tests cover explicit claim, replacement, explicit restart, stale resume rejection, shared stop, current failure, preference off and unmount. No real audio, microphone, models or learner data used. Integrated full frontend suite, production build/typecheck, targeted ESLint and the isolated ambient↔test-tone browser journey passed. Independent code and pedagogy reviews found no blockers or majors. Physical device audibility remains unverified.
