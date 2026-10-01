#!/usr/bin/env bash
# Stop hook: if source changed this turn but tests were never run, remind Claude (non-blocking systemMessage).
# We keep this advisory: exit 2 would force Claude to continue, which is too aggressive for a solo dev loop.
set -u
input=$(cat)
cd "${CLAUDE_PROJECT_DIR:-.}" || exit 0

# Avoid loops: if this Stop was already triggered by a stop hook, do nothing.
printf '%s' "$input" | jq -e '.stop_hook_active == true' >/dev/null 2>&1 && exit 0

changed=$(git status --porcelain 2>/dev/null | grep -E '\.(py|ts|tsx)$' | grep -vE '(_test\.py|\.test\.tsx?|/tests?/)' | wc -l | tr -d ' ')
[ "$changed" = "0" ] && exit 0

marker=".claude/.tests-ran"
if [ -f "$marker" ] && [ "$(find "$marker" -mmin -30 2>/dev/null)" ]; then
  exit 0
fi

jq -n '{systemMessage: "Source files changed but no test run detected in the last 30 min. Run `make test` (or the relevant pytest/vitest subset) before calling this done."}'
exit 0
