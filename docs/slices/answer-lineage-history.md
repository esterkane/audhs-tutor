# Saved-answer follow-up history

A learner opening an earlier answer can find its direct later replies, including discussions
challenging it, without generating a new response. Parent links already existed; the reverse
history view was missing. List API adds an owner-validated parent_answer_id filter combined with
existing search, pagination and context filters. Foreign/missing parents both return 404.

The answer detail has a collapsed, keyboard-accessible Later replies panel: five newest links,
loading/error/retry/empty states and full filtered history when more exist. Search and pagination
preserve parent scope. Only direct children are shown; open a child to see its own descendants.
Hidden/incorrect/outdated answers remain discoverable as history, explicitly not recommended or
verified replacements. No answer excerpts are shown in the inline panel. Existing parent feedback
warnings and suggestion exclusions remain unchanged. No model call, database mutation, learning
evidence, new dependency or migration; source snapshots and original answers remain immutable.

## Acceptance and remaining work

Tests cover owned/direct filtering, pagination, foreign and missing parent equivalence, preserved
reported history, immutable original and zero provider/evidence writes. UI tests cover lazy fetch,
links, failure vs empty and retry. Desktop/narrow journeys exercise keyboard expansion after a real
UI follow-up with fake transport, asserting no second generation. Backend591/frontend275 passed; lint/types/build passed. Two desktop/narrow keyboard journeys
passed. Sanitized focused backend4/frontend10 passed. Existing build chunk warning remains.
Code and pedagogy reviews found no blockers/majors.

This is lineage discoverability, not the complete correction workflow. Next: explicitly prepare a
correction request without overwriting a draft, label the resulting reply as a proposed correction,
and let the learner review before choosing a preferred replacement. Preserve both originals and
all source/evidence associations; do not silently mark a generated correction as verified or train
from it. Formal replacement eligibility and correction-version conflicts remain to be implemented.
