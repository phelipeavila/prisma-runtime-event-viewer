import csv
import io
import json
import logging
from typing import Any, AsyncIterator, Iterable

import duckdb
from dateutil import parser as date_parser

from app.cache.filter_sql import build_count_query, build_order, build_query, build_where
from app.config import Settings

logger = logging.getLogger("runtime_event_viewer.duckdb")


# Order matters — must match the DDL column order so executemany can use positional binds.
COLUMNS: list[str] = [
    "_id",
    "time",
    "hostname",
    "fqdn",
    "region",
    "account_id",
    "provider",
    "resource_id",
    "vm_id",
    "cluster",
    "namespace",
    "collections",
    "version",
    "is_container",
    "container_id",
    "container_name",
    "image_name",
    "image_id",
    "profile_id",
    "label",
    "labels_json",
    "type",
    "attack_type",
    "attack_techniques",
    "effect",
    "severity",
    "count",
    "rule_name",
    "msg",
    "err",
    "interactive",
    "user_name",
    "pid",
    "process_path",
    "command",
    "filepath",
    "md5",
    "ip",
    "port",
    "country",
    "domain",
    "app",
    "app_id",
    "function_name",
    "function_id",
    "request_id",
    "runtime",
    "os",
    "wildfire_url",
    "raw",
]


# Map raw Prisma JSON keys to our column names.
def _normalize(row: dict, keep_raw: bool) -> tuple:
    def s(*keys) -> str | None:
        for k in keys:
            v = row.get(k)
            if v is not None and v != "":
                return str(v)
        return None

    def i(*keys) -> int | None:
        for k in keys:
            v = row.get(k)
            if v is None or v == "":
                continue
            try:
                return int(v)
            except (TypeError, ValueError):
                continue
        return None

    def b(*keys) -> bool | None:
        for k in keys:
            v = row.get(k)
            if v is None:
                continue
            if isinstance(v, bool):
                return v
            if isinstance(v, str):
                return v.lower() in ("true", "1", "yes")
        return None

    def lst(*keys) -> list[str]:
        for k in keys:
            v = row.get(k)
            if isinstance(v, list):
                return [str(x) for x in v if x is not None]
        return []

    def t(*keys) -> Any:
        for k in keys:
            v = row.get(k)
            if v:
                try:
                    return date_parser.isoparse(v) if isinstance(v, str) else v
                except (ValueError, TypeError):
                    continue
        return None

    process = row.get("process") or {}
    file = row.get("file") or {}
    network = row.get("networkActivity") or row.get("network") or {}
    if isinstance(network, list):
        network = network[0] if network else {}
    labels = row.get("labels")

    return (
        s("_id", "id"),
        t("time"),
        s("hostname"),
        s("fqdn"),
        s("region"),
        s("accountID", "account_id"),
        s("provider"),
        s("resourceID", "resource_id"),
        s("vmID", "vm_id"),
        s("cluster"),
        s("namespace"),
        lst("collections"),
        s("version"),
        b("isContainer", "is_container"),
        s("containerID", "container_id"),
        s("container", "containerName", "container_name"),
        s("imageName", "image_name"),
        s("imageID", "image_id"),
        s("profileID", "profile_id"),
        s("label"),
        json.dumps(labels) if labels is not None else None,
        s("type"),
        s("attackType", "attack_type"),
        lst("attackTechniques", "attack_techniques"),
        s("effect"),
        s("severity"),
        i("count"),
        s("ruleName", "rule_name"),
        s("msg"),
        s("err"),
        b("interactive"),
        s("user"),
        i("pid") if row.get("pid") is not None else (
            int(process["pid"]) if isinstance(process, dict) and process.get("pid") is not None else None
        ),
        s("processPath", "process_path") or (process.get("path") if isinstance(process, dict) else None),
        s("command") or (process.get("command") if isinstance(process, dict) else None),
        s("filepath") or (file.get("path") if isinstance(file, dict) else None),
        s("md5") or (file.get("md5") if isinstance(file, dict) else None),
        s("ip") or (network.get("ip") if isinstance(network, dict) else None),
        i("port") or (network.get("port") if isinstance(network, dict) else None),
        s("country") or (network.get("country") if isinstance(network, dict) else None),
        s("domain") or (network.get("domain") if isinstance(network, dict) else None),
        s("app"),
        s("appID", "app_id"),
        s("function", "function_name"),
        s("functionID", "function_id"),
        s("requestID", "request_id"),
        s("runtime"),
        s("os"),
        s("wildFireReportURL", "wildfire_url"),
        json.dumps(row, default=str) if keep_raw else None,
    )


