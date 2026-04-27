import json


def _row(i: int) -> dict:
    return {
        "_id": f"id-{i}",
        "time": "2026-01-01T00:00:00Z",
        "hostname": f"host{i % 3}",
        "type": "processes" if i % 2 == 0 else "network",
        "effect": "alert" if i % 3 else "block",
        "severity": ["low", "medium", "high"][i % 3],
        "imageName": "registry/app:1.0",
        "namespace": "default",
        "cluster": "prod-east",
        "ruleName": "rule-1",
        "msg": f"event {i}",
    }


def test_insert_and_count(store):
    store.insert_many([_row(i) for i in range(100)])
    assert store.count() == 100


def test_insert_replace_dedupes(store):
    store.insert_many([_row(0), _row(0)])
    assert store.count() == 1


def test_query_returns_paginated(store):
    store.insert_many([_row(i) for i in range(150)])
    rows, total = store.query({"page": 0, "page_size": 50})
    assert len(rows) == 50
    assert total == 150


def test_query_with_filter(store):
    store.insert_many([_row(i) for i in range(60)])
    rows, total = store.query(
        {
            "atoms": [{"field": "type", "op": "is_one_of", "value": ["processes"]}],
            "page_size": 1000,
        }
    )
    # i % 2 == 0 → 30 rows
    assert total == 30
    assert all(r["type"] == "processes" for r in rows)


def test_facets(store):
    store.insert_many([_row(i) for i in range(30)])
    facet = store.facet("type")
    assert facet["distinct"] == 2
    assert sorted(v["value"] for v in facet["values"]) == ["network", "processes"]


def test_time_bounds(store):
    store.insert_many([
        {"_id": "a", "time": "2026-01-01T00:00:00Z"},
        {"_id": "b", "time": "2026-01-05T00:00:00Z"},
    ])
    lo, hi = store.time_bounds()
    assert lo is not None and hi is not None
    assert lo < hi
