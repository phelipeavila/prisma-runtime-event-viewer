from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.auth.deps import require_auth
from app.cache.filter_sql import FilterValidationError
from app.state import AppState

router = APIRouter()


@router.post("/query")
async def query_events(
    filters: dict, request: Request, state: AppState = Depends(require_auth)
):
    store = request.app.state.store
    page = int(filters.get("page", 0))
    page_size = int(filters.get("page_size", 100))
    try:
        async with state.db_lock:
            rows, total = store.query(filters)
    except FilterValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {
        "rows": rows,
        "page": page,
        "page_size": page_size,
        "total": total,
    }


@router.get("/facets")
async def facets(
    request: Request,
    field: str = Query(...),
    state: AppState = Depends(require_auth),
):
    store = request.app.state.store
    try:
        async with state.db_lock:
            return store.facet(field)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
