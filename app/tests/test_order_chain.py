"""The order chain with stubs: no AWS and no live writes. Run: ENGINE=docdb python -m unittest discover -s app/tests"""
import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("ENGINE", "docdb")

import psycopg
from flask import Blueprint, Flask

from engine_app import trace
from engine_app.engines import aurora, elasticache, influxdb, keyspaces, neptune, order_ns

VISITOR = "abcdef12-3456"
ORDER = "W1793396741a1b2"


def client_for(mod):
    app = Flask(__name__)
    bp = Blueprint("x", __name__)
    mod.register(bp)
    app.register_blueprint(bp)
    app.before_request(lambda: trace.configure({"name": "stub"}))
    c = app.test_client()
    c.set_cookie("lm_visitor", VISITOR)
    c.set_cookie("lm_persona", "C00002")
    return c


class FakeAurora:
    """Keeps what a committed transaction wrote. `statements` is what reached the database."""

    def __init__(self):
        self.statements, self.params, self.orders, self.pending, self.ensured, self.after_lookup = [], [], {}, {}, 0, None
        self.outbox = []
        self.pending_outbox = []

    def __call__(self):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def cursor(self):
        return self

    def execute(self, text, params=None):
        if text == aurora.ENSURE:
            self.ensured += 1
            return self
        self.statements.append(text)
        self.params.append(params)
        self.rowcount, self.row = 1, None
        if text.startswith("SELECT order_id, total"):
            self.row = self.orders.get(params["rid"])
            if self.after_lookup:                    # another attempt of the same click commits just after this lookup
                self.after_lookup(), setattr(self, "after_lookup", None)
        elif text.startswith("INSERT INTO orders"):
            if params["rid"] in self.orders:
                raise psycopg.errors.UniqueViolation("orders_request_id_key")
            self.pending[params["rid"]] = (params["oid"], params["total"])
        elif text.startswith("INSERT INTO outbox"):
            self.pending_outbox.append(params)
        elif text.startswith("COMMIT"):
            self.orders.update(self.pending)
            self.outbox += self.pending_outbox
            self.pending, self.pending_outbox = {}, []
        elif text.startswith("ROLLBACK"):
            self.pending, self.pending_outbox = {}, []
        return self

    def fetchone(self):
        return self.row


class OrderTest(unittest.TestCase):
    def setUp(self):
        self.db, self.conn = FakeAurora(), aurora.conn
        aurora.conn, aurora._schema_ready = self.db, False
        self.c = client_for(aurora)
        self.items = [{"product_id": "P0131", "qty": 2, "unit_price": 3758.21}, {"product_id": "P0001", "qty": 1, "unit_price": 3373.84}]

    def tearDown(self):
        aurora.conn = self.conn

    def post(self, **extra):
        return self.c.post("/api/orders", json={"items": self.items, "request_id": "r-1", **extra}).get_json()

    def test_repeated_request_id_returns_the_same_order_and_writes_nothing(self):
        first = self.post()["data"]
        self.assertEqual(first["result"], "committed")
        written = len(self.db.statements)
        again = self.post()["data"]
        self.assertEqual(again, first)
        self.assertEqual(self.db.statements[written:], ["SELECT order_id, total FROM orders WHERE request_id = %(rid)s"])
        self.assertEqual(len(self.db.orders), 1)
        self.assertEqual(len(self.db.outbox), 1)

    def test_unique_violation_rolls_back_and_returns_the_other_attempt(self):
        self.db.after_lookup = lambda: self.db.orders.update({"r-1": ("W_OTHER", 100)})
        d = self.post()["data"]
        self.assertEqual((d["order_id"], d["result"], d["total"]), ("W_OTHER", "committed", 100.0))
        self.assertIn("ROLLBACK;", self.db.statements)
        self.assertNotIn("COMMIT;", self.db.statements)
        self.assertEqual(self.db.outbox, [])

    def test_items_lock_in_sorted_order(self):
        self.post()
        locked = [p["pid"] for t, p in zip(self.db.statements, self.db.params) if t.startswith("UPDATE products")]
        self.assertEqual(locked, ["P0001", "P0131"])

    def test_outbox_row_is_in_the_same_transaction(self):
        self.post()
        s = self.db.statements
        begin = s.index("BEGIN;")
        commit = s.index("COMMIT;")
        outbox = next(i for i, t in enumerate(s) if t.startswith("INSERT INTO outbox"))
        self.assertTrue(begin < outbox < commit)
        self.assertEqual(sum(t.startswith("INSERT INTO outbox") for t in s), 1)

    def test_failed_payment_leaves_no_outbox_row_and_allows_a_retry(self):
        d = self.post(fail_after_stock=True)["data"]
        self.assertEqual((d["result"], d["order_id"]), ("rolled back", None))
        self.assertEqual(self.db.outbox, [])
        self.assertFalse(any(t.startswith("INSERT INTO outbox") for t in self.db.statements))
        self.assertEqual(self.post()["data"]["result"], "committed")

    def test_schema_ensure_runs_once_and_is_repeatable(self):
        self.post()
        self.post(request_id="r-2")
        self.assertEqual(self.db.ensured, 1)
        for piece in ("ADD COLUMN IF NOT EXISTS request_id", "CREATE UNIQUE INDEX IF NOT EXISTS", "CREATE TABLE IF NOT EXISTS outbox", "event_id uuid PRIMARY KEY"):
            self.assertIn(piece, aurora.ENSURE)


