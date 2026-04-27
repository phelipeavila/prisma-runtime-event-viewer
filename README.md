# runtime-event-viewer

A single-container web app that pulls runtime container audit events from the
Prisma Cloud API (`/api/v34.03/audits/runtime/container`), caches them
in an in-memory DuckDB instance, lets you filter and sort them in the browser,
and exports CSV — either streamed natively from Prisma's `/download` endpoint or
generated from the local cache.

## Architecture in one paragraph

The user picks a time window (e.g. last 24h) and clicks **Load**. The backend
splits that window into N parallel chunks, paginates each through Prisma's
100-row-per-page API with retry/backoff, and inserts results into DuckDB. The UI
streams progress over Server-Sent Events. After the load finishes, the React
frontend hits `/api/events/query` for filter/sort/page slices that the backend
answers from DuckDB — instant on millions of rows. CSV export uses either
Prisma's native `/download` (streamed proxy) or a cursor-paginated `SELECT` from
DuckDB.

## Run with Docker

```bash
# 1. Build the image (multi-stage: vite build → python:slim runtime)
docker build -t runtime-event-viewer -f docker/Dockerfile .

# 2. Run it. Provide auth via env OR via the in-UI login screen.
docker run --rm -p 8000:8000 \
  -e PRISMA_CONSOLE_URL=https://console.example.com \
  -e PRISMA_API_KEY=... \
  -e PRISMA_API_SECRET=... \
  runtime-event-viewer

# Then open http://localhost:8000
```

If `PRISMA_CONSOLE_URL` and either `PRISMA_API_TOKEN` or
(`PRISMA_API_KEY`+`PRISMA_API_SECRET`) are present in the environment, the app
auto-authenticates on startup. If any are missing, the UI shows a login form on
first visit.

## Local dev

```bash
# Backend (terminal 1)
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'
uvicorn app.main:create_app --factory --reload --port 8000

# Frontend (terminal 2)
cd frontend
npm install
npm run dev    # http://localhost:5173 — proxies /api to :8000
```

## Environment variables

See `.env.example`. Highlights:

| Var | Default | Notes |
|---|---|---|
| `PRISMA_CONSOLE_URL` | — | e.g. `https://console.example.com` |
| `PRISMA_API_TOKEN` | — | Pre-issued JWT (option A) |
| `PRISMA_API_KEY` / `PRISMA_API_SECRET` | — | Exchanged at startup (option B) |
| `PRISMA_VERIFY_TLS` | `true` | Set to `false` only for self-signed test environments |
| `FETCH_CHUNKS` | `8` | Number of parallel time-range chunks during ingest |
| `FETCH_MAX_CONCURRENCY` | `8` | Concurrency cap (one in-flight request per chunk) |
| `DUCKDB_MEMORY_LIMIT` | `4GB` | Cache memory budget — bump for >1M rows |
| `DUCKDB_KEEP_RAW_JSON` | `true` | Disable to save memory if row-detail drawer not needed |

`FETCH_PAGE_SIZE` is **not** configurable: Prisma caps the page size at 100.

## API surface (for reference)

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/auth/status` | Check auth state |
| `POST` | `/api/auth/login` | Token or key+secret login |
| `POST` | `/api/auth/logout` | Clear in-process token |
| `POST` | `/api/ingest` | Start a time-window load |
| `GET` | `/api/ingest/stream` | SSE progress |
| `POST` | `/api/ingest/cancel` | Cancel in-flight ingest |
| `POST` | `/api/events/query` | Filtered/paginated query against DuckDB |
| `GET` | `/api/events/facets?field=...` | Top-N values for a facetable column |
| `GET` | `/api/export/native?filters=...` | Streamed CSV from Prisma's `/download` |
| `GET` | `/api/export/cache?filters=...` | Streamed CSV from DuckDB |
| `GET` | `/api/meta` | Auth + ingest + cache snapshot |

## Running tests

```bash
cd backend
pytest
```

Tests run against an in-process **mock Prisma server** (`tests/mock_prisma.py`)
that emits a Faker-seeded synthetic dataset, so no real tenant is needed.

## Security notes

- The token is held only in the FastAPI process (`app.state`) and never sent to
  the browser. The browser does not need to know it.
- This is a single-user app: there is no per-user session model. Run it on a
  private network or behind a VPN.
- DuckDB queries are parameterized; user-supplied filter values are never
  interpolated into SQL strings.
- Multi-value filters are capped at 200 entries per field to avoid pathological
  query sizes.
