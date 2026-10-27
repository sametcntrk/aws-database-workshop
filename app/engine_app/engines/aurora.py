"""Aurora PostgreSQL - relational: checkout (order + stock in one ACID transaction), order history, order report."""
import secrets
import time
from datetime import datetime, timezone

import psycopg
from flask import jsonify, request

from .. import catalog, trace
from ..base import env, secret
from ..visitor import persona_id, visitor_id
from . import table

META = catalog.META["aurora"]
PAGES = catalog.PAGES["aurora"]

DDL = """DROP TABLE IF EXISTS order_items, orders, products, customers;
CREATE TABLE customers (customer_id text PRIMARY KEY, name text NOT NULL, email text, city text, segment text, created_at timestamptz);
CREATE TABLE products  (product_id text PRIMARY KEY, name text, category text, price numeric(10,2), stock int NOT NULL CHECK (stock >= 0));
CREATE TABLE orders    (order_id text PRIMARY KEY, customer_id text REFERENCES customers, visitor_id text,
                        order_date timestamptz, status text, total numeric(12,2));
CREATE TABLE order_items (order_id text REFERENCES orders ON DELETE CASCADE, product_id text REFERENCES products,
                          qty int, unit_price numeric(10,2), PRIMARY KEY (order_id, product_id));
CREATE INDEX ON orders (customer_id);
CREATE INDEX ON orders (visitor_id);"""


def conn():
    s = secret(env("DB_SECRET_ARN"))
    return psycopg.connect(host=env("DB_HOST"), port=int(env("DB_PORT", "5432")), dbname=env("DB_NAME", "shop"),
                           user=s["username"], password=s["password"], sslmode="require", connect_timeout=10)


def sql(cur, op, text, params=None, note=None):
    """Run one statement and record it as its own trace entry."""
    with trace.call(op, text.strip(), params if isinstance(params, dict) else {"params": params} if params else {}) as t:
        cur.execute(text, params)
        t.result(items=cur.rowcount if cur.rowcount >= 0 else None, note=note)
    return cur


def register(bp):
    @bp.post("/api/orders")
    def api_order():
        body = request.get_json(force=True)
        items = body.get("items", [])
        fail = bool(body.get("fail_after_stock"))
        if not items:
            return jsonify(ok=False, error="The cart is empty.", trace=[]), 400
        order_id = f"W{int(time.time())}{secrets.token_hex(2)}"
        total = round(sum(i["qty"] * float(i["unit_price"]) for i in items), 2)
        result, message = "committed", None
        with conn() as c, c.cursor() as cur:
            c.autocommit = True           # BEGIN / COMMIT / ROLLBACK below are the real statements
            sql(cur, "BEGIN", "BEGIN;", note="Everything until COMMIT is one transaction: all of it happens, or none of it.")
            try:
                for i in items:
                    sql(cur, "UPDATE (stock)", "UPDATE products SET stock = stock - %(qty)s WHERE product_id = %(pid)s AND stock >= %(qty)s",
                        {"qty": i["qty"], "pid": i["product_id"]}, note="The row lock stops two checkouts from selling the same last piece.")
                    if cur.rowcount == 0:
                        raise ValueError(f"Not enough stock for {i['product_id']}.")
                if fail:
                    raise RuntimeError("Experiment: the payment step failed after the stock update.")
                sql(cur, "INSERT (order)", "INSERT INTO orders VALUES (%(oid)s, %(cid)s, %(vid)s, now(), 'processing', %(total)s)",
                    {"oid": order_id, "cid": persona_id(), "vid": visitor_id(), "total": total})
                for i in items:
                    sql(cur, "INSERT (order item)", "INSERT INTO order_items VALUES (%(oid)s, %(pid)s, %(qty)s, %(price)s)",
                        {"oid": order_id, "pid": i["product_id"], "qty": i["qty"], "price": i["unit_price"]})
                sql(cur, "COMMIT", "COMMIT;", note="The order, its items and the stock change are now durable on 6 copies in 3 AZs.")
            except Exception as e:
                result, message = "rolled back", str(e)
                sql(cur, "ROLLBACK", "ROLLBACK;",
                    note="PostgreSQL undid every statement since BEGIN. The stock is unchanged and no order exists.")
        return jsonify(trace.payload({"order_id": order_id if result == "committed" else None, "result": result,
                                      "message": message, "total": total}))

    @bp.get("/api/orders")
    def api_orders():
        q = """SELECT o.order_id, o.order_date, o.status, o.total, count(oi.*) AS lines, string_agg(p.name, ', ') AS products
FROM orders o JOIN order_items oi USING (order_id) JOIN products p USING (product_id)
WHERE o.visitor_id = %(vid)s
GROUP BY o.order_id ORDER BY o.order_date DESC LIMIT 20"""
        with conn() as c, c.cursor() as cur:
            sql(cur, "SELECT (JOIN)", q, {"vid": visitor_id()}, note="Three tables joined by their keys in one statement.")
            cols = [d.name for d in cur.description]
            rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        return jsonify(trace.payload([{**r, "order_date": r["order_date"].isoformat(), "total": float(r["total"])} for r in rows]))

    @bp.get("/api/report")
    def api_report():
        explain = request.args.get("explain") == "on"
        q = """SELECT c.segment, count(DISTINCT o.order_id) AS orders, sum(oi.qty * oi.unit_price) AS revenue,
       round(avg(o.total), 2) AS avg_order
FROM orders o JOIN customers c USING (customer_id) JOIN order_items oi USING (order_id)
WHERE o.status <> 'cancelled'
GROUP BY c.segment ORDER BY revenue DESC"""
        today = """SELECT date_trunc('hour', order_date) AS hour, count(*) AS orders, sum(total) AS revenue
FROM orders WHERE visitor_id IS NOT NULL GROUP BY 1 ORDER BY 1"""
        with conn() as c, c.cursor() as cur:
            sql(cur, "SELECT (report)", q, note="Aurora answers operational reports well on small and medium data. "
                "For large scans across years, the Redshift report is the better tool.")
            seg = [{"segment": r[0], "orders": r[1], "revenue": float(r[2]), "avg_order": float(r[3])} for r in cur.fetchall()]
            plan = None
            if explain:
                sql(cur, "EXPLAIN ANALYZE", "EXPLAIN ANALYZE " + q)
                plan = "\n".join(r[0] for r in cur.fetchall())
            sql(cur, "SELECT (workshop orders)", today)
            hours = [{"hour": r[0].isoformat(), "orders": r[1], "revenue": float(r[2])} for r in cur.fetchall()]
        return jsonify(trace.payload({"segments": seg, "workshop": hours, "plan": plan}))


