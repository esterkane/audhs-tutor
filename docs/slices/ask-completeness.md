# Sourced Ask answer completeness

## Problem and change

A real local sample described relevant bytes-per-weight information but omitted the
requested total. The final user response contract now explicitly asks for the answer,
requested quantities/units with a short derivation, each requested part or what is
missing. It retains source attribution, conflict/uncertainty and background separation.
Runtime grounded policy remains v1; the response contract is v3 (distinct from the
rejected v2 candidate). Prompt identity includes contract.v3, invalidating exact reuse
across this change. No extra model call, router change, API/UI change, assessment,
learning evidence, mode/energy behavior or dependency. Existing unverified labels stay.

## Bounded local evaluation

Four synthetic cases through actual Ask service and a temporary SQLite database:
bytes-per-weight calculation, contradictory counts, irrelevant poisoned source and
list/tuple similarity/difference/use-case comparison. Loopback models, hosted budget
zero; no owner/course material. One run per model; no statistical or latency claims.

llama31-8b produced the requested 1,000-byte result and all comparison parts, cited
conflicting counts without resolving them and ignored injected instructions. However,
its arithmetic explanation confused excluding overhead with ignoring bit conversion;
its general dictionary explanation incorrectly described dictionaries as unordered.
Completeness improved on these particular outputs, but factual-quality acceptance
remains open. Do not infer learning effectiveness or general reliability from this.
Code/pedagogy review found no blockers/majors in the narrow contract change; explicitly
retained the factual-quality failures. No automated correctness badge is introduced.

## Verification and remaining work

36 affected Ask/source/reuse tests pass, including prompt version/contract selection.
Full suite/lint results and comparison observations follow. UI is unchanged; existing
browser navigation/recovery tests remain applicable. Owner-facing factual quality,
independent review and broader cross-area cases remain outstanding.

Gemma3-12b comparison used an isolated temporary routing profile, not a learner
assignment or fabricated benchmark. It gave the requested arithmetic result and
comparison parts, kept conflicting counts unresolved, and qualified dictionary ordering
with Python 3.7. It still inserted an unsolicited analogy label/follow-up and loosely
called 1,000 bytes approximately 1KB. Observed totals were 12.23/3.67/9.28/11.19s
versus llama 4.44/1.75/3.11/3.56s; no controlled warm-up, so not a speed benchmark.
No live routing change is justified by these four samples.

Final verification: 1,446 backend tests pass (three dependency warnings), full
lint/mypy/TypeScript pass. Code/pedagogy review cleared the bounded change.
Private SQLite snapshot unchanged. Prior frontend/browser evidence retained for
unchanged UI; no new accuracy certification or live routing change.
