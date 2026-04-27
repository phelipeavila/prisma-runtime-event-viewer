import asyncio

import httpx
import pytest

from app.auth.routes import _normalize_console_url
from app.main import create_app
from tests.mock_prisma import make_mock


@pytest.fixture(autouse=True)
def _relax_login_gates(monkeypatch):
    """Tests use the in-memory ASGI mock at `http://mock`, which is both
    plain HTTP and a non-resolvable hostname. Phase-1 hardening rejects both
    by default; opt back in here so end-to-end login tests still exercise the
    real login path.
    """
    monkeypatch.setenv("ALLOW_HTTP_CONSOLE", "true")
    monkeypatch.setenv("ALLOW_INTERNAL_CONSOLE", "true")


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("https://console.example.com", "https://console.example.com"),
        ("https://console.example.com/", "https://console.example.com"),
        ("console.example.com", "https://console.example.com"),
        ("HTTPS://console.example.com", "HTTPS://console.example.com"),
        ("https://console.example.com/api", "https://console.example.com"),
        ("https://console.example.com/api/", "https://console.example.com"),
        ("https://console.example.com/api/v34.01/authenticate", "https://console.example.com"),
        ("  https://console.example.com  ", "https://console.example.com"),
        ("", ""),
    ],
)
def test_normalize_console_url(raw, expected):
    assert _normalize_console_url(raw) == expected


@pytest.mark.asyncio
async def test_login_keysecret_end_to_end():
    mock_app, _ = make_mock(n_events=10)
    mock_transport = httpx.ASGITransport(app=mock_app)

    our_app = create_app()
    async with our_app.router.lifespan_context(our_app):
        await our_app.state.app.http.aclose()
        our_app.state.app.http = httpx.AsyncClient(
            transport=mock_transport, base_url="http://mock"
        )
        transport = httpx.ASGITransport(app=our_app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.post(
                "/api/auth/login",
                json={
                    "mode": "keysecret",
                    "console_url": "http://mock/api/",  # exercise normalization
                    "key": "id",
                    "secret": "shh",
                },
            )
            assert r.status_code == 200, r.text
            assert r.json()["authenticated"] is True

            r = await c.get("/api/auth/status")
            assert r.json()["authenticated"] is True
            assert r.json()["console_url"] == "http://mock"


@pytest.mark.asyncio
async def test_login_token_mode():
    our_app = create_app()
    async with our_app.router.lifespan_context(our_app):
        transport = httpx.ASGITransport(app=our_app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.post(
                "/api/auth/login",
                json={
                    "mode": "token",
                    "console_url": "https://console.example.com",
                    "token": "abc.def.ghi",
                },
            )
            assert r.status_code == 200
            r = await c.get("/api/auth/status")
            assert r.json()["authenticated"] is True


@pytest.mark.asyncio
async def test_ui_only_login_then_ingest_succeeds():
    """Regression: when PRISMA_CONSOLE_URL is NOT in env, the user logs in via UI
    only. Ingest must use the URL from token_store, not from settings."""
    mock_app, _ = make_mock(n_events=10)
    mock_transport = httpx.ASGITransport(app=mock_app)

    our_app = create_app()
    async with our_app.router.lifespan_context(our_app):
        # Sanity: env-bootstrap left console_url empty.
        assert our_app.state.app.settings.prisma_console_url is None

        await our_app.state.app.http.aclose()
        our_app.state.app.http = httpx.AsyncClient(
            transport=mock_transport, base_url="http://mock"
        )
        transport = httpx.ASGITransport(app=our_app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.post(
                "/api/auth/login",
                json={"mode": "keysecret", "console_url": "http://mock", "key": "id", "secret": "shh"},
            )
            assert r.status_code == 200, r.text

            r = await c.post(
                "/api/ingest",
                json={
                    "from": "2026-04-25T00:00:00Z",
                    "to": "2026-04-26T00:00:00Z",
                    "chunks": 2,
                    "filters": {},
                },
            )
            assert r.status_code == 200, r.text

            # Wait briefly for the background task to start and either succeed or
            # surface its error via state.ingest.
            for _ in range(20):
                await asyncio.sleep(0.05)
                if our_app.state.app.ingest.status in ("done", "error"):
                    break
            assert our_app.state.app.ingest.error != "Not authenticated"
            assert our_app.state.app.ingest.status == "done"


@pytest.mark.asyncio
async def test_login_missing_console_url_400():
    our_app = create_app()
    async with our_app.router.lifespan_context(our_app):
        transport = httpx.ASGITransport(app=our_app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.post(
                "/api/auth/login",
                json={"mode": "token", "console_url": "", "token": "x"},
            )
            assert r.status_code == 400
