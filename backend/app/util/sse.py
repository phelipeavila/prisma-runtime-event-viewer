import asyncio
import json
from typing import AsyncIterator


def format_sse(event: str, data: dict | str) -> bytes:
    payload = data if isinstance(data, str) else json.dumps(data, default=str)
    lines = [f"event: {event}"]
    for line in payload.splitlines() or [""]:
        lines.append(f"data: {line}")
    lines.append("")
    lines.append("")
    return ("\n".join(lines)).encode("utf-8")


HEARTBEAT_INTERVAL_S = 15.0


async def heartbeat_stream(queue: asyncio.Queue) -> AsyncIterator[bytes]:
    """Yield items put on `queue` and emit a `: keepalive` comment every 15s of idle.

    A queued value of `None` signals end-of-stream.
    """
    while True:
        try:
            item = await asyncio.wait_for(queue.get(), timeout=HEARTBEAT_INTERVAL_S)
        except asyncio.TimeoutError:
            yield b": keepalive\n\n"
            continue
        if item is None:
            return
        yield item