def _rows(cur):
    cols = [d.name for d in cur.description]
    clean = lambda v: float(v) if hasattr(v, "as_integer_ratio") and not isinstance(v, (int, float)) else (v.isoformat() if hasattr(v, "isoformat") else v)
    return [{c: clean(v) for c, v in zip(cols, r)} for r in cur.fetchall()]


def learn_overview(lesson, focus):
    """101: the four tables as shelves. Your orders, their items, products and the persona customer are marked."""
    vid, cid = visitor_id(), persona_id()
    with conn() as c, c.cursor() as cur:
        sql(cur, "SELECT (counts)", "SELECT (SELECT count(*) FROM customers), (SELECT count(*) FROM products), "
            "(SELECT count(*) FROM orders), (SELECT count(*) FROM order_items)")
        counts = cur.fetchone()
        sql(cur, "SELECT (your orders)", "SELECT o.order_id, oi.product_id FROM orders o JOIN order_items oi USING (order_id) "
            "WHERE o.visitor_id = %(vid)s ORDER BY o.order_date DESC LIMIT 60", {"vid": vid})
        mine = cur.fetchall()
        my_orders = list(dict.fromkeys(o for o, _ in mine))
        my_products = list(dict.fromkeys(p for _, p in mine))
        sample = {}
        for tbl, key, order in (("customers", "customer_id", "customer_id"), ("products", "product_id", "product_id"),
                                ("orders", "order_id", "order_date DESC"), ("order_items", "order_id || '|' || product_id", "order_id DESC")):
            sql(cur, f"SELECT ({tbl})", f"SELECT {key} FROM {tbl} ORDER BY {order} LIMIT 40")
            sample[tbl] = [r[0] for r in cur.fetchall()]
    hits = {"customers": {cid}, "products": set(my_products), "orders": set(my_orders),
            "order_items": {f"{o}|{p}" for o, p in mine}}
    first = {"customers": [cid], "products": my_products, "orders": my_orders, "order_items": [f"{o}|{p}" for o, p in mine]}
    labels = {"customers": "customers", "products": "products", "orders": "orders", "order_items": "order_items"}
    groups = []
    for tbl in ("customers", "orders", "order_items", "products"):
        ids = list(dict.fromkeys(first[tbl] + sample[tbl]))[:48]
        groups.append({"label": labels[tbl], "items": [{"id": f"{tbl}:{i}", "title": f"{tbl}: {i}", "hit": i in hits[tbl]} for i in ids]})
    return {"title": "Aurora PostgreSQL: shop veritabanı", "text": "Dört tablo, her biri bir raf. Her kare bir satır (her tablodan en fazla 48 satır gösteriliyor).",
            "facts": [[counts[0], "müşteri"], [counts[1], "ürün"], [counts[2], "sipariş"], [counts[3], "sipariş satırı"], [len(my_orders), "sipariş senin"]],
            "groups": groups, "hit_label": "Senin siparişlerin ve onlara bağlı satırlar"}


