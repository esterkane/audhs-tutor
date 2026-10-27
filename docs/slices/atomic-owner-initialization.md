# Atomic first-owner initialization

Concurrent requests on a fresh installation could each create an owner profile. A project read and later save could then resolve different owners, causing a false unavailable/conflict response while retaining browser writing.

The default-owner convenience function now performs one conditional INSERT ... SELECT ... WHERE NOT EXISTS write and then resolves the stable earliest profile. Existing profiles and settings are preserved; no profile merge, deletion or identifier replacement occurs. IDs remain generated ULIDs. This changes initialization only, not multi-user authentication or learner ownership checks.

Verification: twelve concurrent resolutions on a fresh isolated SQLite database produce one profile; existing-owner preservation is checked separately. The isolated baseline-source regression run passed 25 checks covering owner creation, database declarations, repository initialization and session transitions. The independently developed project save/reload journey also exposed the bug and passes with the fix; project integration is a separate unpublished change.
