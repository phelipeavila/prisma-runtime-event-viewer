from datetime import datetime, timezone

from dateutil import parser as date_parser


def parse_iso(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        dt = value
    else:
        dt = date_parser.isoparse(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def split_time_range(
    from_ts: str | datetime,
    to_ts: str | datetime,
    chunks: int,
) -> list[tuple[str, str]]:
    """Split [from, to] into N half-open intervals [t0, t1), [t1, t2), ..., [t_{N-1}, to].

    Returned as ISO-8601 strings ready to send to Prisma. The final interval is closed
    on the right so no events at exactly `to` are dropped.
    """
    if chunks < 1:
        raise ValueError("chunks must be >= 1")

    start = parse_iso(from_ts)
    end = parse_iso(to_ts)
    if end <= start:
        raise ValueError("to must be after from")

    total = (end - start).total_seconds()
    step = total / chunks
    intervals: list[tuple[str, str]] = []
    for i in range(chunks):
        lo = start.timestamp() + step * i
        hi = start.timestamp() + step * (i + 1)
        lo_dt = datetime.fromtimestamp(lo, tz=timezone.utc)
        hi_dt = datetime.fromtimestamp(hi, tz=timezone.utc) if i < chunks - 1 else end
        intervals.append((lo_dt.isoformat(), hi_dt.isoformat()))
    return intervals
