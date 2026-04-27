import logging
from datetime import datetime, timedelta, timezone

import jwt

logger = logging.getLogger("runtime_event_viewer.auth")


def _decode_exp(token: str) -> datetime | None:
    try:
        payload = jwt.decode(token, options={"verify_signature": False})
    except jwt.PyJWTError:
        return None
    exp = payload.get("exp")
    if not exp:
        return None
    try:
        return datetime.fromtimestamp(int(exp), tz=timezone.utc)
    except (TypeError, ValueError):
        return None


class TokenStore:
    def __init__(self) -> None:
        self._token: str | None = None
        self._expires_at: datetime | None = None
        self._key: str | None = None
        self._secret: str | None = None
        self._console_url: str | None = None

    def set_token(self, token: str, expires_at: datetime | None = None) -> None:
        self._token = token
        if expires_at is not None:
            self._expires_at = expires_at
        else:
            decoded = _decode_exp(token)
            self._expires_at = decoded or (datetime.now(timezone.utc) + timedelta(minutes=30))

    def set_credentials(self, key: str, secret: str) -> None:
        self._key = key
        self._secret = secret

    def set_console_url(self, url: str) -> None:
        self._console_url = url.rstrip("/")

    def get_console_url(self) -> str | None:
        return self._console_url

    def get_token(self) -> str | None:
        return self._token

    def get_credentials(self) -> tuple[str | None, str | None]:
        return self._key, self._secret

    def is_authenticated(self) -> bool:
        return self._token is not None

    def needs_refresh(self) -> bool:
        if not self._expires_at:
            return False
        return self._expires_at - datetime.now(timezone.utc) < timedelta(seconds=60)

    def expires_at_iso(self) -> str | None:
        return self._expires_at.isoformat() if self._expires_at else None

    def clear(self) -> None:
        """Wipe all in-memory credentials, including key/secret/console URL.

        Without this, calling /api/auth/logout would still leave the API key,
        secret, and console URL resident in the FastAPI process — a partial
        logout that misled operators about credential scrubbing.
        """
        self._token = None
        self._expires_at = None
        self._key = None
        self._secret = None
        self._console_url = None
