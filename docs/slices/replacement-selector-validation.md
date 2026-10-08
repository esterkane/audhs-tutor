# Incoming replacement validation — 2026-10-08

Ordinary/challenge selectors previously saw an active owned terminal row without validating its incoming lineage. A mismatched original kind/skill or inconsistent predecessor state could therefore bypass forward checks used at canonical code/listening entry.

The new selected-candidate guard traces learner-owned incoming links to the root (bounded64, cycle detection), validates the complete forward chain and requires the terminal identity to equal the already ranked candidate. It does not redirect ranking, transfer attempts, call models or change historical snapshots. Only the chosen candidate is checked; no new query per unused question. Invalid chains return an explicit unavailable error instead of triggering generation. Optional session-stop recall creation skips invalid/unavailable candidates, preserving the ability to stop without adding a bad review card.

Verification:33 focused backend tests pass, including valid multi-hop selection, incompatible ancestry, bounded/cyclic/foreign chains, ordinary/challenge selection rejection and no optional recall write. Ruff and mypy215 pass; bounded architecture review clear. Browser regression evidence recorded below. No schema or frontend changes. Source/clip compatibility from the preceding resolver remains in effect. No live replacements created.

Remaining: explicit learner transition from retained old work to replacement; complete source/review-impact preview; atomic publication/receipt recovery and reversal policy; integrated two-learner publication acceptance. This validates existing internal links, not permission to publish coursework. Historical grading and recovery retain original IDs.

Six isolated desktop/narrow keyboard browser regression journeys passed (ordinary/challenge/review exclusion controls). No rendering change; previous visual evidence retained. Backend refreshed locally after verification. Browser replacement publication acceptance remains open.
