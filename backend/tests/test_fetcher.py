import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from app.prisma.client import PrismaClient
from app.prisma.fetcher import run_ingest
from app.state import AppState, IngestProgress
from app.auth.token_store import TokenStore


def _make_state(http, settings, store_holder):
    ts = TokenStore()
    ts.set_console_url("http://mock")
    ts.set_token("mock.jwt.token")
    return AppState(
        settings=settings,
        token_store=ts,
        http=http,
        db=store_holder.db,
    )


@pytest.mark.asyncio
async def test_ingest_loads_all_events(mock_prisma_client, settings, store):
    http, events = mock_prisma_client
    state = _make_state(http, settings, store)
    now = datetime.now(timezone.utc)
    from_ts = (now - timedelta(days=14)).isoformat()
    to_ts = now.isoformat()

    await run_ingest(state, store, from_ts, to_ts, filters={}, chunks=2)
    assert state.ingest.status == "done"
    # Mock generated 500 events; some may fall outside the 14-day window —
    # all events fall within last 7d (mock generates within 7d), so all should land.
    assert store.count() == len(events)


@pytest.mark.asyncio
async def test_ingest_handles_429(mock_prisma_throttling, settings, store):
    http, events = mock_prisma_throttling
    state = _make_state(http, settings, store)
    now = datetime.now(timezone.utc)
    from_ts = (now - timedelta(days=14)).isoformat()
    to_ts = now.isoformat()

    await run_ingest(state, store, from_ts, to_ts, filters={}, chunks=2)
    assert state.ingest.status == "done"
    assert state.ingest.retries > 0
    assert store.count() == len(events)


@pytest.mark.asyncio
async def test_ingest_dedupes_on_chunk_overlap(mock_prisma_client, settings, store):
    http, events = mock_prisma_client
    state = _make_state(http, settings, store)
    now = datetime.now(timezone.utc)
    from_ts = (now - timedelta(days=14)).isoformat()
    to_ts = now.isoformat()

    await run_ingest(state, store, from_ts, to_ts, filters={}, chunks=4)
    # Even with multiple chunks possibly overlapping, count never exceeds the dataset size.
    assert store.count() <= len(events)
    assert store.count() == len(events)
