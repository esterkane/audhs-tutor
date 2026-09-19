.PHONY: dev backend frontend services qdrant models test test-backend test-frontend lint migrate ingest evals bench

dev: qdrant
	@echo "backend :8000 | frontend :5173 | qdrant :6333"
	@(cd backend && uv run uvicorn app.main:app --reload --port 8000) & \
	 (cd frontend && pnpm dev) & wait

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

lint:
	cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy app
	cd frontend && pnpm exec tsc -b && pnpm exec eslint src

migrate:
	cd backend && uv run alembic revision --autogenerate -m "$(m)" && uv run alembic upgrade head

ingest:
	cd backend && uv run python ../scripts/ingest.py --src "$(src)"

evals:
	cd backend && uv run python ../scripts/run_evals.py --cases "../evals/cases/*.yaml" --out ../evals/results/latest.json

bench:
	cd backend && uv run python ../scripts/bench_stage$(s).py
