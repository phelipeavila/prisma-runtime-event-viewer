import pytest

from app.cache.filter_sql import (
    FilterValidationError,
    build_count_query,
    build_order,
    build_query,
    build_where,
)


def atom(field: str, op: str, value=None) -> dict:
    a = {"field": field, "op": op}
    if value is not None:
        a["value"] = value
    return a


# ---------------------------------------------------------------------------
# build_where: empty / time bounds
# ---------------------------------------------------------------------------
def test_build_where_empty():
    where, params = build_where({})
    assert where == ""
    assert params == []


def test_build_where_atoms_empty_list():
    where, params = build_where({"atoms": []})
    assert where == ""
    assert params == []


def test_build_where_time_range():
    where, params = build_where({"from": "2026-01-01T00:00:00Z", "to": "2026-01-02T00:00:00Z"})
    assert "time >= ?" in where
    assert "time <= ?" in where
    assert params == ["2026-01-01T00:00:00Z", "2026-01-02T00:00:00Z"]


# ---------------------------------------------------------------------------
# String operators
# ---------------------------------------------------------------------------
def test_string_is_one_of():
    where, params = build_where({"atoms": [atom("type", "is_one_of", ["processes", "network"])]})
    assert "type IN (?,?)" in where
    assert params == ["processes", "network"]


def test_string_is_not_one_of():
    where, params = build_where({"atoms": [atom("severity", "is_not_one_of", ["low"])]})
    assert "severity NOT IN (?)" in where
    assert params == ["low"]


def test_string_equals_and_not_equals():
    where, params = build_where({"atoms": [atom("namespace", "equals", "default")]})
    assert "namespace = ?" in where
    assert params == ["default"]
    where, params = build_where({"atoms": [atom("namespace", "not_equals", "kube-system")]})
    assert "namespace <> ?" in where
    assert params == ["kube-system"]


def test_string_contains_and_not_contains():
    where, params = build_where({"atoms": [atom("msg", "contains", "failure")]})
    assert "CAST(msg AS VARCHAR) ILIKE ?" in where
    assert params == ["%failure%"]
    where, params = build_where({"atoms": [atom("msg", "not_contains", "noise")]})
    assert "CAST(msg AS VARCHAR) NOT ILIKE ?" in where
    assert params == ["%noise%"]


def test_string_starts_and_ends_with():
    where, params = build_where({"atoms": [atom("hostname", "starts_with", "ip-")]})
    assert "ILIKE ?" in where
    assert params == ["ip-%"]
    where, params = build_where({"atoms": [atom("hostname", "ends_with", ".local")]})
    assert "ILIKE ?" in where
    assert params == ["%.local"]


def test_string_is_empty_and_not_empty():
    where, _ = build_where({"atoms": [atom("err", "is_empty")]})
    assert "err IS NULL" in where and "= ''" in where
    where, _ = build_where({"atoms": [atom("err", "is_not_empty")]})
    assert "err IS NOT NULL" in where and "<> ''" in where


# ---------------------------------------------------------------------------
# Bool operators
# ---------------------------------------------------------------------------
def test_bool_is_true_false():
    where, params = build_where({"atoms": [atom("interactive", "is_true")]})
    assert "interactive = ?" in where and params == [True]
    where, params = build_where({"atoms": [atom("is_container", "is_false")]})
    assert "is_container = ?" in where and params == [False]


# ---------------------------------------------------------------------------
# Array operators
# ---------------------------------------------------------------------------
def test_array_contains_any():
    where, params = build_where({"atoms": [atom("collections", "contains_any", ["red", "blue"])]})
    assert "list_has_any(collections, [?,?])" in where
    assert params == ["red", "blue"]


def test_array_contains_all():
    where, params = build_where({"atoms": [atom("collections", "contains_all", ["a", "b"])]})
    assert "list_has_all(collections, [?,?])" in where
    assert params == ["a", "b"]


def test_array_not_contains_any():
    where, params = build_where({"atoms": [atom("collections", "not_contains_any", ["x"])]})
    assert "NOT list_has_any(collections, [?])" in where
    assert params == ["x"]


def test_array_is_empty():
    where, _ = build_where({"atoms": [atom("collections", "is_empty")]})
    assert "len(collections) = 0" in where


# ---------------------------------------------------------------------------
# Number operators
# ---------------------------------------------------------------------------
def test_number_eq_neq_lt_lte_gt_gte():
    cases = [("eq", "="), ("neq", "<>"), ("lt", "<"), ("lte", "<="), ("gt", ">"), ("gte", ">=")]
    for op, sql_op in cases:
        where, params = build_where({"atoms": [atom("port", op, 443)]})
        assert f"port {sql_op} ?" in where
        assert params == [443]


