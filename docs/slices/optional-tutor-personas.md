# Optional tutor personas and response language

2026-10-24. Extends the reviewed Mac Ask teaching-choice work; does not enable the
experimental context-proposal service.

## Behavior

Preferences offers No persona (default), Känguru / Kangaroo, Calm guide and
Technical coach. Language is independently Follow the conversation (default),
English or Deutsch. These explicit, reversible preferences apply across courses
to new Ask, research, workspace help and lesson tutor replies. They do not
translate the interface, rewrite saved material or change grading.

Känguru means the fictional character from Marc-Uwe Kling's books, as requested
by the owner: cheeky, anti-authoritarian and socially critical, with the same
personality in English. Explanations use original wording, without copied book
passages or invented canon. Satire must not target the learner. Precision takes
priority over roleplay; jokes, greetings and questions are not compulsory.

An English question or source no longer implicitly overrides Deutsch, or vice
versa. Versioned language policy states the selected preference explicitly;
only a direct request to answer in another language overrides it. Code, numeric
values, source quotations and citation tokens stay unchanged.

Default prompt bytes remain unchanged. Presentation is included in saved-answer
identity, metadata and research reuse binding. A completed request replay retains
its original saved answer even after preferences change. Histories are retained;
changing presentation does not silently change explicit/guided teaching mode.
English-only deterministic repetition prose and literal probes are bypassed for
explicit German replies, preserving ordinary generation and all source context.

## Verification

- Full backend suite: 2,271 passed, one intentional skip. After the final prompt
  clarification, all 64 affected persona/research tests pass, including both
  language settings on the lesson tutor path.
- Frontend: 769 unit tests pass; final affected test, TypeScript, ESLint and Vite
  build pass. Existing large-bundle warning remains.
- Browser: 27 Ask/presentation journeys pass, including desktop/mobile keyboard,
  accessibility, preference persistence, teaching choice and request recovery.
- Live local inference: six source-attached Ask samples with the larger installed
  model and two with the default Ask model all use the selected German/English
  language after the fix. Two direct language-override requests also pass.
  Earlier failures are retained in local evaluation
  records; these samples are not a general factual-accuracy certification.
- Two full real-model browser flows: upload, source-linked research questions,
  findings, discussion, section drafting, explicit acceptance, Write, Review,
  save/reload, activation and exact accepted reading. Each retains both replies
  and its original source. German discussion/draft took 13.939/10.400 seconds;
  English took 8.627/12.415 seconds (single observations, not a speed comparison).
- Both activated lessons then complete a learning/practice loop: accepted reading,
  saved notes, deterministic abstention feedback and reload/resume. No AI rewriting
  of accepted reading is required. Tests use isolated synthetic learner data.

## Remaining limitations

Language compliance does not establish semantic accuracy. Live samples still
show unsupported embellishments (for example guaranteed new string objects or
guaranteed optimistic evaluation metrics) and redundant questions. This change
does not claim to fix those, reduce generation latency or qualify a different
model for production routing. Hosted keys/budget and model assignments are not
changed by the feature. The separate private archive and private runtime assets
are excluded from publication.
