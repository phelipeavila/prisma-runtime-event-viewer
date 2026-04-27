import asyncio
import json
import logging
from datetime import datetime, timezone

from app.cache.duckdb_store import DuckDBStore
from app.prisma.client import PrismaClient, PrismaAuthError, RetryCounter
from app.prisma.params import filters_to_prisma_params
from app.state import AppState
from app.util.sse import format_sse
from app.util.time_chunks import split_time_range

logger = logging.getLogger("runtime_event_viewer.fetcher")

SENTINEL = object()


async def _broadcast(state: AppState, event: str = "progress") -> None:
    payload = state.ingest.to_dict()
    msg = format_sse(event, payload)
    dead = []
    for q in list(state.progress_subscribers):
        try:
            q.put_nowait(msg)
        except asyncio.QueueFull:
            # If a subscriber is too slow, drop them so we don't stall the writer.
            dead.append(q)
    for q in dead:
        state.progress_subscribers.discard(q)


async def run_ingest(
    state: AppState,
    store: DuckDBStore,
    from_ts: str,
    to_ts: str,
    filters: dict,
    chunks: int,
) -> None:
    settings = state.settings
    console_url = state.token_store.get_console_url()
    if not state.token_store.is_authenticated() or not console_url:
        state.ingest.status = "error"
        state.ingest.error = "Not authenticated"
        await _broadcast(state, "error")
        return

    client = PrismaClient(
        http=state.http,
        console_url=console_url,
        token=state.token_store.get_token(),
        max_retries=settings.fetch_max_retries,
    )

    state.ingest.status = "running"
    state.ingest.rows_loaded = 0
    state.ingest.chunks_total = chunks
    state.ingest.chunks_done = 0
    state.ingest.retries = 0
    state.ingest.error = None
    state.ingest.started_at = datetime.now(timezone.utc)
    state.ingest.finished_at = None
    state.ingest.from_ts = from_ts
    state.ingest.to_ts = to_ts

    async with state.db_lock:
        store.truncate()

    intervals = split_time_range(from_ts, to_ts, chunks)
    sem = asyncio.Semaphore(settings.fetch_max_concurrency)
    queue: asyncio.Queue = asyncio.Queue(maxsize=64)
    retry_counter = RetryCounter()

    base_params = filters_to_prisma_params({k: v for k, v in filters.items() if k not in ("from_", "to")})

    async def worker(lo: str, hi: str, idx: int) -> None:
        offset = 0
        async with sem:
            while True:
                params = list(base_params) + [
                    ("from", lo),
                    ("to", hi),
                    ("offset", str(offset)),
                    ("limit", str(settings.fetch_page_size)),
                    ("sort", "time"),
                    ("reverse", "true"),
                ]
                try:
                    rows = await client.list_audits(params, retry_counter=retry_counter)
                except Exception as exc:
                    logger.exception("chunk %d failed at offset %d: %s", idx, offset, exc)
                    raise
                if not rows:
                    break
                await queue.put(rows)
                if len(rows) < settings.fetch_page_size:
                    break
                offset += len(rows)
        state.ingest.chunks_done += 1
        state.ingest.retries = retry_counter.count
        await _broadcast(state)

    async def writer() -> None:
        while True:
            item = await queue.get()
            if item is SENTINEL:
                return
            async with state.db_lock:
                count = store.insert_many(item)
            state.ingest.rows_loaded += count
            state.ingest.retries = retry_counter.count
            await _broadcast(state)

    writer_task = asyncio.create_task(writer())
    try:
        await asyncio.gather(*(worker(lo, hi, i) for i, (lo, hi) in enumerate(intervals)))
        await queue.put(SENTINEL)
        await writer_task
        state.ingest.status = "done"
        state.ingest.finished_at = datetime.now(timezone.utc)
        await _broadcast(state, "done")
    except PrismaAuthError as exc:
        state.ingest.status = "error"
        state.ingest.error = f"Authentication failed: {exc}"
        state.ingest.finished_at = datetime.now(timezone.utc)
        await _broadcast(state, "error")
        if not writer_task.done():
            await queue.put(SENTINEL)
            await writer_task
    except Exception as exc:
        logger.exception("ingest failed: %s", exc)
        state.ingest.status = "error"
        state.ingest.error = str(exc)
        state.ingest.finished_at = datetime.now(timezone.utc)
        await _broadcast(state, "error")
        if not writer_task.done():
            await queue.put(SENTINEL)
            await writer_task