def test_number_between():
    where, params = build_where(
        {"atoms": [atom("port", "between", {"min": 80, "max": 1024})]}
    )
    assert "port >= ?" in where and "port <= ?" in where
    assert params == [80, 1024]


def test_number_invalid_value():
    with pytest.raises(FilterValidationError):
        build_where({"atoms": [atom("port", "eq", "not-a-number")]})


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
def test_unknown_field_raises():
    with pytest.raises(FilterValidationError):
        build_where({"atoms": [atom("nope", "equals", "x")]})


def test_invalid_op_for_type_raises():
    with pytest.raises(FilterValidationError):
        build_where({"atoms": [atom("interactive", "contains", "x")]})


def test_caps_multi_at_200():
    with pytest.raises(FilterValidationError):
        build_where({"atoms": [atom("type", "is_one_of", ["x"] * 201)]})


def test_atoms_must_be_list():
    with pytest.raises(FilterValidationError):
        build_where({"atoms": "type=processes"})


# ---------------------------------------------------------------------------
# Order / pagination / count helpers
# ---------------------------------------------------------------------------
def test_build_order_default():
    assert "ORDER BY time DESC" in build_order({})


def test_build_order_invalid_sort():
    with pytest.raises(FilterValidationError):
        build_order({"sort": "_id; DROP TABLE events"})


def test_build_order_whitelisted():
    assert build_order({"sort": "severity", "reverse": False}) == " ORDER BY severity ASC"


def test_build_query_pagination():
    sql, params = build_query({"page": 2, "page_size": 50})
    assert sql.endswith("LIMIT ? OFFSET ?")
    assert params[-2:] == [50, 100]


def test_build_count_query():
    sql, params = build_count_query({"atoms": [atom("effect", "is_one_of", ["block"])]})
    assert sql.startswith("SELECT COUNT(*) FROM events")
    assert "effect IN (?)" in sql
    assert params == ["block"]


# ---------------------------------------------------------------------------
# End-to-end against DuckDB
# ---------------------------------------------------------------------------
def test_filter_executes_against_duckdb(store, db):
    rows = [
        {"_id": "a", "time": "2026-01-01T00:00:00Z", "type": "processes",
         "effect": "alert", "severity": "low"},
        {"_id": "b", "time": "2026-01-01T00:00:00Z", "type": "network",
         "effect": "block", "severity": "high"},
    ]
    store.insert_many(rows)
    sql, params = build_query(
        {"atoms": [atom("effect", "is_one_of", ["block"])], "page_size": 10}
    )
    found = db.execute(sql, params).fetchall()
    assert len(found) == 1
    assert found[0][0] == "b"


def test_executes_numeric_between_against_duckdb(store, db):
    rows = [
        {"_id": str(i), "time": "2026-01-01T00:00:00Z", "port": p}
        for i, p in enumerate([22, 80, 443, 8080])
    ]
    store.insert_many(rows)
    sql, params = build_query(
        {"atoms": [atom("port", "between", {"min": 80, "max": 443})], "page_size": 10}
    )
    found = db.execute(sql, params).fetchall()
    assert len(found) == 2  # 80 and 443


def test_executes_array_overlap_against_duckdb(store, db):
    rows = [
        {"_id": "a", "time": "2026-01-01T00:00:00Z", "collections": ["red"]},
        {"_id": "b", "time": "2026-01-01T00:00:00Z", "collections": ["blue", "green"]},
        {"_id": "c", "time": "2026-01-01T00:00:00Z", "collections": []},
    ]
    store.insert_many(rows)
    sql, params = build_query(
        {"atoms": [atom("collections", "contains_any", ["red", "blue"])], "page_size": 10}
    )
    found = db.execute(sql, params).fetchall()
    assert sorted(r[0] for r in found) == ["a", "b"]


def test_executes_string_not_contains_against_duckdb(store, db):
    rows = [
        {"_id": "a", "time": "2026-01-01T00:00:00Z", "msg": "boot ok"},
        {"_id": "b", "time": "2026-01-01T00:00:00Z", "msg": "kernel panic"},
        {"_id": "c", "time": "2026-01-01T00:00:00Z", "msg": "panic averted"},
    ]
    store.insert_many(rows)
    sql, params = build_query(
        {"atoms": [atom("msg", "not_contains", "panic")], "page_size": 10}
    )
    found = db.execute(sql, params).fetchall()
    assert sorted(r[0] for r in found) == ["a"]
