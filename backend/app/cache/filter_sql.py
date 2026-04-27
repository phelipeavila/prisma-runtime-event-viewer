"""Translate the new atom-based Filters payload into a parameterized DuckDB
WHERE/ORDER BY/LIMIT clause.

The wire format produced by the frontend is:

    {
      "atoms": [{"field": "namespace", "op": "is_one_of", "value": ["default"]}],
      "from":  "2026-01-01T00:00:00Z",  # optional
      "to":    "2026-01-02T00:00:00Z",  # optional
      "sort":  "time",
      "reverse": true,
      "page": 0,
      "page_size": 100
    }

Every value goes through `?` parameter binding — we never f-string user input.
Column names and operators are validated against whitelists; the sort column is
also whitelisted.
"""

from typing import Any, Iterable

# ---------------------------------------------------------------------------
# Column type catalog. The data type drives which operators are valid.
# ---------------------------------------------------------------------------
COLUMN_TYPES: dict[str, str] = {
    # datetime
    "time": "datetime",
    # ids / strings
    "_id": "string",
    "hostname": "string",
    "fqdn": "string",
    "region": "string",
    "account_id": "string",
    "provider": "string",
    "resource_id": "string",
    "vm_id": "string",
    "cluster": "string",
    "namespace": "string",
    "version": "string",
    "container_id": "string",
    "container_name": "string",
    "image_name": "string",
    "image_id": "string",
    "profile_id": "string",
    "label": "string",
    "labels_json": "string",
    "type": "string",
    "attack_type": "string",
    "effect": "string",
    "severity": "string",
    "rule_name": "string",
    "msg": "string",
    "err": "string",
    "user_name": "string",
    "process_path": "string",
    "command": "string",
    "filepath": "string",
    "md5": "string",
    "ip": "string",
    "country": "string",
    "domain": "string",
    "app": "string",
    "app_id": "string",
    "function_name": "string",
    "function_id": "string",
    "request_id": "string",
    "runtime": "string",
    "os": "string",
    "wildfire_url": "string",
    # arrays
    "attack_techniques": "array",
    "collections": "array",
    # numbers
    "pid": "number",
    "port": "number",
    "count": "number",
    # booleans
    "is_container": "bool",
    "interactive": "bool",
}

OPS_BY_TYPE: dict[str, set[str]] = {
    "string": {
        "is_one_of", "is_not_one_of",
        "equals", "not_equals",
        "contains", "not_contains",
        "starts_with", "ends_with",
        "is_empty", "is_not_empty",
    },
    "datetime": {"is_empty", "is_not_empty"},
    "array": {
        "contains_any", "contains_all", "not_contains_any",
        "is_empty", "is_not_empty",
    },
    "number": {
        "eq", "neq", "lt", "lte", "gt", "gte", "between",
        "is_empty", "is_not_empty",
    },
    "bool": {"is_true", "is_false"},
}

# Columns the user can sort by. Mirrors the visible columns in the frontend.
SORT_WHITELIST: dict[str, str] = {col: col for col in [
    "_id",
    "time",
    "hostname", "fqdn", "region", "account_id", "provider",
    "resource_id", "vm_id", "cluster", "namespace", "version",
    "is_container", "container_id", "container_name",
    "image_name", "image_id", "profile_id", "label",
    "type", "attack_type", "effect", "severity", "count", "rule_name",
    "msg", "err", "interactive", "user_name",
    "pid", "process_path", "command",
    "filepath", "md5",
    "ip", "port", "country", "domain",
    "app", "app_id",
    "function_name", "function_id", "request_id",
    "runtime", "os", "wildfire_url",
]}

MAX_MULTI_VALUES = 200


class FilterValidationError(ValueError):
    pass


def _coerce_number(value: Any, label: str) -> float | int:
    if isinstance(value, bool):
        raise FilterValidationError(f"{label} expects a number")
    if isinstance(value, (int, float)):
        return value
    try:
        if isinstance(value, str) and "." in value:
            return float(value)
        return int(value)
    except (TypeError, ValueError) as exc:
        raise FilterValidationError(f"{label} expects a number, got {value!r}") from exc


def _as_list(value: Any, label: str) -> list:
    if value is None:
        raise FilterValidationError(f"{label} requires a value")
    if isinstance(value, (list, tuple)):
        items = list(value)
    else:
        items = [value]
    if len(items) == 0:
        raise FilterValidationError(f"{label} requires at least one value")
    if len(items) > MAX_MULTI_VALUES:
        raise FilterValidationError(
            f"{label} has {len(items)} values; max is {MAX_MULTI_VALUES}"
        )
    return items


def _as_str(value: Any, label: str) -> str:
    if value is None or value == "":
        raise FilterValidationError(f"{label} requires a value")
    return str(value)


