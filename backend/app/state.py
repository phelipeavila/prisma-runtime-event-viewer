import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    import duckdb
    import httpx

    from app.auth.token_store import TokenStore
    from app.config import Settings


@dataclass
class IngestProgress:
    status: str = "idle"  # idle | running | done | error
    rows_loaded: int = 0
    chunks_total: int = 0
    chunks_done: int = 0
    retries: int = 0
    error: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    from_ts: str | None = None
    to_ts: str | None = None

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "rows_loaded": self.rows_loaded,
            "chunks_total": self.chunks_total,
            "chunks_done": self.chunks_done,
            "retries": self.retries,
            "error": self.error,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "from_ts": self.from_ts,
            "to_ts": self.to_ts,
        }


@dataclass
class AppState:
    settings: "Settings"
    token_store: "TokenStore"
    http: "httpx.AsyncClient"
    db: "duckdb.DuckDBPyConnection"
    db_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    ingest: IngestProgress = field(default_factory=IngestProgress)
    ingest_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    ingest_task: Optional[asyncio.Task] = None
    progress_subscribers: set[asyncio.Queue] = field(default_factory=set)
    last_filters: dict | None = None
