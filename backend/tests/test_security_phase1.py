"""Coverage for the Phase-1 security hardening:

* `require_auth` dependency on data endpoints
* Loopback gate on `/api/auth/login`
* `TokenStore.clear()` wipes key + secret + console URL
* Console-URL validation (http://, internal addresses, metadata hosts)
"""

import httpx
import pytest

from app.auth.token_store import TokenStore
from app.main import create_app


# ---------------------------------------------------------------------------
# require_auth
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method, path, body",
    [
        ("POST", "/api/events/query", {}),
        ("GET", "/api/events/facets?field=type", None),
        ("GET", "/api/export/cache", None),
        ("GET", "/api/export/native", None),
        ("GET", "/api/meta", None),
        ("POST", "/api/ingest", {"from": "2026-01-01T00:00:00Z", "to": "2026-01-02T00:00:00Z"}),
        ("GET", "/api/ingest/stream", None),
        ("POST", "/api/ingest/cancel", None),
    ],
)
async def test_data_endpoints_require_auth(method, path, body):
    our_app = create_app()
    async with our_app.router.lifespan_context(our_app):
        transport = httpx.ASGITransport(app=our_app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            if method == "POST":
                r = await c.post(path, json=body or {})
            else:
                r = await c.get(path)
            assert r.status_code == 401, f"{method} {path} -> {r.status_code} {r.text}"


# ---------------------------------------------------------------------------
# Loopback gate on login
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_login_rejects_non_loopback_by_default(monkeypatch):
    # Make sure no ALLOW_REMOTE_LOGIN env leaks in from outer scope.
    monkeypatch.delenv("ALLOW_REMOTE_LOGIN", raising=False)

    our_app = create_app()
    async with our_app.router.lifespan_context(our_app):
        # httpx.ASGITransport defaults to client=("127.0.0.1", 123); override
        # to simulate a remote peer.
        transport = httpx.ASGITransport(app=our_app, client=("203.0.113.5", 4242))
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.post(
                "/api/auth/login",
                json={
                    "mode": "token",
                    "console_url": "https://console.example.com",
                    "token": "abc",
                },
            )
            assert r.status_code == 403, r.text


@pytest.mark.asyncio
async def test_login_allows_non_loopback_with_env_opt_in(monkeypatch):
    monkeypatch.setenv("ALLOW_REMOTE_LOGIN", "true")

    our_app = create_app()
    async with our_app.router.lifespan_context(our_app):
        transport = httpx.ASGITransport(app=our_app, client=("203.0.113.5", 4242))
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.post(
                "/api/auth/login",
                json={
                    "mode": "token",
                    "console_url": "https://console.example.com",
                    "token": "abc",
                },
            )
            assert r.status_code == 200, r.text


# ---------------------------------------------------------------------------
# console_url validation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_login_rejects_http_by_default(monkeypatch):
    monkeypatch.delenv("ALLOW_HTTP_CONSOLE", raising=False)

    our_app = create_app()
    async with our_app.router.lifespan_context(our_app):
        transport = httpx.ASGITransport(app=our_app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.post(
                "/api/auth/login",
                json={
                    "mode": "token",
                    "console_url": "http://console.example.com",
                    "token": "abc",
                },
            )
            assert r.status_code == 400
            assert "https" in r.text.lower()


@pytest.mark.asyncio
async def test_login_rejects_internal_ip_by_default(monkeypatch):
    monkeypatch.delenv("ALLOW_INTERNAL_CONSOLE", raising=False)

    our_app = create_app()
    async with our_app.router.lifespan_context(our_app):
        transport = httpx.ASGITransport(app=our_app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            for ip in ("127.0.0.1", "10.0.0.1", "169.254.169.254", "192.168.1.1"):
                r = await c.post(
                    "/api/auth/login",
                    json={
                        "mode": "token",
                        "console_url": f"https://{ip}",
                        "token": "abc",
                    },
                )
                assert r.status_code == 400, f"{ip}: {r.text}"


@pytest.mark.asyncio
async def test_login_rejects_metadata_host(monkeypatch):
    monkeypatch.delenv("ALLOW_INTERNAL_CONSOLE", raising=False)

    our_app = create_app()
    async with our_app.router.lifespan_context(our_app):
        transport = httpx.ASGITransport(app=our_app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.post(
                "/api/auth/login",
                json={
                    "mode": "token",
                    "console_url": "https://metadata.google.internal",
                    "token": "abc",
                },
            )
            assert r.status_code == 400
            assert "metadata" in r.text.lower()


# ---------------------------------------------------------------------------
# TokenStore.clear()
# ---------------------------------------------------------------------------


def test_token_store_clear_wipes_all_credentials():
    ts = TokenStore()
    ts.set_console_url("https://console.example.com")
    ts.set_credentials("k", "s")
    ts.set_token("a.b.c")

    assert ts.is_authenticated()
    assert ts.get_console_url() == "https://console.example.com"
    assert ts.get_credentials() == ("k", "s")

    ts.clear()

    assert not ts.is_authenticated()
    assert ts.get_token() is None
    assert ts.get_console_url() is None
    assert ts.get_credentials() == (None, None)
