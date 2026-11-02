# Learner-controlled project mode and bounded question repair

Project generation now constrains response mode to the selected session mode. Recognized standalone learner commands can change it, including `Switch to neutral mode.`, `Use lesson mode`, and `Bitte wechsle in den Prüfungsmodus.` Quoted examples, code and ordinary mentions do not select modes. The command parser supports a bounded English/German vocabulary, not arbitrary paraphrases. Existing session creation and customer-problem routing remain intact. The model cannot independently convert lesson mode into neutral discussion merely by returning different metadata.

When the only blocking finding is a missing lesson question, the hosted adapter can generate just that question through the existing authorized, budgeted gateway. It preserves the guard-checked explanation exactly and adds the question; other metadata and the append-only history remain intact. All normal guards run again. Local generation and other blocking failures retain the full repair path. Speech summaries explicitly declining a quiz use the full repair path to avoid preserving a known contradiction.

The question schema rejects blank, multiple and code-block questions. These checks are structural: they do not prove that every generated question is non-leading or pedagogically useful. The German pilot still asked about a fact already stated, which remains a quality issue. No factual or citation guard was relaxed.

## Validation

345 scoped backend tests passed, including mode authority, explicit commands, concurrency/reset, byte-preserving repair, history, gateway routing, other-failure handling and guard reruns. Backend Ruff formatting/lint and mypy passed; frontend TypeScript and changed-test ESLint passed. Real English/German hosted browser journeys preserved lesson mode, honored no-quiz requests and restored complete transcripts. Four local English/German reviewed/incident/neutral resume journeys passed. Complete saved answers were manually inspected.

Observed question-only calls took 2.03 seconds in an initial English sample and 1.36 seconds in a German sample, versus 2.75 seconds for a prior full rewrite. These are small unpaired samples, not proof of a general latency gain. Other generation and format repairs still dominate some sessions. Broader vector-reasoning reliability and repetitive questions remain open.
