"""Aurora PostgreSQL - relational: checkout (order + stock in one ACID transaction), order history, order report."""
import secrets
import time
from datetime import datetime, timezone

import psycopg
from flask import jsonify, request

from .. import trace
from ..base import env, secret
from ..visitor import persona_id, visitor_id
from . import page

META = {
    "id": "aurora", "name": "Amazon Aurora PostgreSQL", "data_type": "Structured", "category": "Relational",
    "auth": "Password (Secrets Manager)", "via": "Aurora writer endpoint (data subnet, TLS 5432)",
    "section": "Checkout and orders",
    "model": "customers(customer_id PK, name, city, segment)\nproducts(product_id PK, name, category, price, stock CHECK >= 0)\n"
             "orders(order_id PK, customer_id FK, visitor_id, order_date, status, total)\n"
             "order_items(order_id FK, product_id FK, qty, unit_price, PK(order_id, product_id))",
}
PAGES = [page("checkout", "checkout", "Checkout", "/checkout"), page("orders", "orders", "My orders", "/orders"),
         page("order_report", "order_report", "Order report", "/admin/orders")]

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
