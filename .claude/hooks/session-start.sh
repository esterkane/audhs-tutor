#!/usr/bin/env bash
# SessionStart hook: inject live project state as context (plain stdout is added to Claude's context).
# Exit 0 always — this hook must never block a session.
set -u
cd "${CLAUDE_PROJECT_DIR:-.}" || exit 0

echo "## Project state at session start"
echo "Branch: $(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo 'no git')"
echo "Last commit: $(git log -1 --format='%h %s' 2>/dev/null || echo '-')"
echo "Uncommitted files: $(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')"

echo
echo "## Current stage / open work"
if [ -f docs/ROADMAP.md ]; then
  grep -m1 -E '^\*\*Current stage' docs/ROADMAP.md || true
fi
if [ -f docs/HANDOFF.md ]; then
  echo "Latest handoff (docs/HANDOFF.md):"
  head -40 docs/HANDOFF.md
fi

echo
echo "## Local services"
for pair in "Ollama|11434" "Backend|8000" "Frontend|5173" "Qdrant|6333" "Kokoro(opt)|8880"; do
  name="${pair%%|*}"; port="${pair##*|}"
  if command -v nc >/dev/null 2>&1 && nc -z localhost "$port" 2>/dev/null; then
    echo "- $name: up (:$port)"
  else
    echo "- $name: down (:$port)"
  fi
done

echo
echo "Reminder: pedagogy guardrails and AuDHD UX invariants in CLAUDE.md apply to every tutor prompt, grader and screen."
exit 0
