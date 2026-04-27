from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    prisma_console_url: str | None = None
    prisma_api_token: str | None = None
    prisma_api_key: str | None = None
    prisma_api_secret: str | None = None
    prisma_verify_tls: bool = True

    # Prisma's hard cap is 100 rows per page — not configurable.
    fetch_page_size: int = Field(default=100, frozen=True)
    fetch_chunks: int = 8
    fetch_max_concurrency: int = 8
    fetch_max_retries: int = 5
    fetch_request_timeout: float = 60.0

    duckdb_threads: int = 4
    duckdb_memory_limit: str = "4GB"
    duckdb_keep_raw_json: bool = True

    bind_host: str = "0.0.0.0"
    bind_port: int = 8000

    # Security gates for /api/auth/login.
    # By default, login is restricted to loopback callers, must use https://,
    # and must point at a non-private console URL. Each can be opted out of
    # individually for self-hosted/private deployments.
    allow_remote_login: bool = False
    allow_http_console: bool = False
    allow_internal_console: bool = False

    static_dir: Path = Path(__file__).parent / "static"
    schema_path: Path = Path(__file__).parent / "cache" / "schema.sql"


def get_settings() -> Settings:
    return Settings()
