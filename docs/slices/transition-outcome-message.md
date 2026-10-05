# Honest transition-outcome messaging — 2026-10-05

A browser test forwarded Skip this block to the real sandbox server, confirmed its successful response, then dropped delivery to the page. The authoritative session advanced to Review, while the old lesson said “nothing was changed; try again.” Both390/1280 pre-fix scenarios failed the new assertion against that false guarantee.

The transition errors on Session (including start) and Review now say the latest state could not be confirmed and direct the learner through the existing Pause and return Home → Continue path. Misleading internal comments were corrected too. There are no new controls, dependencies, routes, mutations or learning-logic changes.

Verification:23 Session/Review unit tests,11 pause/late-response/lost-response browser journeys, full lint and TypeScript pass. The lost-delivery cases confirm server advancement, keyboard Pause, return to the actual Review activity and exactly one transition request. The current server state remains identical after recovery; no second advancement is sent. Narrow screenshot inspected: notice and existing Pause control readable, no horizontal overflow. Independent code/clarity review found no actionable findings. A final punctuation separator does not change behavior. No production rebuild was needed for this text-only change.

This does not establish that all transition requests are bounded or canceled; start/next/extend failure semantics and other concurrent navigation paths remain separate reliability work. The message deliberately makes no claim that the original request did or did not commit. Next inspect prolonged/pending transition recovery and the remaining repeated-error guidance.
