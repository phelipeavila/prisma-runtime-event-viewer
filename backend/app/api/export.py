import json
from urllib.parse import unquote_plus

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from app.auth.deps import require_auth
from app.cache.filter_sql import FilterValidationError, build_where
from app.prisma.client import PrismaClient
from app.prisma.params import filters_to_prisma_params
from app.state import AppState

router = APIRouter()


def _decode_filters(filters_json: str | None) -> dict:
    if not filters_json:
        return {}
    try:
        return json.loads(unquote_plus(filters_json))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid filters JSON: {exc}")


@router.get("/native")
async def export_native(
    request: Request,
    filters: str | None = Query(default=None),
    state: AppState = Depends(require_auth),
):
    """Stream Prisma's native CSV /download endpoint with the same filters applied."""
    console_url = state.token_store.get_console_url()
    if not console_url:
        raise HTTPException(status_code=401, detail="Not authenticated")

    f = _decode_filters(filters)
    prisma_params = filters_to_prisma_params(f)
    client = PrismaClient(
        http=state.http,
        console_url=console_url,
        token=state.token_store.get_token(),
        max_retries=state.settings.fetch_max_retries,
    )

    async def body():
        async for chunk in client.stream_audits_csv(prisma_params):
            yield chunk

    return StreamingResponse(
        body(),
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="runtime_container_audits_native.csv"',
            "Cache-Control": "no-store",
        },
    )


@router.get("/cache")
async def export_cache(
    request: Request,
    filters: str | None = Query(default=None),
    state: AppState = Depends(require_auth),
):
    """Stream the current DuckDB cache as CSV, applying the same Filters used in the table."""
    store = request.app.state.store
    f = _decode_filters(filters)
    try:
        build_where(f)
    except FilterValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    async def body():
        async for chunk in store.stream_csv(f):
            yield chunk

    return StreamingResponse(
        body(),
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="runtime_container_audits_cache.csv"',
            "Cache-Control": "no-store",
        },
    )
