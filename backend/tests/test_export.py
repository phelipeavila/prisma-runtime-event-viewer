import pytest


@pytest.mark.asyncio
async def test_cache_csv_streams(store):
    store.insert_many([
        {"_id": f"id-{i}", "time": "2026-01-01T00:00:00Z", "type": "processes",
         "effect": "alert", "severity": "low"}
        for i in range(20)
    ])
    chunks = []
    async for c in store.stream_csv({}):
        chunks.append(c)
    out = b"".join(chunks).decode("utf-8")
    assert out.startswith("_id,time")
    assert out.count("\n") >= 21  # header + 20 rows (csv.writer terminates with \r\n)


@pytest.mark.asyncio
async def test_cache_csv_filtered(store):
    store.insert_many([
        {"_id": f"id-{i}", "time": "2026-01-01T00:00:00Z",
         "type": "processes" if i % 2 == 0 else "network",
         "effect": "alert"}
        for i in range(10)
    ])
    chunks = []
    async for c in store.stream_csv(
        {"atoms": [{"field": "type", "op": "is_one_of", "value": ["network"]}]}
    ):
        chunks.append(c)
    out = b"".join(chunks).decode("utf-8")
    # Header + 5 rows
    assert "network" in out
    assert "processes" not in out
