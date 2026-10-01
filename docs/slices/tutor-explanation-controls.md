# Tutor explanation controls

Q2 bounded slice: after a completed current explanation or answer feedback, offer Shorter, Smaller steps and Show an example. Preserve selected target, prior conversation and unsent draft. Socratic mode keeps Explain instead as the explicit mode change; adaptation controls appear after that switch. Changed-work feedback cannot be adapted as current work.

Uses existing tutor request/event routing; no schema, dependency, mastery or mode/energy changes. Controls wrap on narrow screens, are keyboard buttons and never start audio. Existing Stop/timeout/stale-operation guards apply. Illustrative examples must be labeled and cannot claim execution or new assessment evidence.

Broader Q2 elapsed status, sources and expanded local-model evaluation remain separate gates.

## Verification
- 188 frontend tests and 421 backend tests pass; lint/types and production build pass (existing bundle-size and spectrogram worker warnings).
- Two isolated Chromium journeys at 390/1280px exercise all controls by keyboard, selected-step continuity, draft retention and overflow. Component tests cover stale-work suppression and explicit Socratic switch; existing Stop/storage/error regressions remain green.
- Independent code/pedagogy review: no blockers or majors.
- Local Ollama llama3.1:8b, current playground message builder, three synthetic samples before/after prompt tightening; no paid calls or production routing changes. Raw outputs: evals/results/explanation-controls-local-initial.json and explanation-controls-local.json. Final timings: 1.75/3.46/6.56 seconds for shorter/steps/example; tiny sample, not a benchmark.
- Model-quality gate remains partial: initial example contradicted its own missingness counts, revised example is internally consistent but still supplies unsolicited code. Shorter retains the no-data caveat but adds a preamble rather than shortening this already brief response. Smaller steps retains uncertainty and proposes a relevant first action. These observations do not prove general accuracy, source fidelity or improved learning. Do not silently execute generated examples.

Broader Q2 elapsed status, completed-message announcements, source-view consistency and expanded model evaluation remain open. No additional retrieval or checked-output claim added.
