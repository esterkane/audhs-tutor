.PHONY: dev dev-sandbox sandbox-backend sandbox-frontend pyodide pyodide-verify backend frontend services qdrant models test test-backend test-frontend test-e2e lint migrate migrate-check migrate-apply backup backup-inspect backup-restore ingest evals eval-retrieval bench gen-api seed

dev: qdrant
	@echo "backend :8000 | frontend :5173 | qdrant :6333"
	@(cd backend && uv run uvicorn app.main:app --reload --port 8000) & \
	 (cd frontend && pnpm dev) & wait

# Disposable walk-through / browser journeys: a fresh seeded DB (never data/dev.db), hosted models
# off, no Qdrant reindex. `sandbox-backend` and `sandbox-frontend` are the two halves Playwright
# starts separately (each with its own readiness URL); `dev-sandbox` runs both.
SANDBOX_DB ?= ./data/sandbox.db
SANDBOX_API_PORT ?= 8010
SANDBOX_UI_PORT ?= 5174
SANDBOX_ENV = DATABASE_URL="sqlite+aiosqlite:///$(SANDBOX_DB)" ANTHROPIC_API_KEY= DAILY_BUDGET_USD=0
sandbox-backend:
	$(if $(filter %dev.db,$(SANDBOX_DB)),$(error SANDBOX_DB must not be the learner's dev database),)
	@rm -f $(SANDBOX_DB) $(SANDBOX_DB)-wal $(SANDBOX_DB)-shm
	@echo "sandbox DB $(SANDBOX_DB) | backend :$(SANDBOX_API_PORT) | hosted budget 0"
	@cd backend && $(SANDBOX_ENV) uv run python ../scripts/seed_attention.py --no-index && \
	   $(SANDBOX_ENV) uv run uvicorn app.main:app --port $(SANDBOX_API_PORT)
sandbox-frontend:
	@cd frontend && API_PORT=$(SANDBOX_API_PORT) pnpm dev --host 127.0.0.1 --port $(SANDBOX_UI_PORT) --strictPort
dev-sandbox:
	@echo "frontend :$(SANDBOX_UI_PORT)"
	@$(MAKE) sandbox-backend & $(MAKE) sandbox-frontend & wait

qdrant:
	docker compose -f docker/docker-compose.yml up -d qdrant

services: qdrant
	docker compose -f docker/docker-compose.yml --profile optional up -d

models:
	cd backend && uv run python ../scripts/models.py $(args)

test: test-backend test-frontend
	@touch .claude/.tests-ran

test-backend:
	cd backend && uv run pytest -q

test-frontend:
	cd frontend && pnpm vitest run

# Pinned Pyodide runtime for the code exercise, served from frontend/public/pyodide (ADR-0013; git-ignored,
# pinned by frontend/pyodide.manifest.json). Downloads only what is missing; verifies every file.
pyodide:
	cd backend && uv run python ../scripts/pyodide_runtime.py install

pyodide-verify:
	cd backend && uv run python ../scripts/pyodide_runtime.py verify

# Browser journeys (Playwright, ADR-0013) — starts `make dev-sandbox` itself; never touches data/dev.db.
test-e2e:
	cd frontend && pnpm exec playwright test

lint:
	cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy app
	cd frontend && pnpm exec tsc -b && pnpm lint

# 1) generate only (never touches a database); 2) verify on a throwaway copy; 3) apply to the dev DB explicitly
migrate:
	cd backend && uv run alembic revision --autogenerate -m "$(m)"

migrate-check:
	@T=$$(mktemp -d) && chmod 700 $$T && \
	 if [ -f data/dev.db ]; then sqlite3 data/dev.db ".backup '$$T/check.db'"; fi && \
	 (cd backend && DATABASE_URL="sqlite+aiosqlite:///$$T/check.db" uv run alembic upgrade head && DATABASE_URL="sqlite+aiosqlite:///$$T/check.db" uv run alembic current) && \
	 rm -rf "$$T" && echo "ok: migrations apply to a consistent snapshot of data/dev.db (or an empty DB). Run 'make migrate-apply' to upgrade data/dev.db."

migrate-apply:
	cd backend && uv run alembic upgrade head

# backup: never overwrites; scope=learner (default) leaves course text out, scope=full is private recovery;
# encrypt=1 asks for a password (or pwfile=<file with the password on line 1>) — ADR-0012
backup:
	$(if $(out),,$(error usage: make backup out=<file> [scope=learner|full] [transcripts=1] [encrypt=1] [pwfile=<file>]))
	cd backend && uv run python ../scripts/backup.py create --out "$(out)" --scope "$(or $(scope),learner)" $(if $(transcripts),--include-transcripts,) $(if $(filter 1 yes true,$(encrypt)),--encrypt,) $(if $(pwfile),--password-file "$(pwfile)",)

backup-inspect:
	$(if $(f),,$(error usage: make backup-inspect f=<file>))
	cd backend && uv run python ../scripts/backup.py inspect "$(f)" $(if $(pwfile),--password-file "$(pwfile)",)

# restores into an EMPTY target folder only; the live data/dev.db is never touched
backup-restore:
	$(if $(and $(f),$(target)),,$(error usage: make backup-restore f=<file> target=<empty folder>))
	cd backend && uv run python ../scripts/backup.py restore "$(f)" --target "$(target)" $(if $(pwfile),--password-file "$(pwfile)",)

ingest:
	cd backend && uv run python ../scripts/ingest.py --src "$(src)"

evals:
	cd backend && uv run python ../scripts/run_evals.py --cases "../evals/cases/*.yaml" --out ../evals/results/latest.json

eval-retrieval:
	cd backend && uv run python ../scripts/eval_retrieval.py $(args)

bench:
	cd backend && uv run python ../scripts/bench_stage$(s).py

gen-api:
	cd backend && uv run python -c "import json; from app.main import app; print(json.dumps(app.openapi()))" > openapi.json
	cd frontend && pnpm exec openapi-typescript ../backend/openapi.json -o src/lib/api-types.ts
	cd frontend && pnpm exec prettier --write src/lib/api-types.ts >/dev/null

seed:
	uv run --project backend python scripts/seed_attention.py
