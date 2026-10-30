"""ElastiCache Serverless (Valkey) - in-memory: flash deal counter, session with TTL, live leaderboard."""
import random
import time
from concurrent.futures import ThreadPoolExecutor

from flask import jsonify, request
from redis.cluster import RedisCluster

from .. import catalog, simlimit, trace
from ..base import env, secret
from ..visitor import PERSONAS, persona_id, visitor_id
from . import table as result_table

META = catalog.META["elasticache"]
PAGES = catalog.PAGES["elasticache"]
DEAL_STOCK = 50

_client = None


def r():
    global _client
    if _client is None:
        s = secret(env("CACHE_SECRET_ARN"))
        _client = RedisCluster(host=env("CACHE_HOST"), port=int(env("CACHE_PORT", "6379")), ssl=True, username=s["username"],
                               password=s["password"], decode_responses=True, socket_timeout=10)
    return _client


def cmd(op, text, fn, note=None, **params):
    with trace.call(op, text, params) as t:
        out = fn()
        t.result(note=note)
    return out


def register(bp):
    @bp.get("/api/deal")
    def api_deal():
        deal = cmd("HGETALL", "HGETALL lm:deal", lambda: r().hgetall("lm:deal"))
        stock = cmd("GET", "GET lm:deal:stock", lambda: r().get("lm:deal:stock"),
                    note="Reads from memory take well under a millisecond inside the VPC.")
        return jsonify(trace.payload({**deal, "stock": int(stock or 0)}))

    @bp.post("/api/deal/buy")
    def api_buy():
        left = cmd("DECR", "DECR lm:deal:stock", lambda: r().decr("lm:deal:stock"),
                   note="DECR is atomic: Valkey runs one command at a time, so two buyers can never get the same piece.")
        won = left >= 0
        if not won:
            cmd("INCR", "INCR lm:deal:stock", lambda: r().incr("lm:deal:stock"), note="The counter went below 0, so we give the piece back.")
        return jsonify(trace.payload({"won": won, "stock": max(left, 0)}))

    @bp.post("/api/deal/simulate")
    def api_simulate():
        body = request.get_json(silent=True) or {}
        mode = body.get("mode", "atomic")
        stock = max(1, min(int(body.get("stock", 10)), 100))
        with simlimit.run(visitor_id(), body.get("buyers", 300)) as buyers:
            key = f"lm:sim:{visitor_id()}"
            r().set(key, stock, ex=600)
            latencies = []

            def atomic(_):
                t0 = time.perf_counter()
                won = r().decr(key) >= 0
                return won, (time.perf_counter() - t0) * 1000

            def naive(_):
                t0 = time.perf_counter()
                current = int(r().get(key))
                time.sleep(random.uniform(0.001, 0.004))   # application work between read and write
                won = current > 0
                if won:
                    r().set(key, current - 1, ex=600)
                return won, (time.perf_counter() - t0) * 1000

            text = (f"{buyers} buyers in parallel, stock = {stock}\n" +
                    ("DECR lm:sim  → won if the result >= 0" if mode == "atomic" else
                     "v = GET lm:sim ... if v > 0: SET lm:sim v-1  → read, then write"))
            started = time.perf_counter()
            with trace.call("Load Simulation", text, {"mode": mode, "buyers": buyers, "stock": stock}) as t:
                with ThreadPoolExecutor(max_workers=48) as pool:
                    results = list(pool.map(atomic if mode == "atomic" else naive, range(buyers)))
                winners = sum(1 for w, _ in results if w)
                latencies = sorted(ms for _, ms in results)
                oversold = max(0, winners - stock)
                t.result(items=buyers, note=("Atomic DECR: exactly the stock was sold." if oversold == 0 else
                                             f"Read-then-write: {oversold} pieces were sold that do not exist (a race condition)."))
            seconds = round(time.perf_counter() - started, 2)
            # A read-then-write run also runs the same rush with atomic DECR, inside the same reservation, so the
            # Guided panel can compare both without a second Load Simulation run.
            atomic_run = None
            if mode != "atomic":
                r().set(key, stock, ex=600)
                with ThreadPoolExecutor(max_workers=48) as pool:
                    res = list(pool.map(atomic, range(buyers)))
                lat = sorted(ms for _, ms in res)
                won = sum(1 for w, _ in res if w)
                atomic_run = {"winners": won, "oversold": max(0, won - stock),
                              "p50_ms": round(lat[len(lat) // 2], 2), "p95_ms": round(lat[int(len(lat) * 0.95)], 2)}
            r().delete(key)
        return jsonify(trace.payload({"mode": mode, "buyers": buyers, "stock": stock, "winners": winners, "oversold": oversold,
                                      "seconds": seconds,
                                      "p50_ms": round(latencies[len(latencies) // 2], 2),
                                      "p95_ms": round(latencies[int(len(latencies) * 0.95)], 2),
                                      "atomic": atomic_run}))

    @bp.post("/api/session")
    def api_session():
        body = request.get_json(silent=True) or {}
        ttl = max(10, min(int(body.get("ttl", 1800)), 86400))
        key = f"lm:session:{visitor_id()}"
        cmd("HSET", f"HSET {key} persona {persona_id()} last_page {body.get('page', '/')}",
            lambda: r().hset(key, mapping={"persona": persona_id(), "last_page": body.get("page", "/"), "seen_at": int(time.time())}))
        cmd("EXPIRE", f"EXPIRE {key} {ttl}", lambda: r().expire(key, ttl),
            note=f"Valkey deletes the session by itself after {ttl} seconds without activity. No clean-up job is necessary.")
        cmd("ZADD", f"ZADD lm:active {int(time.time())} {visitor_id()}", lambda: r().zadd("lm:active", {visitor_id(): int(time.time())}))
        return jsonify(trace.payload({"ttl": ttl}))

    @bp.get("/api/session")
    def api_session_get():
        key = f"lm:session:{visitor_id()}"
        data = cmd("HGETALL", f"HGETALL {key}", lambda: r().hgetall(key))
        ttl = cmd("TTL", f"TTL {key}", lambda: r().ttl(key))
        return jsonify(trace.payload({"session": data, "ttl": ttl}))

    @bp.post("/api/leaderboard/add")
    def api_lb_add():
        body = request.get_json(force=True)
        amount = float(body.get("amount", 0))
        cmd("ZINCRBY", f"ZINCRBY lm:leaderboard {amount} {persona_id()}", lambda: r().zincrby("lm:leaderboard", amount, persona_id()),
            note="The sorted set keeps members ordered by score at every write, so 'top 10' is always ready.")
        cmd("INCR", "INCR lm:orders:today", lambda: r().incr("lm:orders:today"))
        return jsonify(trace.payload({"added": amount}))

    @bp.get("/api/leaderboard")
    def api_lb():
        top = cmd("ZREVRANGE", "ZREVRANGE lm:leaderboard 0 9 WITHSCORES", lambda: r().zrevrange("lm:leaderboard", 0, 9, withscores=True))
        names = {p["id"]: p["name"] for p in PERSONAS}
        orders = cmd("GET", "GET lm:orders:today", lambda: r().get("lm:orders:today"))
        active = cmd("ZCOUNT", "ZCOUNT lm:active <now-300> +inf", lambda: r().zcount("lm:active", int(time.time()) - 300, "+inf"),
                     note="Visitors active in the last 5 minutes, counted from a sorted set of last-seen times.")
        rows = []
        for i, (member, score) in enumerate(top, start=1):
            name = names.get(member) or r().get(f"lm:name:{member}") or member
            rows.append({"rank": i, "customer": member, "name": name, "revenue": round(score, 2)})
        return jsonify(trace.payload({"top": rows, "orders_today": int(orders or 0), "active_visitors": active}))


def seed(ds):
    revenue = {}
    for o in ds.orders:
        if o["status"] != "cancelled":
            revenue[o["customer_id"]] = revenue.get(o["customer_id"], 0) + o["total"]
    p = ds.products[0]
    with trace.call("pipeline", "DEL ...; ZADD lm:leaderboard ...; SET lm:name:* ...; HSET lm:deal ...; SET lm:deal:stock 50", {}) as t:
        for k in list(r().scan_iter(match="lm:*", count=1000, target_nodes=RedisCluster.ALL_NODES)):
            r().delete(k)
        r().zadd("lm:leaderboard", {k: round(v, 2) for k, v in revenue.items()})
        pipe = r().pipeline()
        for c in ds.customers:
            pipe.set(f"lm:name:{c['customer_id']}", c["name"])
        pipe.execute()
        r().hset("lm:deal", mapping={"product_id": p["product_id"], "name": p["name"], "price": round(p["price"] * 0.6, 2),
                                     "old_price": p["price"], "ends_at": int(time.time()) + 6 * 3600})
        r().set("lm:deal:stock", DEAL_STOCK)
        r().set("lm:orders:today", 0)
        t.result(items=len(revenue))
    return [f"Loaded the leaderboard with {len(revenue)} customers.", f"Started the flash deal for {p['name']} with {DEAL_STOCK} pieces."]


def reset_visitors():
    n = 0
    for pattern in ("lm:session:*", "lm:sim:*"):
        for k in list(r().scan_iter(match=pattern, count=1000, target_nodes=RedisCluster.ALL_NODES)):
            r().delete(k)
            n += 1
    r().delete("lm:active")
    r().set("lm:deal:stock", DEAL_STOCK)
    return [f"Deleted {n} session keys.", f"Reset the flash deal stock to {DEAL_STOCK}."]


def status():
    return {"deal stock": r().get("lm:deal:stock"), "leaderboard members": r().zcard("lm:leaderboard")}


KEY_GROUPS = [("lm:deal", "Flash deal"), ("lm:session:", "Sessions"), ("lm:leaderboard", "Rankings and counters"),
              ("lm:active", "Rankings and counters"), ("lm:orders", "Rankings and counters"), ("lm:name:", "Names"), ("lm:sim", "Load Simulation")]
TYPE_TR = {"string": "string (text or counter)", "hash": "hash (field to value)", "zset": "sorted set (sorted by score)",
           "set": "set", "list": "list"}


def learn_overview(lesson, focus):
    """101: every lm:* key as a tile, grouped by use. `focus` = the keys that the call touched; your session key is marked too."""
    mine = f"lm:session:{visitor_id()}"
    f = set(focus) | ({mine} if lesson == "session" else set())
    with trace.call("SCAN", "SCAN 0 MATCH lm:* COUNT 500   # on every shard, at most 400 keys", {}) as t:
        keys = []
        for k in r().scan_iter(match="lm:*", count=500):
            keys.append(k)
            if len(keys) >= 400:
                break
        t.result(items=len(keys), note="SCAN walks the key space in small steps, so it does not block the cache like KEYS does.")
    keys = sorted(set(keys) | {k for k in f if k.startswith("lm:")})
    groups = {}
    for k in keys:
        label = next((g for prefix, g in KEY_GROUPS if k.startswith(prefix)), "Other")
        groups.setdefault(label, []).append(k)
    for label in groups:   # the keys of the call first, then the others
        groups[label].sort(key=lambda k: (k not in f, k))
        groups[label] = groups[label][:60]
    order = [g for _, g in KEY_GROUPS]
    return {"title": "ElastiCache (Valkey): the key space", "text": "Each key in memory is one square. The shelves are the job of the key (the prefix of its name).",
            "facts": [[len(keys), "keys (at most 400 are counted)"], [len(groups), "groups"], [len([k for k in keys if k in f]), "keys in your call"]],
            "groups": [{"label": g, "items": [{"id": k, "title": k, "hit": k in f} for k in groups[g]]}
                       for g in sorted(groups, key=lambda g: order.index(g) if g in order else 99)],
            "hit_label": "The keys that your call read or wrote"}


def learn_item(lesson, key):
    with trace.call("TYPE + read", f"TYPE {key}; <read by type>; TTL {key}", {}) as t:
        kind = r().type(key)
        if kind == "hash":
            value = r().hgetall(key)
        elif kind == "zset":
            value = {m: sc for m, sc in r().zrevrange(key, 0, 9, withscores=True)}
        elif kind == "string":
            value = r().get(key)
        elif kind == "set":
            value = sorted(r().smembers(key))[:20]
        elif kind == "list":
            value = r().lrange(key, 0, 19)
        else:
            value = None
        ttl = r().ttl(key)
        t.result(items=1 if value is not None else 0)
    rec = {"key": key, "type": TYPE_TR.get(kind, kind), "value": value,
           "TTL": "no expiry (-1)" if ttl == -1 else ("no key (-2)" if ttl == -2 else f"deleted in {ttl} seconds")}
    if kind == "zset":
        rec["value"] = {"first 10 members (by score, highest first)": value}
    return {"title": key, "sub": "One key and its value in memory. There is no table, row or query plan on disk.",
            "record": rec, "marks": {"anahtar": "kept", "TTL": "kept"}}


# ---------------------------------------------------------------- E2E tutorial queries (templates/e2e/elasticache.html)
# Tutorial keys start with lm:tut: and expire after 10 minutes, so they never pile up.
TUT_TTL = 600


def _e2e_deal():
    t = cmd("TYPE", "TYPE lm:deal", lambda: r().type("lm:deal"))
    deal = cmd("HGETALL", "HGETALL lm:deal", lambda: r().hgetall("lm:deal"))
    t2 = cmd("TYPE", "TYPE lm:deal:stock", lambda: r().type("lm:deal:stock"))
    stock = cmd("GET", "GET lm:deal:stock", lambda: r().get("lm:deal:stock"))
    rows = [["lm:deal", t, f, v] for f, v in deal.items()] + [["lm:deal:stock", t2, "(value)", stock]]
    return result_table(["key", "type", "field", "value"], rows)


def _e2e_string():
    cmd("SET", f"SET lm:tut:greeting \"merhaba\" EX {TUT_TTL}", lambda: r().set("lm:tut:greeting", "merhaba", ex=TUT_TTL))
    v = cmd("GET", "GET lm:tut:greeting", lambda: r().get("lm:tut:greeting"))
    ttl = cmd("TTL", "TTL lm:tut:greeting", lambda: r().ttl("lm:tut:greeting"))
    return result_table(["key", "value", "TTL (seconds left)"], [["lm:tut:greeting", v, ttl]])


def _e2e_counter():
    rows = []
    for _ in range(3):
        rows.append(["INCR lm:tut:visits", cmd("INCR", "INCR lm:tut:visits", lambda: r().incr("lm:tut:visits"))])
    cmd("EXPIRE", f"EXPIRE lm:tut:visits {TUT_TTL}", lambda: r().expire("lm:tut:visits", TUT_TTL))
    rows.append(["INCRBY lm:tut:visits 10", cmd("INCRBY", "INCRBY lm:tut:visits 10", lambda: r().incrby("lm:tut:visits", 10))])
    return result_table(["command", "reply (the new value)"], rows, note="Each run continues from the last value, until the key expires.")


def _e2e_hash():
    key = "lm:tut:cart:demo"
    cmd("HSET", f"HSET {key} P0001 2 P0044 1", lambda: r().hset(key, mapping={"P0001": 2, "P0044": 1}))
    cmd("HINCRBY", f"HINCRBY {key} P0001 1", lambda: r().hincrby(key, "P0001", 1))
    cmd("EXPIRE", f"EXPIRE {key} {TUT_TTL}", lambda: r().expire(key, TUT_TTL))
    h = cmd("HGETALL", f"HGETALL {key}", lambda: r().hgetall(key))
    return result_table(["field", "value"], list(h.items()), note="HSET sets P0001 to 2 again on each run, then HINCRBY adds 1. So P0001 is 3 after each run.")


def _e2e_zset():
    key = "lm:tut:board"
    scores = {"Ayşe": 36708.47, "Mert": 98210.10, "Elif": 1599.41, "Lukas": 45120.00, "Zeynep": 27300.55}
    cmd("ZADD", f"ZADD {key} " + " ".join(f"{v} {k}" for k, v in scores.items()), lambda: r().zadd(key, scores))
    cmd("ZINCRBY", f"ZINCRBY {key} 20000 Elif", lambda: r().zincrby(key, 20000, "Elif"))
    cmd("EXPIRE", f"EXPIRE {key} {TUT_TTL}", lambda: r().expire(key, TUT_TTL))
    top = cmd("ZREVRANGE", f"ZREVRANGE {key} 0 2 WITHSCORES", lambda: r().zrevrange(key, 0, 2, withscores=True))
    rank = cmd("ZREVRANK", f"ZREVRANK {key} Elif", lambda: r().zrevrank(key, "Elif"))
    rows = [[i + 1, m, s] for i, (m, s) in enumerate(top)] + [["Elif is at rank", rank + 1 if rank is not None else None, "(ZREVRANK + 1)"]]
    return result_table(["rank", "member", "score"], rows,
                        note="ZADD resets the five scores on each run. ZINCRBY then moves Elif from 1,599.41 to 21,599.41.")


def _e2e_ttl():
    key = "lm:tut:short"
    cmd("SET", f"SET {key} \"I expire soon\" EX 5", lambda: r().set(key, "I expire soon", ex=5))
    rows = []
    for wait in (0, 2, 4, 6):
        if wait:
            time.sleep(2)
        rows.append([f"after {wait} s", cmd("TTL", f"TTL {key}", lambda: r().ttl(key)), cmd("EXISTS", f"EXISTS {key}", lambda: r().exists(key))])
    return result_table(["time", "TTL (seconds left, -2 = no key)", "EXISTS"], rows)


def _e2e_race():
    """Two ways to sell 10 pieces to 60 buyers in 20 threads: GET then SET, and DECR."""
    out = []
    for mode in ("naive", "atomic"):
        key = f"lm:tut:race:{mode}:{visitor_id()}"
        r().set(key, 10, ex=TUT_TTL)
        sold = 0

        def buy(_):
            if mode == "atomic":
                if r().decr(key) >= 0:
                    return 1
                r().incr(key)
                return 0
            v = int(r().get(key))
            if v > 0:
                time.sleep(0.002)            # the app does some work between the read and the write
                r().set(key, v - 1, ex=TUT_TTL)
                return 1
            return 0
        text = (f"SET {key} 10\n60 buyers, 20 threads: " +
                ("GET stock; if > 0: SET stock (value - 1)" if mode == "naive" else "DECR stock; if < 0: INCR stock"))
        with trace.call("Load (60 buyers)", text, {"mode": mode}) as t:
            with ThreadPoolExecutor(max_workers=20) as pool:
                sold = sum(pool.map(buy, range(60)))
            left = int(r().get(key))
            t.result(items=sold)
        out.append(["GET, then SET" if mode == "naive" else "DECR", 10, sold, left, "oversold" if sold > 10 else "correct"])
    return result_table(["mode", "stock at start", "pieces sold", "stock at end", "result"], out)


def _e2e_board():
    top = cmd("ZREVRANGE", "ZREVRANGE lm:leaderboard 0 4 WITHSCORES", lambda: r().zrevrange("lm:leaderboard", 0, 4, withscores=True))
    n = cmd("ZCARD", "ZCARD lm:leaderboard", lambda: r().zcard("lm:leaderboard"))
    rows = [[i + 1, m, r().get(f"lm:name:{m}"), round(s, 2)] for i, (m, s) in enumerate(top)]
    return result_table(["rank", "member", "name (from lm:name:<id>)", "revenue (score)"], rows, note=f"The sorted set has {n} members.")


E2E = {"V1": _e2e_deal, "V2": _e2e_string, "V3": _e2e_counter, "V4": _e2e_hash, "V5": _e2e_zset, "V6": _e2e_ttl,
       "V7": _e2e_race, "V8": _e2e_board}
