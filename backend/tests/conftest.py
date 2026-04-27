import sys
from pathlib import Path

import duckdb
import httpx
import pytest

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.config import Settings  # noqa: E402
from app.cache.duckdb_store import DuckDBStore  # noqa: E402
from tests.mock_prisma import make_mock  # noqa: E402


@pytest.fixture
def settings(tmp_path) -> Settings:
    s = Settings(
        prisma_console_url="http://mock",
        prisma_api_key="key",
        prisma_api_secret="secret",
        fetch_chunks=2,
        fetch_max_concurrency=2,
        fetch_max_retries=3,
        duckdb_memory_limit="512MB",
    )
    return s


@pytest.fixture
def db():
    conn = duckdb.connect(":memory:")
    yield conn
    conn.close()


@pytest.fixture
def store(db, settings) -> DuckDBStore:
    s = DuckDBStore(db, settings)
    s.init_schema()
    return s


@pytest.fixture
async def mock_prisma_client():
    """An httpx.AsyncClient routed to an in-memory mock Prisma ASGI app."""
    app, events = make_mock(n_events=500)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://mock") as client:
        yield client, events


@pytest.fixture
async def mock_prisma_throttling():
    app, events = make_mock(n_events=300, inject_429_every=5)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://mock") as client:
        yield client, events
