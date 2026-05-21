.PHONY: install frontend-install frontend-dev frontend-build dev dev-postgres worker scan check clean

install:
	uv sync

frontend-install:
	cd frontend && corepack enable && corepack pnpm install

frontend-dev:
	cd frontend && corepack pnpm dev

frontend-build:
	cd frontend && corepack pnpm build

dev:
	set -a; [ -f .env.local ] && . ./.env.local || . ./.env.local.example; set +a; \
	uv run uvicorn app.main:app --host 0.0.0.0 --port 8123 --reload

dev-postgres:
	uv run uvicorn app.main:app --host 0.0.0.0 --port 8123 --reload

worker:
	uv run celery -A app.workers.celery_app worker --loglevel=INFO

check:
	uv run python -m compileall app

clean:
	find app -type d -name __pycache__ -prune -exec rm -rf {} +
