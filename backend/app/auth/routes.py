import ipaddress
import logging
import socket
from typing import Literal
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.prisma.client import PrismaClient, PrismaAuthError
from app.state import AppState

logger = logging.getLogger("runtime_event_viewer.auth")

router = APIRouter()


# Hosts that the AWS / Azure / GCP instance metadata services live on. These
# are technically not in the IPv4 link-local block (`169.254.0.0/16` is, but
# users sometimes use `metadata.google.internal` etc. — we add belt-and-braces).
_METADATA_HOSTS = frozenset(
    {
        "metadata.google.internal",
        "metadata.azure.com",
        "169.254.169.254",
    }
)


class LoginBody(BaseModel):
    mode: Literal["token", "keysecret"]
    console_url: str
    token: str | None = None
    key: str | None = None
    secret: str | None = None


def _state(request: Request) -> AppState:
    return request.app.state.app


def _normalize_console_url(raw: str) -> str:
    url = raw.strip().rstrip("/")
    if not url:
        return url
    if not url.lower().startswith(("http://", "https://")):
        url = "https://" + url
    # Strip a trailing /api or /api/v34.x that users sometimes paste from a curl example.
    while True:
        lower = url.lower()
        if lower.endswith("/api"):
            url = url[: -len("/api")]
        elif "/api/" in lower:
            url = url[: lower.index("/api/")]
        else:
            break
    return url.rstrip("/")


def _is_loopback_client(request: Request) -> bool:
    """True when the originating peer is on a loopback interface.

    The token is global process state, so any unauthenticated caller capable of
    reaching the bind address could otherwise hijack the running session.
    Loopback enforcement is the simplest mitigation that doesn't require
    redesigning the single-user auth model.
    """
    client = request.client
    if client is None or not client.host:
        # Starlette uses None for direct ASGI lifespan calls and certain test
        # transports. Treat as not-loopback so the explicit env opt-in is
        # required to allow remote login.
        return False
    try:
        return ipaddress.ip_address(client.host).is_loopback
    except ValueError:
        return client.host in {"localhost"}


def _is_disallowed_address(addr: ipaddress._BaseAddress) -> bool:
    return (
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_multicast
        or addr.is_reserved
        or addr.is_unspecified
    )


def _check_console_url_allowed(
    console_url: str,
    *,
    allow_http: bool,
    allow_internal: bool,
) -> None:
    """Reject obviously-unsafe console URLs.

    Raises HTTPException(400) for invalid URLs, http-without-opt-in, or hosts
    that resolve to private/loopback/link-local/metadata addresses without the
    operator opt-in.
    """
    parsed = urlparse(console_url)
    if parsed.scheme.lower() not in ("http", "https"):
        raise HTTPException(status_code=400, detail="console_url must be http(s)")
    if parsed.scheme.lower() == "http" and not allow_http:
        raise HTTPException(
            status_code=400,
            detail=(
                "console_url must use https://. Set ALLOW_HTTP_CONSOLE=true to "
                "override (not recommended outside test fixtures)."
            ),
        )
    host = parsed.hostname
    if not host:
        raise HTTPException(status_code=400, detail="console_url has no hostname")

    if allow_internal:
        return

    if host.lower() in _METADATA_HOSTS:
        raise HTTPException(
            status_code=400,
            detail="console_url points at a cloud metadata host",
        )

    # Direct IP-literal? Reject if it falls in any disallowed range.
    try:
        addr = ipaddress.ip_address(host)
        if _is_disallowed_address(addr):
            raise HTTPException(
                status_code=400,
                detail=(
                    f"console_url IP {host} is in a private/loopback/link-local "
                    "range. Set ALLOW_INTERNAL_CONSOLE=true to override."
                ),
            )
        return
    except ValueError:
        pass

    # Hostname: best-effort DNS resolution. If lookup fails (test fixtures,
    # offline runs), fall through; the egress call will fail naturally.
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return
    for info in infos:
        sockaddr = info[4]
        try:
            addr = ipaddress.ip_address(sockaddr[0])
        except (ValueError, IndexError):
            continue
        if _is_disallowed_address(addr):
            raise HTTPException(
                status_code=400,
                detail=(
                    f"console_url host {host!r} resolves to a private/loopback "
                    "address. Set ALLOW_INTERNAL_CONSOLE=true to override."
                ),
            )


@router.get("/status")
async def status(request: Request):
    state = _state(request)
    return {
        "authenticated": state.token_store.is_authenticated(),
        "console_url": state.token_store.get_console_url(),
        "expires_at": state.token_store.expires_at_iso(),
    }


@router.post("/login")
async def login(body: LoginBody, request: Request):
    state = _state(request)
    settings = state.settings

    # Loopback gate: a network attacker reaching the bind address could
    # otherwise hijack the in-process token. Operators who deliberately want
    # to expose login (e.g. behind a reverse proxy with their own auth) must
    # opt in via ALLOW_REMOTE_LOGIN=true.
    if not settings.allow_remote_login and not _is_loopback_client(request):
        client_host = request.client.host if request.client else "unknown"
        logger.warning("login rejected: non-loopback caller %s", client_host)
        raise HTTPException(
            status_code=403,
            detail=(
                "Login is restricted to loopback callers. Connect via the SPA "
                "served on the same host, or set ALLOW_REMOTE_LOGIN=true to "
                "opt in to remote login."
            ),
        )

    console_url = _normalize_console_url(body.console_url)
    if not console_url:
        raise HTTPException(status_code=400, detail="console_url required")

    _check_console_url_allowed(
        console_url,
        allow_http=settings.allow_http_console,
        allow_internal=settings.allow_internal_console,
    )
    state.token_store.set_console_url(console_url)

    if body.mode == "token":
        if not body.token:
            raise HTTPException(status_code=400, detail="token required for mode=token")
        state.token_store.set_token(body.token)
        return {"authenticated": True}

    if not (body.key and body.secret):
        raise HTTPException(status_code=400, detail="key and secret required for mode=keysecret")

    client = PrismaClient(state.http, console_url)
    try:
        token = await client.authenticate(body.key, body.secret)
    except PrismaAuthError as exc:
        logger.warning("login: invalid credentials for %s", console_url)
        raise HTTPException(status_code=401, detail=str(exc))
    except httpx.ConnectError as exc:
        logger.warning("login: cannot reach %s — %s", console_url, exc)
        raise HTTPException(
            status_code=502,
            detail=f"Cannot reach {console_url}. Check the URL, network, and TLS verification.",
        )
    except httpx.HTTPStatusError as exc:
        sc = exc.response.status_code
        snippet = (exc.response.text or "")[:200]
        logger.warning("login: HTTP %s from %s — %s", sc, console_url, snippet)
        raise HTTPException(
            status_code=502,
            detail=(
                f"Authentication endpoint at {console_url}/api/v34.01/authenticate returned HTTP {sc}. "
                f"Body: {snippet!r}"
            ),
        )
    except Exception as exc:
        logger.exception("login: unexpected error against %s", console_url)
        raise HTTPException(status_code=502, detail=f"Authentication call failed: {type(exc).__name__}: {exc}")

    state.token_store.set_credentials(body.key, body.secret)
    state.token_store.set_token(token)
    return {"authenticated": True}


@router.post("/logout")
async def logout(request: Request):
    state = _state(request)
    state.token_store.clear()
    return {"authenticated": False}