class FakeCache:
    def __init__(self):
        self.kv, self.board, self.counter, self.pipes, self.active = {}, {}, 0, [], {}

    def __call__(self):
        return self

    def set(self, key, value, nx=False, ex=None):
        if nx and key in self.kv:
            return None
        self.kv[key] = (value, ex)
        return True

    def zincrby(self, key, amount, member):
        self.board[member] = self.board.get(member, 0) + amount

    def incr(self, key):
        self.counter += 1

    def zadd(self, key, mapping):
        self.active.update(mapping)

    def get_node_from_key(self, key):
        return "node:" + key

    def get_redis_connection(self, node):
        cache = self

        class Conn:
            def pipeline(self, transaction=None):
                p = SimpleNamespace(transaction=transaction, node=node, calls=[], executed=False)
                p.hset = lambda key, mapping: p.calls.append(("hset", key))
                p.expire = lambda key, ttl: p.calls.append(("expire", key, ttl))
                p.execute = lambda: setattr(p, "executed", True) or [0, 1]
                cache.pipes.append(p)
                return p
        return Conn()


class CacheTest(unittest.TestCase):
    def setUp(self):
        self.cache, self.r = FakeCache(), elasticache.r
        elasticache.r = self.cache
        self.c = client_for(elasticache)

    def tearDown(self):
        elasticache.r = self.r

    def test_session_is_one_multi_exec_then_zadd_alone(self):
        d = self.c.post("/api/session", json={"page": "/deals", "ttl": 30}).get_json()
        p = self.cache.pipes[0]
        key = f"lm:session:{VISITOR}"
        self.assertEqual((p.transaction, p.node, p.executed), (True, "node:" + key, True))
        self.assertEqual(p.calls, [("hset", key), ("expire", key, 30)])
        self.assertIn(VISITOR, self.cache.active)
        self.assertEqual([e["op"] for e in d["trace"]], ["MULTI/EXEC", "ZADD"])
        self.assertEqual(d["data"], {"ttl": 30})

    def test_repeated_leaderboard_add_counts_once(self):
        body = {"amount": 100.5, "order_id": ORDER}
        first = self.c.post("/api/leaderboard/add", json=body).get_json()
        again = self.c.post("/api/leaderboard/add", json=body).get_json()
        self.assertEqual(self.cache.board, {"C00002": 100.5})
        self.assertEqual(self.cache.counter, 1)
        self.assertEqual(self.cache.kv[f"processed:{ORDER}"], (1, 604800))
        self.assertEqual(set(first), set(again))
        self.assertEqual(first["data"], {"added": 100.5})
        self.assertEqual(again["data"], {"added": 0})
        self.assertEqual([e["op"] for e in first["trace"]], ["SET NX", "ZINCRBY", "INCR"])
        self.assertEqual([e["op"] for e in again["trace"]], ["SET NX"])


class GraphTest(unittest.TestCase):
    def setUp(self):
        self.calls, self.q = [], neptune._q
        neptune._q = lambda query, params=None: self.calls.append((query, params)) or []
        self.c = client_for(neptune)

    def tearDown(self):
        neptune._q = self.q

    def test_edge_is_merged_by_order_id_with_the_real_qty(self):
        d = self.c.post("/api/purchase", json={"order_id": ORDER, "products": ["P0001", "P0131"], "qty": {"P0001": 1, "P0131": 2}}).get_json()
        query, params = self.calls[0]
        self.assertIn("MERGE (c)-[b:BOUGHT {order_id: r.o}]->(p) ON CREATE SET b.qty = r.q", query)
        self.assertNotIn("CREATE (c)", query)
        self.assertEqual([(r["p"], r["o"], r["q"], r["c"]) for r in params["rows"]],
                         [("P0001", ORDER, 1, "C00002"), ("P0131", ORDER, 2, "C00002")])
        self.assertEqual(d["data"], {"edges": 2})


