from datetime import datetime, timedelta, timezone

from app.util.time_chunks import split_time_range


def test_split_into_n_intervals_covers_range():
    a = datetime(2026, 1, 1, tzinfo=timezone.utc)
    b = a + timedelta(hours=24)
    chunks = split_time_range(a.isoformat(), b.isoformat(), 4)
    assert len(chunks) == 4
    assert datetime.fromisoformat(chunks[0][0]) == a
    assert datetime.fromisoformat(chunks[-1][1]) == b


def test_intervals_are_contiguous():
    a = datetime(2026, 1, 1, tzinfo=timezone.utc)
    b = a + timedelta(hours=12)
    chunks = split_time_range(a, b, 6)
    for i in range(len(chunks) - 1):
        assert chunks[i][1] == chunks[i + 1][0]
