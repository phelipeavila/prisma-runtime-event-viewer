"""Translate the new atom-based Filters payload to Prisma query parameters.

Used by the ingest fetcher and the native CSV export proxy. Prisma only
supports value-equality / "one of" semantics natively, so any operator outside
that subset is ignored when constructing the params (the result will still be
valid; it just won't carry the more advanced predicate over the wire). The
DuckDB cache later applies the full operator set when querying for the table.
"""

from typing import Any

# Backend column name -> Prisma camelCase param name.
COLUMN_TO_PRISMA: dict[str, str] = {
    "_id": "id",
    "profile_id": "profileID",
    "image_name": "imageName",
    "container_name": "container",
    "container_id": "containerID",
    "hostname": "hostname",
    "namespace": "namespace",
    "cluster": "cluster",
    "rule_name": "ruleName",
    "type": "type",
    "attack_type": "attackType",
    "attack_techniques": "attackTechniques",
    "effect": "effect",
    "user_name": "user",
    "os": "os",
    "msg": "msg",
    "interactive": "interactive",
    "app": "app",
    "app_id": "appID",
    "process_path": "processPath",
    "function_name": "function",
    "function_id": "functionID",
    "runtime": "runtime",
    "request_id": "requestID",
}


def _emit(prisma_key: str, value: Any) -> list[tuple[str, str]]:
    if value is None or value == "" or value == []:
        return []
    if isinstance(value, bool):
        return [(prisma_key, "true" if value else "false")]
    if isinstance(value, (list, tuple, set)):
        return [(prisma_key, str(v)) for v in value if v is not None and v != ""]
    return [(prisma_key, str(value))]


def filters_to_prisma_params(filters: dict[str, Any]) -> list[tuple[str, str]]:
    """Convert the atom-based Filters dict to a list of (key, value) tuples.

    `from_`/`to` are NOT included here — the ingest fetcher injects them per
    chunk. Multi-value atoms produce repeated keys (e.g. type=processes&type=network).
    Operators outside the equality/in subset are silently skipped.
    """
    out: list[tuple[str, str]] = []
    atoms = filters.get("atoms") or []
    if not isinstance(atoms, (list, tuple)):
        return out

    for atom in atoms:
        if not isinstance(atom, dict):
            continue
        field = atom.get("field")
        op = atom.get("op")
        prisma_key = COLUMN_TO_PRISMA.get(field) if isinstance(field, str) else None
        if not prisma_key or not isinstance(op, str):
            continue
        value = atom.get("value")
        if op in ("is_one_of", "equals"):
            out.extend(_emit(prisma_key, value))
        elif op == "is_true":
            out.append((prisma_key, "true"))
        elif op == "is_false":
            out.append((prisma_key, "false"))
        # Other operators (contains, starts_with, ranges, negations, etc.) are
        # not natively supported by Prisma, so we drop them; the cache layer
        # will still honor them when serving the table view.
    return out
