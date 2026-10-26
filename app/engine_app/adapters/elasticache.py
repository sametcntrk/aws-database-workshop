"""ElastiCache Serverless (Valkey) - in-memory: sessions with TTL and a sales leaderboard."""
from redis.cluster import RedisCluster

from ..base import Adapter, ReadResult, SeedResult, env, secret

MODEL = """\
dbws:session:<session_id>   HASH  {customer_id, name, city, cart_items, last_page}   TTL 3600 s
dbws:leaderboard:revenue    ZSET  member = customer_id, score = total revenue
dbws:name:<customer_id>     STRING customer name (for the leaderboard page)

Access patterns: microsecond GET/HGETALL by key, ZREVRANGE for "top N"."""


class ElastiCache(Adapter):
    engine_id = "elasticache"
    title = "Amazon ElastiCache Serverless (Valkey)"
    data_type = "Semi-structured"
    category = "In-memory"
    domain_slice = "oturumlar ve liderlik tablosu"
    why = ("Mikrosaniye gecikme gereken, kaybedilebilir veya yeniden üretilebilir veriler için: oturum, önbellek, sayaç, "
           "sıralı liste (sorted set). Veri bellekte durur; TTL ile kendiliğinden silinir. Kalıcı ana veritabanı değildir.")
    model = MODEL

    def _client(self):
        s = secret(env("CACHE_SECRET_ARN"))
        return RedisCluster(host=env("CACHE_HOST"), port=int(env("CACHE_PORT", "6379")), ssl=True,
                            username=s["username"], password=s["password"], decode_responses=True,
                            socket_timeout=10)

    def seed(self, ds):
        r = self._client()
        old = list(r.scan_iter(match="dbws:*", count=1000, target_nodes=RedisCluster.ALL_NODES))
        for k in old:
            r.delete(k)
        revenue = {}
        for o in ds.orders:
            if o["status"] != "cancelled":
                revenue[o["customer_id"]] = revenue.get(o["customer_id"], 0) + o["total"]
        r.zadd("dbws:leaderboard:revenue", {k: round(v, 2) for k, v in revenue.items()})
        pipe = r.pipeline()
        for c in ds.customers:
            pipe.set(f"dbws:name:{c['customer_id']}", c["name"])
        pipe.execute()
        sessions = ds.customers[: max(50, len(ds.customers) // 5)]
        pipe = r.pipeline()
        for i, c in enumerate(sessions, start=1):
            key = f"dbws:session:s{i:05d}"
            pipe.hset(key, mapping={"customer_id": c["customer_id"], "name": c["name"], "city": c["city"],
                                    "cart_items": i % 5, "last_page": f"/urun/P{(i % 50) + 1:04d}"})
            pipe.expire(key, 3600)
        pipe.execute()
        return SeedResult(
            summary=[f"{len(old)} eski anahtar silindi", f"{len(revenue)} müşteri liderlik tablosuna eklendi (ZADD)",
                     f"{len(sessions)} oturum yazıldı (HSET + EXPIRE 3600)"],
            operation="ZADD dbws:leaderboard:revenue <revenue> <customer_id> ...\n"
                      "HSET dbws:session:s00001 customer_id C00001 name ... cart_items 1\nEXPIRE dbws:session:s00001 3600",
            counts={"leaderboard": len(revenue), "sessions": len(sessions)})

    def read(self):
        r = self._client()
        top = r.zrevrange("dbws:leaderboard:revenue", 0, 9, withscores=True)
        rows = [(rank, cid, r.get(f"dbws:name:{cid}"), score) for rank, (cid, score) in enumerate(top, start=1)]
        sess = r.hgetall("dbws:session:s00001")
        ttl = r.ttl("dbws:session:s00001")
        note = f"Örnek oturum dbws:session:s00001 = {sess} · kalan TTL {ttl} s" if sess else "Oturum bulunamadı: Seed çalıştırın."
        return ReadResult(["rank", "customer_id", "name", "revenue"], rows,
                          "ZREVRANGE dbws:leaderboard:revenue 0 9 WITHSCORES\nGET dbws:name:<customer_id>\n"
                          "HGETALL dbws:session:s00001\nTTL dbws:session:s00001", note=note)


ADAPTER = ElastiCache
