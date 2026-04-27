"""Tiny in-process mock of the Prisma Cloud endpoints we depend on.

Generates a deterministic synthetic dataset and serves both the JSON and CSV
audit endpoints, plus the auth exchange. Used by tests via an httpx ASGI
transport — no real network."""

import csv
import io
import json
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse


SEED = 42
TYPES = ["processes", "network", "filesystem", "kubernetes"]
EFFECTS = ["alert", "block", "prevent", "disable"]
SEVERITIES = ["low", "medium", "high"]
NAMESPACES = ["default", "kube-system", "production", "staging", "ingress-nginx"]
CLUSTERS = ["prod-east", "prod-west", "staging"]
IMAGES = [f"registry.example.com/app/{n}:v1.{i}" for i, n in enumerate(["api", "worker", "ui", "db", "cache"])]
HOSTS = [f"node-{i:02d}.example.com" for i in range(20)]
RULES = [f"rule-{i}" for i in range(8)]


@dataclass
class MockEvent:
    _id: str
    time: datetime
    type: str
    effect: str
    severity: str
    namespace: str
    cluster: str
    image_name: str
    hostname: str
    rule_name: str
    msg: str
    raw: dict[str, Any] = field(default_factory=dict)


def _generate(n: int, base_time: datetime) -> list[MockEvent]:
    rng = random.Random(SEED)
    events: list[MockEvent] = []
    for i in range(n):
        t = base_time - timedelta(seconds=rng.randint(0, 60 * 60 * 24 * 7))
        ev = MockEvent(
            _id=f"id-{i:08d}",
            time=t,
            type=rng.choice(TYPES),
            effect=rng.choice(EFFECTS),
            severity=rng.choice(SEVERITIES),
            namespace=rng.choice(NAMESPACES),
            cluster=rng.choice(CLUSTERS),
            image_name=rng.choice(IMAGES),
            hostname=rng.choice(HOSTS),
            rule_name=rng.choice(RULES),
            msg=f"event {i} flagged",
        )
        ev.raw = {
            "_id": ev._id,
            "time": ev.time.isoformat(),
            "type": ev.type,
            "effect": ev.effect,
            "severity": ev.severity,
            "namespace": ev.namespace,
            "cluster": ev.cluster,
            "imageName": ev.image_name,
            "hostname": ev.hostname,
            "ruleName": ev.rule_name,
            "msg": ev.msg,
        }
        events.append(ev)
    events.sort(key=lambda e: e.time, reverse=True)
    return events


def _filter(events: Iterable[MockEvent], q) -> list[MockEvent]:
    out = list(events)
    f_from = q.get("from")
    f_to = q.get("to")
    if f_from:
        from_dt = datetime.fromisoformat(f_from.replace("Z", "+00:00"))
        out = [e for e in out if e.time >= from_dt]
    if f_to:
        to_dt = datetime.fromisoformat(f_to.replace("Z", "+00:00"))
        out = [e for e in out if e.time <= to_dt]
    for key, attr in [
        ("type", "type"), ("effect", "effect"), ("severity", "severity"),
        ("namespace", "namespace"), ("cluster", "cluster"),
        ("imageName", "image_name"), ("hostname", "hostname"),
        ("ruleName", "rule_name"),
    ]:
        vals = q.get_list(key) if hasattr(q, "get_list") else q.getlist(key)
        if vals:
            out = [e for e in out if getattr(e, attr) in vals]
    return out


def make_mock(n_events: int = 1000, inject_429_every: int = 0) -> tuple[FastAPI, list[MockEvent]]:
    app = FastAPI()
    base = datetime.now(timezone.utc)
    events = _generate(n_events, base)
    counter = {"calls": 0, "throttled": 0}

    @app.post("/api/v34.01/authenticate")
    async def authenticate(payload: dict):
        if not payload.get("username") or not payload.get("password"):
            raise HTTPException(401, "missing creds")
        # opaque "token"; clients accept this as bearer.
        return {"token": "mock.jwt.token"}

    @app.get("/api/v34.03/audits/runtime/container")
    async def list_audits(request: Request):
        counter["calls"] += 1
        if inject_429_every and counter["calls"] % inject_429_every == 0:
            counter["throttled"] += 1
            return JSONResponse({"detail": "rate limited"}, status_code=429,
                                headers={"Retry-After": "1"})
        q = request.query_params
        offset = int(q.get("offset", "0"))
        limit = min(int(q.get("limit", "100")), 100)
        filtered = _filter(events, q)
        page = filtered[offset:offset + limit]
        return [e.raw for e in page]

    @app.get("/api/v34.03/audits/runtime/container/download")
    async def download(request: Request):
        q = request.query_params
        filtered = _filter(events, q)

        async def gen():
            buf = io.StringIO()
            writer = csv.writer(buf)
            writer.writerow(["_id", "time", "type", "effect", "severity",
                             "namespace", "cluster", "imageName", "hostname",
                             "ruleName", "msg"])
            yield buf.getvalue().encode("utf-8")
            for e in filtered:
                buf = io.StringIO()
                csv.writer(buf).writerow([
                    e._id, e.time.isoformat(), e.type, e.effect, e.severity,
                    e.namespace, e.cluster, e.image_name, e.hostname, e.rule_name, e.msg,
                ])
                yield buf.getvalue().encode("utf-8")

        return StreamingResponse(gen(), media_type="text/csv")

    return app, events
