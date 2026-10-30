"""Amazon Keyspaces - wide column: activity events per Visitor, newest first, with TTL."""
import ssl
import time
import uuid
from datetime import datetime, timedelta, timezone

import boto3
from cassandra import ConsistencyLevel
from cassandra.cluster import EXEC_PROFILE_DEFAULT, Cluster, ExecutionProfile
from cassandra.concurrent import execute_concurrent_with_args
from cassandra.policies import DCAwareRoundRobinPolicy
from cassandra.query import SimpleStatement
from cassandra_sigv4.auth import SigV4AuthProvider
from flask import jsonify, request

from .. import catalog, simlimit, trace
from ..base import env, region
from ..visitor import persona_id, visitor_id
from . import PRICE_WRITE_RU, table as result_table, usd

META = catalog.META["keyspaces"]
PAGES = catalog.PAGES["keyspaces"]
LEVELS = {"LOCAL_ONE": ConsistencyLevel.LOCAL_ONE, "LOCAL_QUORUM": ConsistencyLevel.LOCAL_QUORUM}

_session = None


def s():
    global _session
    if _session is None:
        host = f"cassandra.{region()}.amazonaws.com"
        profile = ExecutionProfile(consistency_level=ConsistencyLevel.LOCAL_QUORUM,
                                   load_balancing_policy=DCAwareRoundRobinPolicy(local_dc=region()))
        # the driver connects to endpoint ENI IPs from system.peers, so TLS checks the service host name
        cluster = Cluster([host], port=9142, ssl_context=ssl.create_default_context(), ssl_options={"server_hostname": host},
                          auth_provider=SigV4AuthProvider(boto3.Session(region_name=region())),
                          execution_profiles={EXEC_PROFILE_DEFAULT: profile}, protocol_version=4)
        _session = cluster.connect()
    return _session


def table():
    return f"{env('KEYSPACE')}.{env('TABLE_NAME')}"


def write_all(stmt, args, concurrency=32, attempts=6):
    """Concurrent writes; timed-out or throttled rows are retried with backoff."""
    pending, retried = list(args), 0
    for attempt in range(attempts):
        results = execute_concurrent_with_args(s(), stmt, pending, concurrency=concurrency, raise_on_first_error=False)
        failed = [a for a, (ok, _) in zip(pending, results) if not ok]
        if not failed:
            return len(args), retried
        retried += len(failed)
        pending = failed
        time.sleep(min(2 ** attempt, 10))
    raise RuntimeError(f"{len(pending)} writes still fail after {attempts} attempts")


def register(bp):
    @bp.post("/api/events")
    def api_event():
        body = request.get_json(force=True)
        cql = f"INSERT INTO {table()} (user_id, event_time, event_id, event_type, product_id, detail) VALUES (?, ?, ?, ?, ?, ?)"
        with trace.call("INSERT", cql, {"user_id": visitor_id(), "event_type": body.get("type")}) as t:
            s().execute(s().prepare(cql), (visitor_id(), datetime.now(timezone.utc), uuid.uuid4(), body.get("type", "view"),
                                           body.get("product_id", ""), body.get("detail", "")[:200]))
            t.result(items=1, capacity="1 WRU", cost=usd(PRICE_WRITE_RU),
                     note="Writes go to one partition (your id) and are always LOCAL_QUORUM. The row expires after 7 days (table TTL).")
        return jsonify(trace.payload({"stored": True}))

    @bp.get("/api/activity")
    def api_activity():
        who = request.args.get("who", "visitor")
        level = request.args.get("consistency", "LOCAL_QUORUM")
        limit = min(int(request.args.get("limit", 20)), 50)
        uid = persona_id() if who == "persona" else visitor_id()
        cql = f"SELECT event_time, event_type, product_id, detail FROM {table()} WHERE user_id = %s LIMIT {limit}"
        with trace.call("SELECT", cql.replace("%s", f"'{uid}'"), {"consistency": level}) as t:
            rows = list(s().execute(SimpleStatement(cql, consistency_level=LEVELS.get(level, ConsistencyLevel.LOCAL_QUORUM)), (uid,)))
            t.result(items=len(rows), note=("LOCAL_ONE reads one replica: half the read cost, but a write from the last moment can be missing."
                                            if level == "LOCAL_ONE" else
                                            "LOCAL_QUORUM reads 2 of 3 replicas, so you always see your own last write.")
                     + " Rows come back newest first because the table stores them in that order.")
        return jsonify(trace.payload([{"event_time": r.event_time.isoformat(), "type": r.event_type, "product_id": r.product_id,
                                       "detail": r.detail} for r in rows]))

    @bp.get("/api/recent")
    def api_recent():
        cql = f"SELECT product_id, detail, event_type FROM {table()} WHERE user_id = %s LIMIT 40"
        with trace.call("SELECT", cql.replace("%s", f"'{visitor_id()}'"), {}) as t:
            rows = list(s().execute(cql, (visitor_id(),)))
            seen, recent = set(), []
            for r in rows:
                if r.event_type == "view" and r.product_id not in seen:
                    seen.add(r.product_id)
                    recent.append({"product_id": r.product_id, "detail": r.detail})
            t.result(items=len(recent), read=len(rows), note="The partition holds your history in time order, so 'recently viewed' is one read.")
        return jsonify(trace.payload(recent[:8]))

    @bp.post("/api/simulate")
    def api_simulate():
        body = request.get_json(silent=True) or {}
        with simlimit.run(visitor_id(), body.get("requests", 1000)) as n:
            cql = f"INSERT INTO {table()} (user_id, event_time, event_id, event_type, product_id, detail) VALUES (?, ?, ?, ?, ?, ?) USING TTL 600"
            stmt = s().prepare(cql)
            now = datetime.now(timezone.utc)
            args = [(f"SIM-{i % 500}", now, uuid.uuid4(), "view", f"P{i % 200 + 1:04d}", "simulated") for i in range(n)]
            started = time.perf_counter()
            with trace.call("INSERT × N", cql + f"\n# {n} rows, 500 synthetic shoppers, 32 in flight", {"requests": n}) as t:
                written, retried = write_all(stmt, args)
                elapsed = time.perf_counter() - started
                t.result(items=written, capacity=f"{written + retried} WRU", cost=usd((written + retried) * PRICE_WRITE_RU),
                         note=f"{retried} writes were retried with backoff. A new on-demand table increases its capacity step by step; "
                              "the synthetic rows expire after 10 minutes.")
        return jsonify(trace.payload({"requests": n, "retried": retried, "seconds": round(elapsed, 2), "per_second": round(n / elapsed)}))


