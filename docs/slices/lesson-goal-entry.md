# Goal and explanation entry — 2026-10-11

PDF target: complete design system pp2,9 (one next step,context before content,
learner-controlled explanation), with retained accessibility controls from p11.
This is an incremental Learn improvement, not completed shell/ContextBar adoption.

The narrow baseline placed the primary explanation action after the separate goal's
idle narration controls. Move the goal into the explanation card above Start explanation;
keep goal narration below the optional lesson question. Assessment still presents its
own goal and narration. Teach narration mounts only while that panel is active, so
hidden teaching content cannot retain invisible playback controls. Existing ReadAloud
owns cleanup. No prompt,checkpoint,grading,mastery,provider or request-handler changes.

Same seeded390px fixture: action top moves851.8→737.8px. Final layout journeys also
measure829.8px at320 and532px at1280. These are layout positions,not comprehension
results. Text size and all controls retained; no audio starts automatically.

Verification:12 Session/SessionControls unit tests;4 browser journeys covering320/390/1280,
goal→primary→narration order,keyboard exits/disclosures,labels/Undo,unchanged checkpoints,
and assessment context/hints/audio access. Narrow screenshot inspected. ESLint and
production type/build pass with existing chunk warnings. Bounded code/pedagogy review
clear. No model calls for validation. Human comprehension,physical audio,screen-reader
and complete PDF shell alignment remain open.
