from fastapi import APIRouter, Depends, Request

from app.auth.deps import require_auth
from app.state import AppState

router = APIRouter()


@router.get("/meta")
async def meta(request: Request, state: AppState = Depends(require_auth)):
    store = request.app.state.store
    async with state.db_lock:
        row_count = store.count()
        time_min, time_max = store.time_bounds()
    return {
        "authenticated": state.token_store.is_authenticated(),
        "console_url": state.token_store.get_console_url(),
        "expires_at": state.token_store.expires_at_iso(),
        "ingest": state.ingest.to_dict(),
        "row_count": row_count,
        "time_bounds": {"min": time_min, "max": time_max},
        "last_filters": state.last_filters,
    }