def seed(ds):
    users = sorted({c["customer_id"] for c in ds.customers})
    with trace.call("DELETE + INSERT", f"DELETE FROM {table()} WHERE user_id = ?; INSERT INTO {table()} ...", {}) as t:
        write_all(s().prepare(f"DELETE FROM {table()} WHERE user_id = ?"), [(u,) for u in users])
        stmt = s().prepare(f"INSERT INTO {table()} (user_id, event_time, event_id, event_type, product_id, detail) VALUES (?, ?, ?, ?, ?, ?)")
        written, retried = write_all(stmt, [(e["user_id"], e["event_time"], e["event_id"], e["event_type"], e["product_id"], e["detail"])
                                            for e in ds.events])
        t.result(items=written)
    return [f"Cleared {len(users)} customer partitions (Keyspaces has no TRUNCATE).", f"Wrote {written} events ({retried} retried)."]


def reset_visitors():
    return ["Visitor events expire after 7 days by the table TTL. Keyspaces cannot list partitions cheaply, so no delete runs."]


def status():
    return {"keyspace": env("KEYSPACE"), "table": env("TABLE_NAME")}


def learn_overview(lesson, focus):
    """101: partitions (one per user_id) as shelves, rows (event_time DESC) as tiles. Your partition comes first."""
    mine = visitor_id()
    with trace.call("SELECT", f"SELECT user_id, event_time, event_id, event_type FROM {table()} LIMIT 1500", {}) as t:
        rows = list(s().execute(f"SELECT user_id, event_time, event_id, event_type FROM {table()} LIMIT 1500"))
        t.result(items=len(rows))
    with trace.call("SELECT", f"SELECT user_id, event_time, event_id, event_type FROM {table()} WHERE user_id = '{mine}' LIMIT 60", {}) as t:
        own = list(s().execute(f"SELECT user_id, event_time, event_id, event_type FROM {table()} WHERE user_id = %s LIMIT 60", (mine,)))
        t.result(items=len(own))
    parts = {}
    for row in rows:
        parts.setdefault(row.user_id, []).append(row)
    parts[mine] = own
    order = sorted(parts, key=lambda u: (u != mine, u))[:20]
    rid = lambda row: f"{row.user_id}|{row.event_time.isoformat()}|{row.event_id}"
    short = lambda u: u if len(u) <= 18 else u[:16] + "…"
    groups = [{"label": "Your history" if u == mine else short(u),
               "items": [{"id": rid(x), "title": f"{x.event_time:%Y-%m-%d %H:%M:%S}  {x.event_type}", "hit": u == mine}
                         for x in sorted(parts[u], key=lambda x: x.event_time, reverse=True)[:40]]} for u in order]
    return {"title": f"Keyspaces: the {table()} table", "text": "Each shelf is one partition (one user), and each square is one event, the newest at the left. The first 20 partitions are shown.",
            "facts": [[len(rows), "rows in the sample"], [len(parts), "partitions in the sample"], [len(own), "events in your partition"], ["7 days", "TTL"]],
            "groups": groups, "hit_label": "Your partition (user_id = your id)"}


