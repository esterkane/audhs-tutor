# G0b — Local image and speech transports

Preserve local image reading and narration without sending source images or lesson
text through external model endpoints, environment proxies or redirects. This
slice emits no new learning events, changes no grading/scheduling/prompt behavior,
and adds no UI controls or mode-specific behavior.

## Reproduced problem and fix

Six regression cases failed before the fix: remote speech/image endpoints accepted
payload work, and speech readiness could describe a remote service as ready. The
previous model-provider guard did not cover these independent media adapters.

Shared endpoint validation now requires HTTP(S) loopback with no credentials,
proxy path, query or fragment; malformed ports fail closed. Shared local-weight
validation requires nonempty model metadata and rejects cloud aliases. The existing
Ollama provider uses these same validators.

The synchronous image reader checks /api/show before submitting image bytes. Both
requests use one proxy-disabled, redirect-disabled client, closed after reading.
Kokoro readiness, voice listing and synthesis use loopback-only, proxy-disabled,
redirect-disabled clients. Narration retains its existing text bounds, voice,
language mapping, PCM format and sample rate. Remote readiness returns false;
content calls raise an explicit source-policy error.

## Acceptance

- Six failed-before cases now pass.
- 46 focused media/model policy tests pass, including cloud/unknown image model
  rejection, exact local payloads/PCM, redirect rejection, environment proxy
  isolation, and client cleanup.
- Ruff/format and strict mypy on the four changed production modules pass.
- Full backend suite: 1,359 passed (3 existing warnings). After the additional
  voice-ID parser correction below, all 73 affected voice/policy tests passed;
  unchanged unrelated tests were not repeated.
- Live local speech: explicit English voice returned 94,286 PCM bytes at 24 kHz.
  The server exposed 72 voices as objects. This revealed an existing bug: the app
  converted those objects to strings, so automatic first-voice synthesis returned
  HTTP400. Two new cases failed before correction. The parser now accepts string
  IDs or object IDs and rejects malformed envelopes. After correction, automatic
  first-voice synthesis returned 108,676 PCM bytes. This proves server audio
  generation, not physical speaker/headphone playback. Tiny follow-up review clear.
- Required bounded code review found no blockers/majors. No pedagogy semantics,
  source content, learning evidence or assessment behavior changed.
- No frontend changed; browser/keyboard/responsive acceptance was not rerun.
  Physical headphone output and human/assistive-technology gates remain open.

## Boundaries and next step

These checks assume trusted local services. They do not attest a malicious daemon,
prove source rights, or authorize hosted calls. Unknown material remains eligible
for local work only. Owner-origin/version/derived-lineage receipts, revocation and
public-export enforcement remain outstanding; neither repository becomes public.
No historical content is reclassified or deleted.

Next implementation: G1 session-independent Ask workspace with local saved-question
suggestions and recovery. Reuse nullable-session TutorAnswer records and existing
answer search where appropriate; never manufacture a learning session to chat.
Keep generated answers labelled separately from checked/reviewed content. This
slice adds no Ask UI, new generated content or automatic course replacement.
