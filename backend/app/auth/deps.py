"""Shared FastAPI dependencies for auth-gated endpoints.

The app is single-user but the in-process token is global, so anything that
queries the cache, talks to Prisma, or leaks ingest metadata must require an
authenticated session before responding.
"""

from fastapi import HTTPException, Request

from app.state import AppState


def get_state(request: Request) -> AppState:
    return request.app.state.app


def require_auth(request: Request) -> AppState:
    """FastAPI dependency: ensure the in-process TokenStore is authenticated."""
    state = get_state(request)
    if not state.token_store.is_authenticated():
        raise HTTPException(status_code=401, detail="Not authenticated")
    return state
