# Validated starter contract

2026-10-04. Bounded structural improvement; the broader semantic quality gate remains open.

## Problem and implementation

Prompt-only starter help produced completed programs and instructions incompatible with the unfinished template. A distinct starter intent now asks for bounded JSON data, explanation and a result description. The application supplies practice(data), a real NotImplementedError placeholder and explicit data-access paths. No model-generated imports or executable structure enter this scaffold; insertion remains explicit and execution remains learner-controlled. Existing conversational help is unchanged. This does not modify assessment, mastery or routing policy.

## Current evidence

43 focused backend tests pass (starter contract, playground sources, playground, request recovery and diagnostic). Ruff passes for starter schema/tests; mypy passes for starter schema and playground orchestrator. Structured repair and same-request replay are exercised. AST tests check that sample strings remain literal data and the function remains unfinished.

Three successive local-only starter samples exposed: contradictory placeholder instructions; a mismatched function name; then dictionary keys described as variables. The last sample used the result_description contract and completed in about five seconds with one local model attempt. Application-owned input-access guidance was added after that sample and has a regression test. None of these samples proves general semantic relevance or teaching quality. Raw evidence is private only.

## Browser and review evidence

Two isolated Chromium journeys pass at390/1280 pixels using a representative unfinished scaffold fixture. They cover preserved lesson/unsent chat/code, source restoration, keyboard insertion and return, disabled duplicate insertion, Undo and stale lesson handling. Visual inspection found that a wide code block expanded the entire conversation; min-w-0 on each message fixes this, and the journeys now assert the conversation itself has no horizontal overflow. Code blocks retain their own scrolling. Both resulting screenshots were inspected; the conversation remains vertically scrollable. These mocked browser replies establish interaction behavior, not model quality.

Frontend starter helper tests:2 passed. Lint, TypeScript and production build pass; existing large-bundle and spectrogram worker_threads warnings remain. Code review found no blockers/majors. Pedagogy review rated the actual sample Partial because its variable wording was misleading; renderer instructions now explicitly say to use data entries instead of names in prior code or model prose. That clarification is application-owned, not evidence of improved model reasoning.

## Remaining issues

Task relevance, feasibility and prose solution leakage remain semantic limitations. No broad teaching-quality pass is claimed. Current browser journey uses the plain editor preference; it does not certify screen-reader behavior or every rich-editor interaction. Full C3 and the broader authoritative workspace design remain incomplete. Next: review remaining contextual-tool requirements before the next workspace slice; do not treat this structural contract as completion of the design plan.
