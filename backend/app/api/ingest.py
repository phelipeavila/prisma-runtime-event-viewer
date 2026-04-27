import asyncio

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.auth.deps import require_auth
from app.prisma.fetcher import run_ingest
from app.state import AppState
from app.util.sse import format_sse, heartbeat_stream

router = APIRouter()


class IngestRequest(BaseModel):
    from_: str = Field(alias="from")
    to: str
    chunks: int = Field(default=8, ge=1, le=64)
    filters: dict = Field(default_factory=dict)

    model_config = {"populate_by_name": True}


@router.post("")
@router.post("/")
async def start_ingest(
    body: IngestRequest,
    request: Request,
    state: AppState = Depends(require_auth),
):
    store = request.app.state.store

    async with state.ingest_lock:
        if state.ingest.status == "running":
            raise HTTPException(status_code=409, detail="Ingest already running")

        state.last_filters = body.filters
        task = asyncio.create_task(
            run_ingest(
                state=state,
                store=store,
                from_ts=body.from_,
                to_ts=body.to,
                filters=body.filters,
                chunks=body.chunks,
            )
        )
        state.ingest_task = task

    return {"status": "running", "chunks_total": body.chunks}


@router.get("/stream")
async def stream(request: Request, state: AppState = Depends(require_auth)):
    queue: asyncio.Queue = asyncio.Queue(maxsize=128)
    state.progress_subscribers.add(queue)

    # Send current snapshot immediately so late subscribers see state.
    try:
        queue.put_nowait(format_sse("progress", state.ingest.to_dict()))
    except asyncio.QueueFull:
        pass

    async def gen():
        try:
            async for chunk in heartbeat_stream(queue):
                yield chunk
                # Auto-close once an ingest finishes successfully.
                if state.ingest.status in ("done", "error") and queue.empty():
                    break
        finally:
            state.progress_subscribers.discard(queue)

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/cancel")
async def cancel(request: Request, state: AppState = Depends(require_auth)):
    if state.ingest_task and not state.ingest_task.done():
        state.ingest_task.cancel()
        state.ingest.status = "error"
        state.ingest.error = "Cancelled"
        return {"cancelled": True}
    return {"cancelled": False}