def learn_item(lesson, item_id):
    tbl, _, key = item_id.partition(":")
    with conn() as c, c.cursor() as cur:
        if tbl == "orders":
            sql(cur, "SELECT", "SELECT * FROM orders WHERE order_id = %(k)s", {"k": key})
            row = (_rows(cur) or [{}])[0]
            sql(cur, "SELECT (JOIN)", "SELECT oi.*, p.name, p.category FROM order_items oi JOIN products p USING (product_id) WHERE oi.order_id = %(k)s", {"k": key})
            items = _rows(cur)
            sql(cur, "SELECT", "SELECT * FROM customers WHERE customer_id = %(c)s", {"c": row.get("customer_id")})
            cust = (_rows(cur) or [None])[0]
            rec = {**row, "order_items (JOIN, order_id ile)": [{"product_id": i["product_id"], "qty": i["qty"], "unit_price": i["unit_price"],
                                                                 "products (JOIN, product_id ile)": {"name": i["name"], "category": i["category"]}} for i in items],
                   "customers (JOIN, customer_id ile)": cust}
            marks = {"order_id": "kept", "customer_id": "kept"}
            return {"title": f"Sipariş {key}", "sub": "orders tablosunda bir satır. Altında, anahtarlarla bağlı öteki tabloların satırları var (JOIN).",
                    "record": rec, "marks": marks}
        if tbl == "order_items":
            oid, _, pid = key.partition("|")
            sql(cur, "SELECT (JOIN)", "SELECT oi.*, p.name FROM order_items oi JOIN products p USING (product_id) WHERE order_id = %(o)s AND product_id = %(p)s",
                {"o": oid, "p": pid})
            row = (_rows(cur) or [{}])[0]
            return {"title": f"Sipariş satırı {oid} / {pid}", "sub": "order_items: bir siparişin bir ürünü. order_id ve product_id öteki tablolara işaret eder.",
                    "record": row, "marks": {"order_id": "kept", "product_id": "kept"}}
        keycol = {"customers": "customer_id", "products": "product_id"}.get(tbl)
        if not keycol:
            return {"title": item_id, "sub": "Bilinmeyen tablo.", "record": {}}
        sql(cur, "SELECT", f"SELECT * FROM {tbl} WHERE {keycol} = %(k)s", {"k": key})
        row = (_rows(cur) or [{}])[0]
        if tbl == "customers":
            sql(cur, "SELECT", "SELECT order_id, order_date, total FROM orders WHERE customer_id = %(k)s ORDER BY order_date DESC LIMIT 5", {"k": key})
            row["orders (son 5, customer_id ile)"] = _rows(cur)
        else:
            sql(cur, "SELECT", "SELECT count(*) AS satir, coalesce(sum(qty), 0) AS adet FROM order_items WHERE product_id = %(k)s", {"k": key})
            row["order_items içinde (sayım)"] = _rows(cur)[0]
    return {"title": f"{tbl}: {key}", "sub": f"{tbl} tablosunda bir satır. Her sütunun tipi tabloyu kurarken bir kez belirlendi.",
            "record": row, "marks": {keycol: "kept"}}


def seed(ds):
    with conn() as c, c.cursor() as cur:
        with trace.call("DDL + COPY", DDL + "\nCOPY ... FROM STDIN  -- 4 tables, one transaction", {}) as t:
            cur.execute(DDL)
            with cur.copy("COPY customers (customer_id, name, email, city, segment, created_at) FROM STDIN") as cp:
                for x in ds.customers:
                    cp.write_row((x["customer_id"], x["name"], x["email"], x["city"], x["segment"], x["created_at"]))
            with cur.copy("COPY products (product_id, name, category, price, stock) FROM STDIN") as cp:
                for p in ds.products:
                    cp.write_row((p["product_id"], p["name"], p["category"], p["price"], max(p["stock"], 20)))
            with cur.copy("COPY orders (order_id, customer_id, order_date, status, total) FROM STDIN") as cp:
                for o in ds.orders:
                    cp.write_row((o["order_id"], o["customer_id"], o["order_date"], o["status"], o["total"]))
            n_items = 0
            with cur.copy("COPY order_items (order_id, product_id, qty, unit_price) FROM STDIN") as cp:
                for o in ds.orders:
                    for i in {x["product_id"]: x for x in o["items"]}.values():
                        cp.write_row((o["order_id"], i["product_id"], i["qty"], i["unit_price"]))
                        n_items += 1
            t.result(items=len(ds.orders))
    return [f"Wrote {len(ds.customers)} customers, {len(ds.products)} products, {len(ds.orders)} orders, {n_items} order items.",
            "All tables have primary keys, so the zero-ETL integration replicates them to Redshift."]


