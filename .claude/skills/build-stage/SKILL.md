---
name: build-stage
description: Drive one roadmap stage (0–6) end to end — read the stage definition, plan slices, build each with /feature-slice, run the stage benchmark, update ROADMAP and HANDOFF. Use when asked to "build stage N", "start stage N", or "continue the current stage".
argument-hint: "[stage-number]"
disable-model-invocation: true
allowed-tools: Bash(make *) Bash(uv *) Bash(pnpm *) Bash(git status *) Bash(git diff *) Bash(git log *)
---
# Build stage $0

## Current roadmap state
!`sed -n '1,60p' "${CLAUDE_PROJECT_DIR}/docs/ROADMAP.md"`

## Procedure
1. Read `docs/ROADMAP.md` → Stage $0: goal, slices, benchmark, exit criteria. Read the ADRs it references.
2. Create a task list with one task per slice plus "run stage benchmark" and "update docs". Dependencies in order.
3. For each slice invoke `/feature-slice <slice-name>` and finish it fully (schema → service → API → UI → tests → events → docs) before the next.
4. After all slices: run `make test` and `make lint`. Fix until green.
5. Run the stage benchmark exactly as written in ROADMAP (it is a script under `scripts/bench_stage$0.*`; create it if missing, from the ROADMAP text). Paste the measured numbers into ROADMAP under the stage.
6. If a threshold in ROADMAP "Thresholds that change the plan" is tripped, stop and write an ADR with `/adr` before continuing.
7. Update `docs/ROADMAP.md` (`**Current stage:**` line, checkboxes) and write `docs/HANDOFF.md` with `/handoff`.
8. Write the handoff, then **offer** `/commit` to the owner (manual-only skill; never run it or `git commit` yourself).

Rules: never skip event logging or tests to "get the stage done". Ask before adding a dependency not listed in ARCHITECTURE.md. Never run benchmarks or wipe scripts against `data/dev.db`; benches use their own `data/bench<N>.db`. The improvement programme P0–P9 (`docs/IMPROVEMENT-PLAN.md`) is not a roadmap stage: do not invoke this skill for it.