def learn_item(lesson, item_id):
    uid, ts, eid = item_id.split("|")
    cql = f"SELECT * FROM {table()} WHERE user_id = %s AND event_time = %s AND event_id = %s"
    with trace.call("SELECT", cql.replace("%s", "?"), {}) as t:
        row = s().execute(cql, (uid, datetime.fromisoformat(ts), uuid.UUID(eid))).one()
        t.result(items=1 if row else 0)
    if not row:
        return {"title": eid, "sub": "This row does not exist any more (TTL may have deleted it).", "record": {}}
    rec = {k: (v.isoformat() if hasattr(v, "isoformat") else str(v) if isinstance(v, uuid.UUID) else v) for k, v in row._asdict().items()}
    order = ["user_id", "event_time", "event_id"] + [k for k in rec if k not in ("user_id", "event_time", "event_id")]
    return {"title": f"{rec.get('event_type')} event", "sub": "One row. user_id is the partition key. event_time and event_id are the clustering key (the order inside the partition).",
            "record": {k: rec[k] for k in order}, "marks": {"user_id": "kept", "event_time": "kept", "event_id": "kept"}}


# ---------------------------------------------------------------- E2E tutorial queries (templates/e2e/keyspaces.html)
def _cql(op, cql, params=(), level="LOCAL_QUORUM", note=None, limit_rows=50):
    """Run one read-only CQL statement. A refused statement comes back as a one-row table with the message."""
    shown = cql
    for p in params:
        shown = shown.replace("%s", f"'{p}'" if isinstance(p, str) else str(p), 1)
    try:
        with trace.call(op, shown, {"consistency": level}) as t:
            rs = s().execute(SimpleStatement(cql, consistency_level=LEVELS.get(level, ConsistencyLevel.LOCAL_QUORUM), fetch_size=500), params)
            rows = list(rs)
            t.result(items=len(rows))
    except Exception as e:                       # the lesson shows the refusal of Keyspaces
        return result_table(["Keyspaces answered with an error"], [[f"{type(e).__name__}: {e}"[:600]]], note=note)
    if not rows:
        return result_table(["result"], [["No rows."]], note=note)
    cols = list(rows[0]._fields)
    return result_table(cols, [list(r) for r in rows[:limit_rows]], note=note, total=len(rows))


def _e2e_size():
    out = _cql("SELECT (full partition)", f"SELECT event_time FROM {table()} WHERE user_id = %s", ("C00005",))
    n = out.get("total", 0)
    return result_table(["partition (user_id)", "rows in the partition"], [["C00005", n]],
                        note="Keyspaces has no aggregate functions such as count(). The Engine App counted the rows that the read returned.")


E2E = {
    "K1": lambda: _cql("SELECT (one partition)", f"SELECT user_id, event_time, event_type, product_id, detail FROM {table()} WHERE user_id = %s LIMIT 10",
                       ("C00005",), note="Newest first: the table stores the rows of a partition in event_time DESC order."),
    "K2": lambda: _cql("SELECT (clustering range)", f"SELECT event_time, event_type, product_id FROM {table()} WHERE user_id = %s AND event_time > %s",
                       ("C00005", datetime.now(timezone.utc).replace(microsecond=0) - timedelta(days=1)),
                       note="A range on the clustering column event_time inside one partition."),
    "K3": _e2e_size,
    "K4": lambda: _cql("SELECT (no partition key)", f"SELECT user_id, event_type FROM {table()} WHERE event_type = 'purchase' LIMIT 5"),
    "K5": lambda: _cql("SELECT (LOCAL_ONE)", f"SELECT user_id, event_time, event_type, product_id FROM {table()} WHERE user_id = %s LIMIT 10",
                       ("C00005",), level="LOCAL_ONE", note="LOCAL_ONE: one replica answers. The read costs half of a LOCAL_QUORUM read."),
    "K6": lambda: _cql("SELECT (schema)", "SELECT column_name, kind, position, clustering_order, type FROM system_schema.columns "
                       "WHERE keyspace_name = %s AND table_name = %s", (env("KEYSPACE"), env("TABLE_NAME"))),
    "K7": lambda: _cql("SELECT (table settings)", "SELECT default_time_to_live, custom_properties FROM system_schema_mcs.tables "
                       "WHERE keyspace_name = %s AND table_name = %s", (env("KEYSPACE"), env("TABLE_NAME"))),
}
