# Correction editor: newer reads after a cached mount

HTML review capture exposed older correction wording after returning to the editor. The ordinary
browser scenario passed on a separate run, so capture timing alone was not treated as proof.
Two controlled component regressions then reproduced a concrete defect: the editor initialized
its server view from cached props and ignored a subsequent query result with a higher revision.

Adopt a strictly newer authoritative revision in the editor's local server view. Existing recovery
logic updates clean text to that revision and preserves dirty writing against its earlier base,
requiring explicit comparison/rebase before a replacement save. Equal/older initial reads cannot
roll back an acknowledged version. No API command, retry identity, grade, history or schema change.

Tests cover clean and dirty cached mounts followed by a deferred newer read, plus lost save
responses and existing correction publication/recovery browser journeys. The controlled tests
fail before and pass after the change. Export capture results and normal app verification are
reported separately; synthetic review screenshots do not establish human usability acceptance.
