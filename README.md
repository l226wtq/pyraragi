# Pyrragi

A LANraragi-inspired archive library built with FastAPI, PostgreSQL, Redis, and Celery.

This is an early scaffold focused on the core architecture:

- PostgreSQL stores durable metadata and searchable relationships.
- Redis is used for Celery and short-lived cache/locks.
- Celery handles archive scanning, page indexing, and thumbnail generation.
- The frontend is served by FastAPI templates and static assets.

## Run

```bash
docker compose up --build
```

Then open http://localhost:8000.

## Development

```bash
cp .env.example .env
docker compose up --build
```

## Local Debugging Without Docker

Light mode uses SQLite and runs Celery tasks inline inside the FastAPI process. It is the quickest way to debug API, UI, upload, scanning, and reading flows.

Install the system image library used by `pyvips` before running thumbnail generation locally:

```bash
sudo apt-get install libvips42
```

WebP pages are supported by default. JPEG XL pages (`.jxl`) are supported when the installed libvips has JPEG XL support. You can also choose the generated cover thumbnail format:

```bash
THUMBNAIL_FORMAT=webp  # default
THUMBNAIL_FORMAT=jxl
```

```bash
cd pyrragi
make install
make dev
```

The backend runs at http://127.0.0.1:8123.

The Python backend uses `uv` for dependency management. The frontend is a Vue 3 + Vite app using `pnpm` through Corepack. Install Node.js 20+ or 22+, then run:

```bash
make frontend-install
make frontend-dev
```

Open http://127.0.0.1:5234. Vite proxies `/api` to the FastAPI backend.

Put `.zip` or `.cbz` files in `storage/archives`, then click `Scan` on the library page. Uploading from `/upload` also works. Because `CELERY_TASK_ALWAYS_EAGER=true`, indexing and cover generation run immediately during the request.

To build the Vue SPA for FastAPI to serve directly:

```bash
make frontend-build
make dev
```

Then open http://127.0.0.1:8123.

Full local mode keeps the same topology as Docker, but runs services on the host:

```bash
createdb pyrragi
psql pyrragi -c 'CREATE EXTENSION IF NOT EXISTS pg_trgm;'
cp .env.postgres-local.example .env
make install
make dev-postgres
make worker
```

Run `make dev` and `make worker` in separate terminals. Redis must be running on `localhost:6379`.

Storage is mounted under `./storage`:

- `storage/archives`: original archive files
- `storage/thumbs`: generated thumbnails
- `storage/cache`: temporary/generated page cache
