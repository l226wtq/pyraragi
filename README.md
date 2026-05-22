# Pyrragi

A LANraragi-inspired archive library built with FastAPI, PostgreSQL, Redis, and Celery.

This is an early scaffold focused on the core architecture:

- PostgreSQL stores durable metadata and searchable relationships.
- Redis is used for Celery and short-lived cache/locks.
- Celery handles archive scanning, page indexing, and thumbnail generation.
- The frontend is a Vue 3 SPA served by FastAPI in production.
- Archives are intentionally limited to ZIP/CBZ.

## Archive Format Scope

Pyrragi is ZIP-only by design. It accepts `.zip` and `.cbz` files, where CBZ is just a ZIP archive with a comic-book extension.

RAR/CBR and 7Z/CB7 are intentionally out of scope for now:

- RAR and 7Z often have weaker random-read behavior, especially solid archives.
- RAR support commonly depends on external tools such as `unrar` or `unar`.
- 7Z support adds more decoding complexity and can make page seeking slower.
- Mobile apps benefit from a stable server-side page API instead of format-specific client logic.

The recommended library convention is to normalize imported books to `.zip` or `.cbz`. The HTTP API can stay stable even if the storage implementation changes later.

For existing RAR/CBR or 7Z/CB7 libraries, convert them before import:

```bash
sudo apt-get install zip unrar 7zip
scripts/convert-to-zip.sh --cbz -d storage/archives /path/to/books
```

If `unrar` is unavailable in your distro repositories, install `unar` instead. The conversion script extracts each source archive to a temporary directory, then repacks it as ZIP/CBZ. It uses `unrar` for RAR when available, `7z`/`7zz` for 7Z, and `unar` as a fallback.

You can also start conversions from the web UI at `/convert`. The UI creates background conversion jobs, shows progress, and keeps recent job history. It supports server-side paths and browser file uploads. Uploaded sources go to `ARCHIVE_DIR` when the destination path is empty. Local light mode runs these jobs in a background thread; Docker and full local mode use the Celery worker.

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

Background maintenance jobs live at `/jobs`. You can start and stop library scans, cover thumbnail generation, page fingerprint scans, and strict file duplicate checks there. Duplicate checking uses three stages:

1. Match files with the same byte size.
2. Narrow candidates with SHA-1 of the first 512000 bytes.
3. Confirm duplicates with full-file SHA-256.

Page fingerprint scans read each indexed page and store per-page MD5/SHA-256 plus two perceptual hashes. A fast 64-bit dHash index first filters candidates with `DHASH_CANDIDATE_DISTANCE_THRESHOLD`, then a 64-bit DCT pHash is computed with SciPy for the smaller candidate set and checked with `PHASH_DISTANCE_THRESHOLD`. Byte-identical pages are marked as `duplicate`; visually similar pages are marked as `similar` but are not hidden automatically. These fingerprints are the foundation for later ad-page rules and archive cleanup jobs.

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
