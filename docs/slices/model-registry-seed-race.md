# Model registry initialization race

Integrated browser verification at the preceding code state finished409 passed,
20 intentional opt-in skips and1 failure in narrow Models reflow. The backend log
and browser trace show HTTP500 and UNIQUE model_registry.id, not a CSS defect.
Concurrent model/routing reads can both observe missing defaults and enqueue inserts.

The registry now performs SQLite INSERT ON CONFLICT DO NOTHING before reading each
row, serializing initializers through its existing commit boundary. Existing owner
labels/status/settings are not replaced. No schema, routing assignment, learning,
provider or budget changes. Tradeoff: a short write transaction even when all
registry defaults exist. Never interpret conflict avoidance as permission to route.

The new independent-session concurrency regression failed before and passes after;
it also verifies owner edits survive later concurrent seeds.1313 backend tests pass,
Ruff/format and targeted strict mypy pass.8 affected Models/routing browser journeys
pass, including keyboard horizontal table scrolling and390/1280 reflow. Narrow
screenshot inspected. Read-only code review found no blockers/majors.
The original full browser run remains recorded as failed; targeted reruns do not
constitute a new full-suite pass. Older hosted head1353098 passed CI; newer heads
remain separately unverified. Logs:/tmp/audhs-integrated-current.log and
/tmp/registry-race-{before,after,full,browser,types}.log.

Next priority: implement the newly approved owner-only hosted/public-export policy
in material-rights-contract.md; it is accepted but not yet enforced across runtime.
Human/assistive-technology acceptance and broader queued work remain open.