def _emit_clause(field: str, type_: str, op: str, value: Any) -> tuple[str, list]:
    """Return (clause, params) for a single atom. Caller has already validated
    that `field` is in COLUMN_TYPES and `op` is allowed for `type_`."""
    label = f"Filter '{field}' ({op})"

    # No-value operators
    if op == "is_empty":
        if type_ == "array":
            return f"({field} IS NULL OR len({field}) = 0)", []
        if type_ == "string":
            return f"({field} IS NULL OR CAST({field} AS VARCHAR) = '')", []
        return f"{field} IS NULL", []
    if op == "is_not_empty":
        if type_ == "array":
            return f"({field} IS NOT NULL AND len({field}) > 0)", []
        if type_ == "string":
            return f"({field} IS NOT NULL AND CAST({field} AS VARCHAR) <> '')", []
        return f"{field} IS NOT NULL", []
    if op == "is_true":
        return f"{field} = ?", [True]
    if op == "is_false":
        return f"{field} = ?", [False]

    # String / datetime operators
    if type_ == "string":
        if op == "is_one_of":
            vals = _as_list(value, label)
            ph = ",".join(["?"] * len(vals))
            return f"{field} IN ({ph})", list(vals)
        if op == "is_not_one_of":
            vals = _as_list(value, label)
            ph = ",".join(["?"] * len(vals))
            return f"{field} NOT IN ({ph})", list(vals)
        if op == "equals":
            return f"{field} = ?", [_as_str(value, label)]
        if op == "not_equals":
            return f"{field} <> ?", [_as_str(value, label)]
        if op == "contains":
            return f"CAST({field} AS VARCHAR) ILIKE ?", [f"%{_as_str(value, label)}%"]
        if op == "not_contains":
            return f"CAST({field} AS VARCHAR) NOT ILIKE ?", [f"%{_as_str(value, label)}%"]
        if op == "starts_with":
            return f"CAST({field} AS VARCHAR) ILIKE ?", [f"{_as_str(value, label)}%"]
        if op == "ends_with":
            return f"CAST({field} AS VARCHAR) ILIKE ?", [f"%{_as_str(value, label)}"]

    # Array operators
    if type_ == "array":
        if op == "contains_any":
            vals = _as_list(value, label)
            ph = ",".join(["?"] * len(vals))
            return f"list_has_any({field}, [{ph}])", list(vals)
        if op == "contains_all":
            vals = _as_list(value, label)
            ph = ",".join(["?"] * len(vals))
            return f"list_has_all({field}, [{ph}])", list(vals)
        if op == "not_contains_any":
            vals = _as_list(value, label)
            ph = ",".join(["?"] * len(vals))
            return f"NOT list_has_any({field}, [{ph}])", list(vals)

    # Number operators
    if type_ == "number":
        if op == "between":
            if not isinstance(value, dict):
                raise FilterValidationError(f"{label} requires {{min, max}}")
            lo = value.get("min")
            hi = value.get("max")
            if lo is None and hi is None:
                raise FilterValidationError(f"{label} requires at least min or max")
            clauses = []
            params: list = []
            if lo is not None:
                clauses.append(f"{field} >= ?")
                params.append(_coerce_number(lo, f"{label}.min"))
            if hi is not None:
                clauses.append(f"{field} <= ?")
                params.append(_coerce_number(hi, f"{label}.max"))
            return "(" + " AND ".join(clauses) + ")", params
        op_map = {"eq": "=", "neq": "<>", "lt": "<", "lte": "<=", "gt": ">", "gte": ">="}
        if op in op_map:
            return f"{field} {op_map[op]} ?", [_coerce_number(value, label)]

    raise FilterValidationError(f"Unsupported operator {op!r} for column {field!r}")


def _normalize_atom(atom: Any) -> tuple[str, str, str, Any]:
    if not isinstance(atom, dict):
        raise FilterValidationError(f"Atom must be an object, got {type(atom).__name__}")
    field = atom.get("field")
    op = atom.get("op")
    if not isinstance(field, str) or not field:
        raise FilterValidationError("Atom missing 'field'")
    if not isinstance(op, str) or not op:
        raise FilterValidationError(f"Atom for {field!r} missing 'op'")
    type_ = COLUMN_TYPES.get(field)
    if type_ is None:
        raise FilterValidationError(f"Unknown filter column: {field}")
    if op not in OPS_BY_TYPE[type_]:
        raise FilterValidationError(
            f"Operator '{op}' is not valid for {field!r} (type {type_})"
        )
    return field, type_, op, atom.get("value")


def build_where(filters: dict[str, Any]) -> tuple[str, list]:
    """Build the WHERE clause from the atom list plus optional time bounds."""
    clauses: list[str] = []
    params: list = []

    f_from = filters.get("from_") or filters.get("from")
    if f_from:
        clauses.append("time >= ?")
        params.append(f_from)
    f_to = filters.get("to")
    if f_to:
        clauses.append("time <= ?")
        params.append(f_to)

    atoms: Iterable = filters.get("atoms") or []
    if not isinstance(atoms, (list, tuple)):
        raise FilterValidationError("'atoms' must be a list")
    for atom in atoms:
        field, type_, op, value = _normalize_atom(atom)
        clause, p = _emit_clause(field, type_, op, value)
        clauses.append(clause)
        params.extend(p)

    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    return where, params


def build_order(filters: dict[str, Any]) -> str:
    sort_key = filters.get("sort") or "time"
    column = SORT_WHITELIST.get(sort_key)
    if column is None:
        raise FilterValidationError(f"Invalid sort column: {sort_key}")
    direction = "DESC" if filters.get("reverse", True) else "ASC"
    return f" ORDER BY {column} {direction}"


def build_query(filters: dict[str, Any]) -> tuple[str, list]:
    where, params = build_where(filters)
    order = build_order(filters)
    page = max(int(filters.get("page", 0)), 0)
    page_size = min(max(int(filters.get("page_size", 100)), 1), 1000)
    sql = f"SELECT * FROM events{where}{order} LIMIT ? OFFSET ?"
    return sql, params + [page_size, page * page_size]


def build_count_query(filters: dict[str, Any]) -> tuple[str, list]:
    where, params = build_where(filters)
    return f"SELECT COUNT(*) FROM events{where}", params