def reset_visitors():
    with conn() as c, c.cursor() as cur:
        sql(cur, "DELETE", "DELETE FROM orders WHERE visitor_id IS NOT NULL")
        n = cur.rowcount
    return [f"Deleted {n} Visitor orders (their items go with ON DELETE CASCADE)."]


def status():
    with conn() as c, c.cursor() as cur:
        cur.execute("SELECT (SELECT count(*) FROM orders), (SELECT count(*) FROM orders WHERE visitor_id IS NOT NULL)")
        a, b = cur.fetchone()
    return {"orders": a, "visitor orders": b, "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}


# ---------------------------------------------------------------- E2E tutorial queries (templates/e2e/aurora.html)
def _e2e(steps, note=None, rollback=False):
    """Run statements in one connection. The last statement gives the result table. rollback: the writes do not stay."""
    with conn() as c, c.cursor() as cur:
        c.autocommit = True
        result = None
        if rollback:
            sql(cur, "BEGIN", "BEGIN;")
        try:
            for op, text in steps:
                sql(cur, op, text)
            result = table([d.name for d in cur.description], cur.fetchall(), note=note)
        except psycopg.Error as e:
            result = table(["PostgreSQL refused the statement"], [[f"{type(e).__name__}: {str(e).strip()}"]], note=note)
        if rollback:
            sql(cur, "ROLLBACK", "ROLLBACK;", note="The tutorial query keeps no change.")
        return result


E2E = {
    "A1": lambda: _e2e([("SELECT (row counts)", """SELECT 'customers' AS table_name, count(*) AS rows FROM customers
UNION ALL SELECT 'products', count(*) FROM products
UNION ALL SELECT 'orders', count(*) FROM orders
UNION ALL SELECT 'order_items', count(*) FROM order_items""")]),
    "A2": lambda: _e2e([("SELECT (one row)", "SELECT * FROM customers WHERE customer_id = 'C00001'")]),
    "A3": lambda: _e2e([("SELECT (JOIN)", """SELECT o.order_id, o.order_date::date AS order_date, c.name AS customer,
       p.name AS product, oi.qty, oi.unit_price, oi.qty * oi.unit_price AS line_total
FROM orders o
JOIN customers   c  ON c.customer_id = o.customer_id
JOIN order_items oi ON oi.order_id   = o.order_id
JOIN products    p  ON p.product_id  = oi.product_id
WHERE o.order_id = 'O000001'""")]),
    "A4": lambda: _e2e([("SELECT (GROUP BY)", """SELECT p.category, count(DISTINCT o.order_id) AS orders,
       sum(oi.qty) AS pieces, round(sum(oi.qty * oi.unit_price), 2) AS revenue
FROM order_items oi
JOIN orders o   ON o.order_id = oi.order_id
JOIN products p ON p.product_id = oi.product_id
WHERE o.status <> 'cancelled'
GROUP BY p.category
ORDER BY revenue DESC""")]),
    "A5": lambda: _e2e([("SELECT (indexes)", """SELECT tablename, indexname, indexdef
FROM pg_indexes WHERE schemaname = 'public' ORDER BY tablename, indexname""")]),
    "A6": lambda: _e2e([("EXPLAIN ANALYZE (by key)", "EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM customers WHERE customer_id = 'C00450'")],
                       note="Index Scan: PostgreSQL walks the B-tree of the primary key to one row."),
    "A7": lambda: _e2e([("EXPLAIN ANALYZE (no index)", "EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM customers WHERE email = 'ayse.yilmaz@example.com'")],
                       note="Seq Scan: no index on email, so PostgreSQL reads each row of the table and tests the filter."),
    "A8": lambda: _e2e([("INSERT (bad foreign key)", "INSERT INTO order_items VALUES ('O000001', 'P9999', 1, 10.00)")], rollback=True,
                       note="The foreign key stops an order item that points to no product."),
    "A9": lambda: _e2e([("UPDATE (breaks CHECK)", "UPDATE products SET stock = stock - 100000 WHERE product_id = 'P0001'")], rollback=True,
                       note="The CHECK (stock >= 0) constraint stops a negative stock."),
    "A10": lambda: _e2e([("UPDATE (conditional)", """UPDATE products SET stock = stock - 1
WHERE product_id = 'P0001' AND stock >= 1
RETURNING product_id, stock AS stock_after""")], rollback=True,
                        note="One statement tests and changes the row under a row lock. The ROLLBACK puts the stock back."),
}
