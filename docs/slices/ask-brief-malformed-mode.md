# Ask retained-context recovery

A persisted conversation brief whose mode was a JSON list or object raised TypeError during follow-up resolution. Four regression cases reproduced the failure before the fix. Tuple membership now rejects these values as unavailable without hashing them; valid inheritance, clear and exact replay behavior is unchanged.

Verification: 20 brief-contract tests pass, including an API follow-up from a corrupted saved snapshot that returns successfully and excludes corrupt notes from the provider packet. Targeted Ruff and resolver strict mypy pass. Independent code review found no blockers or majors; its formatting nit was corrected. No UI, grading, scheduling, routing or model calls changed. Browser, keyboard and responsive checks were not repeated because this delta only changes backend malformed-data handling; API behavior is exercised directly.

This fixes one recovery failure, not general model accuracy. Pending guided-mode teaching acceptance and automatic source-aware context proposals remain open.