class DuckDBStore:
    def __init__(self, db: duckdb.DuckDBPyConnection, settings: Settings) -> None:
        self.db = db
        self.settings = settings

    def init_schema(self) -> None:
        ddl = self.settings.schema_path.read_text(encoding="utf-8")
        self.db.execute(ddl)

    def truncate(self) -> None:
        self.db.execute("DELETE FROM events")

    def insert_many(self, rows: Iterable[dict]) -> int:
        tuples = [_normalize(r, self.settings.duckdb_keep_raw_json) for r in rows]
        if not tuples:
            return 0
        placeholders = ",".join(["?"] * len(COLUMNS))
        cols = ",".join(COLUMNS)
        self.db.executemany(
            f"INSERT OR REPLACE INTO events ({cols}) VALUES ({placeholders})",
            tuples,
        )
        return len(tuples)

    def count(self) -> int:
        return int(self.db.execute("SELECT COUNT(*) FROM events").fetchone()[0])

    def time_bounds(self) -> tuple[str | None, str | None]:
        row = self.db.execute("SELECT MIN(time), MAX(time) FROM events").fetchone()
        if not row or row[0] is None:
            return None, None
        lo, hi = row
        return (lo.isoformat() if lo else None, hi.isoformat() if hi else None)

    def query(self, filters: dict) -> tuple[list[dict], int]:
        sql, params = build_query(filters)
        rows = self.db.execute(sql, params).fetchall()
        names = [d[0] for d in self.db.description]
        result = [dict(zip(names, r)) for r in rows]

        cnt_sql, cnt_params = build_count_query(filters)
        total = int(self.db.execute(cnt_sql, cnt_params).fetchone()[0])
        return result, total

    def facet(self, field: str, limit: int = 200) -> dict:
        FACET_WHITELIST = {
            # severity / outcome
            "type", "effect", "severity", "attack_type", "rule_name",
            # k8s
            "namespace", "cluster",
            # container / image
            "image_name", "image_id", "container_name", "container_id",
            "profile_id", "label",
            # host
            "hostname", "fqdn", "os", "vm_id",
            # cloud
            "provider", "region", "account_id", "resource_id", "version",
            # process
            "user_name", "app", "app_id", "process_path",
            # network
            "ip", "country", "domain", "port",
            # serverless
            "function_name", "function_id", "request_id", "runtime",
        }
        if field not in FACET_WHITELIST:
            raise ValueError(f"Invalid facet field: {field}")
        sql = (
            f"SELECT {field} AS value, COUNT(*) AS c FROM events "
            f"WHERE {field} IS NOT NULL GROUP BY {field} ORDER BY c DESC LIMIT ?"
        )
        rows = self.db.execute(sql, [limit]).fetchall()
        distinct = int(
            self.db.execute(
                f"SELECT COUNT(DISTINCT {field}) FROM events WHERE {field} IS NOT NULL"
            ).fetchone()[0]
        )
        return {
            "field": field,
            "values": [{"value": r[0], "count": int(r[1])} for r in rows],
            "distinct": distinct,
        }

    async def stream_csv(self, filters: dict) -> AsyncIterator[bytes]:
        """Cursor-paginated CSV stream filtered by `filters`. Sorts by _id for stable cursor."""
        where, params = build_where(filters)
        # We append a cursor predicate; combine with existing WHERE.
        cursor = ""
        page_size = 5000

        # Header
        header_buf = io.StringIO()
        writer = csv.writer(header_buf)
        writer.writerow(COLUMNS)
        yield header_buf.getvalue().encode("utf-8")

        while True:
            cursor_clause = "_id > ?"
            if where:
                composite_where = f"{where} AND {cursor_clause}"
            else:
                composite_where = f" WHERE {cursor_clause}"
            sql = (
                f"SELECT * FROM events{composite_where} ORDER BY _id LIMIT ?"
            )
            rows = self.db.execute(sql, params + [cursor, page_size]).fetchall()
            if not rows:
                return
            buf = io.StringIO()
            w = csv.writer(buf)
            for r in rows:
                w.writerow(["" if v is None else v for v in r])
            yield buf.getvalue().encode("utf-8")
            cursor = rows[-1][0]
            if len(rows) < page_size:
                return
