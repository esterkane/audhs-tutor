#!/usr/bin/env bash
# One-shot bootstrap for a fresh clone on macOS (Apple Silicon). Idempotent.
# Usage: ./scripts/bootstrap.sh [--no-models]
set -euo pipefail
cd "$(dirname "$0")/.."
PULL_MODELS=1; [ "${1:-}" = "--no-models" ] && PULL_MODELS=0

need() { command -v "$1" >/dev/null 2>&1 || { echo "missing: $1 — $2"; exit 1; }; }
need brew   "install Homebrew first"
need jq     "brew install jq"
need docker "install OrbStack or Docker Desktop (needed for Qdrant)"
docker info >/dev/null 2>&1 || { echo "Docker daemon not running — start Docker Desktop / OrbStack, then re-run"; exit 1; }

echo "▸ tools"
command -v uv >/dev/null 2>&1 || brew install uv
command -v pnpm >/dev/null 2>&1 || brew install pnpm
command -v ollama >/dev/null 2>&1 || brew install ollama
command -v sqlite3 >/dev/null 2>&1 || brew install sqlite
command -v claude >/dev/null 2>&1 || echo "note: Claude Code CLI not found — install per docs.claude.com"

echo "▸ hooks executable"
chmod +x .claude/hooks/*.sh

echo "▸ env"
[ -f .env ] || cp .env.example .env
[ -f .claude/settings.local.json ] || cp .claude/settings.local.json.example .claude/settings.local.json

mkdir -p backend frontend

echo "▸ backend (uv)"
if [ ! -f backend/pyproject.toml ]; then
  (cd backend && uv init --bare --name audhs_tutor --python 3.12 >/dev/null && \
   uv add fastapi "uvicorn[standard]" pydantic pydantic-settings sqlalchemy alembic aiosqlite \
          instructor openai litellm qdrant-client fastembed sqlite-vec fsrs python-ulid httpx websockets numpy huggingface_hub && \
   uv add --dev pytest pytest-asyncio ruff mypy httpx)
else
  (cd backend && uv sync)
fi

echo "▸ frontend (pnpm)"
if [ ! -f frontend/package.json ]; then
  (cd frontend && pnpm create vite@latest . --template react-ts --eslint --no-immediate --no-interactive </dev/null >/dev/null && pnpm install && \
   pnpm add @tanstack/react-query zustand react-router-dom katex mermaid @codemirror/state @codemirror/view && \
   pnpm add -D vitest @testing-library/react @testing-library/jest-dom jsdom eslint-plugin-jsx-a11y prettier openapi-typescript)
else
  (cd frontend && pnpm install)
fi

echo "▸ Qdrant"
docker compose -f docker/docker-compose.yml up -d qdrant

if [ "$PULL_MODELS" = "1" ]; then
  echo "▸ models (Ollama) — verify names against current library before relying on them"
  (ollama serve >/dev/null 2>&1 &) ; sleep 2
  for m in llama3.1:8b gemma3:12b nomic-embed-text; do ollama pull "$m" || echo "pull failed: $m"; done
  echo "manage/download any model later: make models args=\"search-hf <query>\" ; make models args=\"pull <id>\""
fi

echo "▸ voice servers (python, MLX)"
uv tool install mlx-whisper >/dev/null 2>&1 || true
echo "Kokoro: see docker/kokoro/README.md (persistent server on :8880)"

mkdir -p data/corpus data/backups data/models data/qdrant
echo
echo "Done. Next: 'make dev' then 'claude' and run /build-stage 0"
