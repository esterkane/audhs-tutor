# Assessment widget identity

Reproduced three duplicate React key warnings in the isolated session-clarity journey before the fix. QuestionHelp and QuestionFeedback were siblings sharing the assessment ID as their key. Give each widget a distinct role prefix while retaining the assessment ID so both reset when the question changes. No grading, prompt, scheduling, answer or feedback API changes.

Regression observes browser console warnings and verifies one hint control plus retained feedback draft during answer edits. Existing optional confidence, bookmark and stop behavior stays in the same journey. Validation: 191 frontend tests, lint/types/build and four isolated session browser journeys pass. The pre-fix console regression failed with three warnings; it now passes without them. Independent code review found no blockers/majors. Backend unchanged (prior421-test baseline).
