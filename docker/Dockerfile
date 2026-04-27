# syntax=docker/dockerfile:1.6

# ---------- Stage 1: build SPA ----------
FROM node:20-alpine AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json* ./
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi
COPY frontend/ ./
# Build SPA into ./dist (overrides vite.config outDir)
RUN npx vite build --outDir dist --emptyOutDir

# ---------- Stage 2: runtime ----------
FROM python:3.12-slim AS runtime
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps from pyproject.toml (pip resolves dependencies)
COPY backend/pyproject.toml ./
RUN pip install --no-cache-dir .

# App code + built SPA
COPY backend/app ./app
COPY --from=web /web/dist ./app/static

EXPOSE 8000

# Documented runtime env vars (set at `docker run`):
#   PRISMA_CONSOLE_URL          (required for non-interactive auth)
#   PRISMA_API_TOKEN            (option A)
#   PRISMA_API_KEY              (option B)
#   PRISMA_API_SECRET           (option B)
#   PRISMA_VERIFY_TLS           (default: true)
#   FETCH_CHUNKS                (default: 8)
#   FETCH_MAX_CONCURRENCY       (default: 8)
#   DUCKDB_THREADS              (default: 4)
#   DUCKDB_MEMORY_LIMIT         (default: 4GB)
#   DUCKDB_KEEP_RAW_JSON        (default: true)
#   BIND_HOST                   (default: 0.0.0.0)
#   BIND_PORT                   (default: 8000)

USER 65532:65532

CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
