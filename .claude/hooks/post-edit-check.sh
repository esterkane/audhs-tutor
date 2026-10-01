#!/usr/bin/env bash
# PostToolUse (Edit|Write): format + fast lint the touched file. Exit 2 surfaces problems to Claude.
# Formatting is applied in place (ruff format / prettier). Lint errors are reported, not auto-fixed.
set -u
input=$(cat)
path=$(printf '%s' "$input" | jq -r '.tool_input.file_path // empty')
[ -z "$path" ] || [ ! -f "$path" ] && exit 0
cd "${CLAUDE_PROJECT_DIR:-.}" || exit 0

problems=""
case "$path" in
  *.py)
    if command -v uv >/dev/null 2>&1 && [ -f backend/pyproject.toml ]; then
      (cd backend && uv run ruff format "$path" >/dev/null 2>&1 || true)
      out=$(cd backend && uv run ruff check "$path" 2>&1) || problems="$out"
    fi ;;
  *.ts|*.tsx)
    if [ -f frontend/package.json ] && [ -d frontend/node_modules ]; then
      (cd frontend && pnpm exec prettier --write "$path" >/dev/null 2>&1 || true)
      out=$(cd frontend && pnpm exec eslint "$path" 2>&1) || problems="$out"
    fi ;;
  *.json)
    jq empty "$path" 2>&1 || problems="Invalid JSON in $path" ;;
  prompts/*.md|prompts/*.yaml)
    # Pedagogy guardrail lint on prompt files.
    if grep -qiE 'how do you feel|learning style|visual learner|auditory learner' "$path"; then
      problems="Prompt violates pedagogy guardrails (feeling-question or learning-styles language): $path"
    fi ;;
esac

if [ -n "$problems" ]; then
  echo "$problems" >&2
  exit 2
fi
exit 0
