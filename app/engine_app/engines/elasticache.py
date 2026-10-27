"""ElastiCache Serverless (Valkey) - in-memory: flash deal counter, session with TTL, live leaderboard."""
import random
import time
from concurrent.futures import ThreadPoolExecutor

from flask import jsonify, request
from redis.cluster import RedisCluster

from .. import catalog, simlimit, trace
from ..base import env, secret
from ..visitor import PERSONAS, persona_id, visitor_id

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
            r().delete(key)
        return jsonify(trace.payload({"mode": mode, "buyers": buyers, "stock": stock, "winners": winners, "oversold": oversold,
                                      "seconds": round(time.perf_counter() - started, 2),
                                      "p50_ms": round(latencies[len(latencies) // 2], 2),
                                      "p95_ms": round(latencies[int(len(latencies) * 0.95)], 2)}))

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


KEY_GROUPS = [("lm:deal", "Flash deal"), ("lm:session:", "Oturumlar (session)"), ("lm:leaderboard", "Sıralama ve sayaçlar"),
              ("lm:active", "Sıralama ve sayaçlar"), ("lm:orders", "Sıralama ve sayaçlar"), ("lm:name:", "İsimler"), ("lm:sim", "Load Simulation")]
TYPE_TR = {"string": "string (metin veya sayaç)", "hash": "hash (alan → değer)", "zset": "sorted set (puana göre sıralı)",
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
        label = next((g for prefix, g in KEY_GROUPS if k.startswith(prefix)), "Öteki")
        groups.setdefault(label, []).append(k)
    for label in groups:   # the keys of the call first, then the others
        groups[label].sort(key=lambda k: (k not in f, k))
        groups[label] = groups[label][:60]
    order = [g for _, g in KEY_GROUPS]
    return {"title": "ElastiCache (Valkey): anahtar uzayı", "text": "Bellekteki her anahtar bir kare. Raflar anahtarın işi (adındaki önek).",
            "facts": [[len(keys), "anahtar (en fazla 400 sayılır)"], [len(groups), "grup"], [len([k for k in keys if k in f]), "anahtar senin çağrında"]],
            "groups": [{"label": g, "items": [{"id": k, "title": k, "hit": k in f} for k in groups[g]]}
                       for g in sorted(groups, key=lambda g: order.index(g) if g in order else 99)],
            "hit_label": "Senin çağrının okuduğu veya yazdığı anahtarlar"}


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
    rec = {"anahtar": key, "tip": TYPE_TR.get(kind, kind), "değer": value,
           "TTL": "süresiz (-1)" if ttl == -1 else ("anahtar yok (-2)" if ttl == -2 else f"{ttl} saniye sonra silinecek")}
    if kind == "zset":
        rec["değer"] = {"ilk 10 üye (puana göre, büyükten küçüğe)": value}
    return {"title": key, "sub": "Bellekte tek bir anahtar ve değeri. Diskte tablo, satır veya sorgu planı yok.",
            "record": rec, "marks": {"anahtar": "kept", "TTL": "kept"}}