class ActivityTest(unittest.TestCase):
    def setUp(self):
        self.rows, self.single = [], []
        self.write_all, self.s = keyspaces.write_all, keyspaces.s
        keyspaces.write_all = lambda stmt, rows: self.rows.extend(rows) or (len(rows), 0)
        session = SimpleNamespace(prepare=lambda cql: cql, execute=lambda stmt, args: self.single.append(args))
        keyspaces.s = lambda: session
        os.environ.setdefault("KEYSPACE", "dbws")
        os.environ.setdefault("TABLE_NAME", "activity_by_user")
        self.c = client_for(keyspaces)

    def tearDown(self):
        keyspaces.write_all, keyspaces.s = self.write_all, self.s

    def buy(self):
        return self.c.post("/api/events", json={"type": "purchase", "order_id": ORDER, "products": ["P0001", "P0131"], "detail": "Order"}).get_json()

    def test_purchase_goes_to_both_partitions_with_one_event_id_per_product(self):
        d = self.buy()
        self.assertEqual(d["data"], {"stored": True})
        self.assertEqual(d["trace"][0]["items"], 4)
        self.assertEqual({r[0] for r in self.rows}, {VISITOR, "C00002"})
        ids = {}
        for uid, at, eid, kind, pid, _ in self.rows:
            ids.setdefault(pid, set()).add(eid)
            self.assertEqual(kind, "purchase")
        self.assertEqual({k: len(v) for k, v in ids.items()}, {"P0001": 1, "P0131": 1})
        self.assertNotEqual(ids["P0001"], ids["P0131"])

    def test_repeated_purchase_is_the_same_rows(self):
        self.buy()
        keys = {r[:3] for r in self.rows}
        self.assertEqual(len(keys), 4)
        self.buy()
        self.assertEqual({r[:3] for r in self.rows}, keys)   # same primary key, so Keyspaces overwrites

    def test_a_view_stays_in_the_visitor_partition(self):
        d = self.c.post("/api/events", json={"type": "view", "product_id": "P0001", "detail": "x"}).get_json()
        self.assertEqual(self.rows, [])
        self.assertEqual([a[0] for a in self.single], [VISITOR])
        self.assertEqual(d["trace"][0]["items"], 1)


class FakeInflux:
    def __init__(self, sink):
        self.sink = sink

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def write_api(self, write_options=None):
        return SimpleNamespace(write=lambda bucket, org, record: self.sink.append(record.to_line_protocol()))


class MetricTest(unittest.TestCase):
    def setUp(self):
        self.lines, self.client, self.flux = [], influxdb.client, influxdb.flux
        influxdb.client = lambda: FakeInflux(self.lines)
        self.c = client_for(influxdb)

    def tearDown(self):
        influxdb.client, influxdb.flux = self.client, self.flux

    def test_timestamp_is_stable_for_one_order_and_differs_between_orders(self):
        for _ in range(2):
            self.assertEqual(self.c.post("/api/orders-metric", json={"count": 1, "order_id": ORDER}).get_json()["data"], {"written": 1})
        self.assertEqual(self.lines[0], self.lines[1])
        self.assertEqual(self.lines[0], f"orders,channel=web count=1i {1793396741 * 10**9 + 0xa1b2}")
        self.c.post("/api/orders-metric", json={"count": 1, "order_id": "W1793396741a1b3"})
        self.assertNotEqual(self.lines[0], self.lines[2])

    def test_series_still_reads_the_channel(self):
        rec = SimpleNamespace(values={"channel": "web"}, get_time=lambda: SimpleNamespace(isoformat=lambda: "t"), get_value=lambda: 3)
        influxdb.flux = lambda op, q, note=None: [SimpleNamespace(records=[rec])]
        d = self.c.get("/api/series?measure=orders").get_json()
        self.assertEqual(d["data"]["series"], {"web": [{"t": "t", "v": 3}]})


class OrderTimeTest(unittest.TestCase):
    def test_order_ns(self):
        self.assertEqual(order_ns(ORDER), 1793396741 * 10**9 + 0xa1b2)
        self.assertIsNone(order_ns("O000001"))
        self.assertIsNone(order_ns(None))


if __name__ == "__main__":
    unittest.main()
