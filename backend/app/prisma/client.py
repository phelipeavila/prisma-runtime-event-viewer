import json
import logging
from typing import AsyncIterator

import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential_jitter,
)

logger = logging.getLogger("runtime_event_viewer.prisma")

TARGET_ENV_HEADER = "x-prisma-cloud-target-env"
TARGET_ENV_VALUE = json.dumps({"permission": "monitorRuntimeContainers"})

AUTH_PATH = "/api/v34.01/authenticate"
AUDITS_PATH = "/api/v34.03/audits/runtime/container"
AUDITS_DOWNLOAD_PATH = "/api/v34.03/audits/runtime/container/download"


class PrismaError(Exception):
    pass


class PrismaAuthError(PrismaError):
    pass


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, httpx.TransportError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in {429, 500, 502, 503, 504}
    return False


class RetryCounter:
    """Increment via on_retry callback so the fetcher can surface throttle activity in SSE."""

    def __init__(self) -> None:
        self.count = 0

    def bump(self, _retry_state) -> None:
        self.count += 1


class PrismaClient:
    def __init__(
        self,
        http: httpx.AsyncClient,
        console_url: str,
        token: str | None = None,
        max_retries: int = 5,
    ) -> None:
        self.http = http
        self.console_url = console_url.rstrip("/")
        self.token = token
        self.max_retries = max_retries

    def set_token(self, token: str) -> None:
        self.token = token

    def _headers(self, *, with_target_env: bool = True) -> dict[str, str]:
        h = {"Accept": "application/json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        if with_target_env:
            h[TARGET_ENV_HEADER] = TARGET_ENV_VALUE
        return h

    async def authenticate(self, key: str, secret: str) -> str:
        url = f"{self.console_url}{AUTH_PATH}"
        resp = await self.http.post(
            url,
            json={"username": key, "password": secret},
            headers={"Content-Type": "application/json"},
        )
        if resp.status_code == 401:
            raise PrismaAuthError("Invalid API key or secret")
        resp.raise_for_status()
        token = resp.json().get("token")
        if not token:
            raise PrismaAuthError("Authenticate response missing token")
        self.token = token
        return token

    async def _retrying(self, retry_counter: RetryCounter | None = None):
        return AsyncRetrying(
            stop=stop_after_attempt(self.max_retries),
            wait=wait_exponential_jitter(initial=1, max=16, jitter=0.2),
            retry=retry_if_exception(_is_retryable),
            before_sleep=retry_counter.bump if retry_counter else None,
            reraise=True,
        )

    async def list_audits(
        self, params: list[tuple[str, str]], retry_counter: RetryCounter | None = None
    ) -> list[dict]:
        url = f"{self.console_url}{AUDITS_PATH}"
        retrying = await self._retrying(retry_counter)
        async for attempt in retrying:
            with attempt:
                resp = await self.http.get(url, params=params, headers=self._headers())
                if resp.status_code == 429:
                    retry_after = resp.headers.get("Retry-After")
                    raise httpx.HTTPStatusError(
                        f"429 retry-after={retry_after}",
                        request=resp.request,
                        response=resp,
                    )
                resp.raise_for_status()
                data = resp.json()
                return data if isinstance(data, list) else []
        return []

    async def stream_audits_csv(
        self, params: list[tuple[str, str]]
    ) -> AsyncIterator[bytes]:
        url = f"{self.console_url}{AUDITS_DOWNLOAD_PATH}"
        async with self.http.stream("GET", url, params=params, headers=self._headers()) as resp:
            resp.raise_for_status()
            async for chunk in resp.aiter_bytes():
                yield chunk
