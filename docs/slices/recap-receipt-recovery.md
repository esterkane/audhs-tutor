# Exact saved-recap recovery — AU-RECAP-04

## Problem and implementation
A committed save whose response was lost could be followed by an edited retry. The old endpoint returned the already-ended session without checking those edited values; the UI then cleared the newer draft and showed Session saved. The browser regression reproduced this after waiting for the retry response to settle (an initial check had incorrectly observed the old fetch error too early).

Implemented the contract in ../design/RECAP-RECEIPT-RECOVERY.md:
- Owned read-only completion endpoint derives open/saved/unverified from the session and exactly one matching, validated ENDED event. Missing/malformed historical receipts stay unverified. No backfill, new table or invented learning evidence.
- Explicit confirm_recap on recap Save checks canonical notes/optional ratings against that receipt. Different or unverifiable retries return409, preserving the local draft. Plain End retains existing bodyless semantics. End now resolves ownership before any side effects.
- Recap reads completion on opening and offers Check saved recap after failure. Server notes and browser draft stay separate. Known-ended sessions cannot resubmit a recap; newer notes remain selectable and retained across reload and explicit exit. No automatic completion POST.
- Normal matching Save retains its success summary and draft cleanup. Generated API types updated.

## Evidence
30 backend tests pass: receipt matching/conflict, exact replay, canonical empty notes, missing/malformed legacy receipt, foreign learner denial, existing atomic end/transitions/clarity.15 component tests pass including saved/unverified retained drafts and no automatic POST. Six browser scenarios pass across lost-response/read-failure/reload, competing finish controls and normal recap save. Final copy-selection and keyboard-exit extension reran both lost-response cases at390/1280. No overflow; screenshots inspected.

Full lint/types/build pass. Code and pedagogy reviews: no blockers/majors. Native keyboard text selection verified; no claim of clipboard permission, physical audio or human acceptance. No paid/model calls. Logs /tmp/recap-receipt-*.log; screenshots /tmp/recap-receipt-{390,1280}.png.

## Limits and next work
Browser drafts remain tab-lifetime recovery, not durable published notes. This slice adds no edit/replace operation for an ended recap. Historical missing receipts remain unverified. Outer end API recall scheduling/block closure/checkpoint pruning still use separate boundaries. Broader R3/R4 and human acceptance remain open; proceed from the reconciled current checklist rather than redoing delivered checks.


Follow-up2026-10-14: session-end-transaction.md closes the previously recorded outer API transaction gap for recall creation, block closure and checkpoint pruning. Receipt recovery remains necessary for postcommit delivery failures.
