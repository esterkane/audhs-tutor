---
name: handoff
description: Write docs/HANDOFF.md so the next session (or a fresh Claude) can continue without re-discovery — what was done, what's open, how to verify, next step. Use at the end of a work session or when asked to "wrap up".
disable-model-invocation: true
allowed-tools: Bash(git status *) Bash(git diff --stat *) Bash(git log *)
---
# Handoff

State: !`cd "${CLAUDE_PROJECT_DIR}" && git status --short | head -30 && echo "---" && git log --oneline -8`

Write `docs/HANDOFF.md` (overwrite) with ≤ 40 lines:
- **Date / stage / slice**
- **Done this session** (bullets, with file paths)
- **Verified by** (exact commands run and their result)
- **Open / blocked** (what, why, what decision or info is missing)
- **Next step** (one concrete command or slice to start with)
- **Do not** (traps discovered, e.g. "don't upgrade X, breaks Y")

Then update the `**Current stage:**` line and checkboxes in `docs/ROADMAP.md` (never tick future stages), and the status column in `docs/IMPROVEMENT-PLAN.md` when a P-stage moved. Do not commit unless asked (offer `/commit`).
