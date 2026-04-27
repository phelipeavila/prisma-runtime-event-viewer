import logging
from contextlib import asynccontextmanager
from pathlib import Path

import duckdb
import httpx
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api import events as events_routes
from app.api import export as export_routes
from app.api import ingest as ingest_routes
from app.api import meta as meta_routes
from app.auth import bootstrap as auth_bootstrap
from app.auth import routes as auth_routes
from app.auth.token_store import TokenStore
from app.cache.duckdb_store import DuckDBStore
from app.config import Settings, get_settings
from app.state import AppState

logger = logging.getLogger("runtime_event_viewer")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


class SPAStaticFiles(StaticFiles):
    """Serve a static SPA, falling back to index.html on filesystem 404 so client-side
    routes survive hard-refresh. /api/* is mounted before this so it never hits here."""

    async def get_response(self, path: str, scope):
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code == 404:
                index = Path(self.directory) / "index.html"
                if index.exists():
                    return FileResponse(index)
            raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings: Settings = app.state.settings
    http = httpx.AsyncClient(
        verify=settings.prisma_verify_tls,
        timeout=httpx.Timeout(settings.fetch_request_timeout, connect=10.0),
    )
    db = duckdb.connect(
        ":memory:",
        config={
            "threads": settings.duckdb_threads,
            "memory_limit": settings.duckdb_memory_limit,
        },
    )
    store = DuckDBStore(db, settings)
    store.init_schema()
    token_store = TokenStore()

    state = AppState(
        settings=settings,
        token_store=token_store,
        http=http,
        db=db,
    )
    app.state.app = state
    app.state.store = store

    await auth_bootstrap.bootstrap(state)

    try:
        yield
    finally:
        if state.ingest_task and not state.ingest_task.done():
            state.ingest_task.cancel()
        await http.aclose()
        db.close()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="runtime-event-viewer", lifespan=lifespan)
    app.state.settings = settings

    app.include_router(auth_routes.router, prefix="/api/auth", tags=["auth"])
    app.include_router(ingest_routes.router, prefix="/api/ingest", tags=["ingest"])
    app.include_router(events_routes.router, prefix="/api/events", tags=["events"])
    app.include_router(export_routes.router, prefix="/api/export", tags=["export"])
    app.include_router(meta_routes.router, prefix="/api", tags=["meta"])

    static_dir = settings.static_dir
    static_dir.mkdir(parents=True, exist_ok=True)
    if not (static_dir / "index.html").exists():
        # Placeholder so dev runs before the SPA is built don't 404 the root.
        (static_dir / "index.html").write_text(
            "<!doctype html><meta charset='utf-8'>"
            "<title>runtime-event-viewer</title>"
            "<p>Frontend not built. Run <code>pnpm build</code> in <code>frontend/</code>"
            " or use <code>pnpm dev</code> (proxies /api).</p>",
            encoding="utf-8",
        )
    app.mount("/", SPAStaticFiles(directory=str(static_dir), html=True), name="spa")

    return app
