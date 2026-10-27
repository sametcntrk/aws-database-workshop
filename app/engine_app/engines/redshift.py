"""Redshift Serverless - columnar: the sales Report Screen. Live data arrives from Aurora by zero-ETL integration
(docs/adr/0001-aurora-to-redshift-zero-etl.md)."""
import redshift_connector
from flask import jsonify, request

from .. import trace
from ..base import env, secret
from ..visitor import visitor_id
from . import page

META = {
    "id": "redshift", "name": "Amazon Redshift Serverless", "data_type": "Structured", "category": "Columnar",
    "auth": "Password (Secrets Manager)", "via": "Redshift Serverless workgroup endpoint (data subnet, TLS 5439)",
    "section": "Sales reports",
    "model": "dev.public.sales            history: DISTKEY customer_id, SORTKEY order_date\n"
             "aurora_live.public.*        live copy of the Aurora tables (zero-ETL integration)",
}
PAGES = [page("reports", "reports", "Sales reports", "/admin/reports")]
LIVE_DB = "aurora_live"

DIMENSIONS = {
    "month": ("date_trunc('month', order_date)::date", "month"),
    "category": ("category", "category"),
    "city": ("city", "city"),
}
HISTORY = """CREATE TABLE IF NOT EXISTS sales (order_id varchar(16), order_date date SORTKEY, customer_id varchar(8) DISTKEY,
  city varchar(32), category varchar(32), product_id varchar(8), qty smallint, amount decimal(12,2))"""


def conn(database=None):
    s = secret(env("DB_SECRET_ARN"))
    c = redshift_connector.connect(host=env("DB_HOST"), port=int(env("DB_PORT", "5439")), database=database or env("DB_NAME", "dev"),
                                   user=s["username"], password=s["password"], ssl=True, sslmode="verify-ca", timeout=30)
    c.autocommit = True
    return c


def run(op, text, note=None, database=None):
    with trace.call(op, text, {"database": database or env("DB_NAME", "dev")}) as t:
        c = conn(database)
        try:
            cur = c.cursor()
            cur.execute(text)
            cols = [d[0] for d in cur.description] if cur.description else []
            rows = cur.fetchall() if cur.description else []
        finally:
            c.close()
        t.result(items=len(rows), note=note)
    return cols, rows


def integration_id():
    return env("INTEGRATION_ARN", "").rsplit(":", 1)[-1]


def register(bp):
    @bp.get("/api/report")
    def api_report():
        dim = request.args.get("dim", "month")
        source = request.args.get("source", "history")
        expr, alias = DIMENSIONS.get(dim, DIMENSIONS["month"])
        if source == "live":
            q = f"""SELECT {expr.replace('order_date', 'o.order_date').replace('category', 'p.category').replace('city', 'c.city')} AS {alias},
       count(DISTINCT o.order_id) AS orders, sum(oi.qty) AS units, sum(oi.qty * oi.unit_price) AS revenue
FROM {LIVE_DB}.public.orders o
JOIN {LIVE_DB}.public.order_items oi ON oi.order_id = o.order_id
JOIN {LIVE_DB}.public.products p ON p.product_id = oi.product_id
JOIN {LIVE_DB}.public.customers c ON c.customer_id = o.customer_id
WHERE o.status <> 'cancelled'
GROUP BY 1 ORDER BY revenue DESC LIMIT 24"""
            note = ("This query reads the Aurora tables that zero-ETL replicates into Redshift. "
                    "An order you place in checkout appears here within seconds, with no pipeline code.")
        else:
            q = f"""SELECT {expr} AS {alias}, count(DISTINCT order_id) AS orders, sum(qty) AS units, sum(amount) AS revenue
FROM sales GROUP BY 1 ORDER BY revenue DESC LIMIT 24"""
            note = "Columnar storage reads only the columns in the query; the other columns of the table stay on disk."
        cols, rows = run("SELECT (report)", q, note)
        return jsonify(trace.payload({"columns": cols, "rows": [[str(v) if not isinstance(v, (int, float)) else v for v in r] for r in rows]}))

    @bp.get("/api/replication")
    def api_replication():
        cols, rows = run("SELECT (integration status)",
                         "SELECT integration_id, target_database, state, total_tables_replicated, total_tables_failed, last_replicated_checkpoint\n"
                         "FROM svv_integration",
                         note="svv_integration shows the state of the zero-ETL integration.")
        status = dict(zip(cols, rows[0])) if rows else {}
        lag, connected = None, False
        try:
            _, r2 = run("SELECT (newest live order)",
                        f"SELECT max(order_date) AS newest, datediff(second, max(order_date)::timestamp, getdate()) AS seconds_ago\n"
                        f"FROM {LIVE_DB}.public.orders WHERE visitor_id IS NOT NULL",
                        note=f"Reads the zero-ETL copy of the Aurora orders table in the database {LIVE_DB}.")
            connected = True
            if r2 and r2[0][0]:
                lag = {"newest": str(r2[0][0]), "seconds_ago": r2[0][1]}
        except Exception:
            pass   # the trace entry shows the error: the database is not connected yet
        return jsonify(trace.payload({"integration": {k: str(v) for k, v in status.items()}, "newest_visitor_order": lag,
                                      "connected": connected,
                                      "integration_id": integration_id()}))

    @bp.post("/api/admin/zeroetl")
    def api_zeroetl():
        from ..admin import _authorized
        if not _authorized():
            return jsonify(ok=False, error="The admin key is not correct."), 403
        q = f"CREATE DATABASE {LIVE_DB} FROM INTEGRATION '{integration_id()}' DATABASE shop"
        run("CREATE DATABASE", q, note="One statement connects Redshift to the integration. Redshift then copies every Aurora table "
            "and keeps it in step.")
        return jsonify(trace.payload({"database": LIVE_DB}))


def seed(ds):
    city = {c["customer_id"]: c["city"] for c in ds.customers}
    rows = [(o["order_id"], o["order_date"][:10], o["customer_id"], city[o["customer_id"]], i["category"], i["product_id"],
             i["qty"], round(i["qty"] * i["unit_price"], 2)) for o in ds.orders if o["status"] != "cancelled" for i in o["items"]]
    with trace.call("DDL + INSERT", "DROP TABLE IF EXISTS sales; " + HISTORY + "; INSERT INTO sales VALUES (...), ...", {}) as t:
        c = conn()
        try:
            cur = c.cursor()
            cur.execute("DROP TABLE IF EXISTS sales")
            cur.execute(HISTORY)
            for k in range(0, len(rows), 1000):
                chunk = rows[k:k + 1000]
                cur.execute("INSERT INTO sales VALUES " + ",".join(["(%s,%s,%s,%s,%s,%s,%s,%s)"] * len(chunk)), [v for r in chunk for v in r])
        finally:
            c.close()
        t.result(items=len(rows))
    out = [f"Wrote {len(rows)} history rows into sales."]
    try:
        run("SELECT", f"SELECT 1 FROM {LIVE_DB}.public.orders LIMIT 1")
        out.append(f"The zero-ETL database {LIVE_DB} exists.")
    except Exception:
        out.append(f"The zero-ETL database {LIVE_DB} does not exist yet. Use 'Connect zero-ETL' in the Admin Console.")
    return out


def reset_visitors():
    return ["Redshift keeps no Visitor data. Visitor orders disappear here when Aurora deletes them (zero-ETL)."]


def status():
    _, rows = run("SELECT", "SELECT count(*) FROM sales")
    return {"history rows": rows[0][0] if rows else 0, "integration": integration_id()}


SALES_COLS = ["order_id", "order_date", "customer_id", "city", "category", "product_id", "qty", "amount"]
DIM_COLS = {"month": "order_date", "category": "category", "city": "city"}


def _v(v):
    return v.isoformat() if hasattr(v, "isoformat") else float(v) if hasattr(v, "as_integer_ratio") and not isinstance(v, (int, float)) else v


def learn_overview(lesson, focus):
    """101. report: the sales table drawn as columns (each shelf is one column, each tile one value).
    zeroetl: the Aurora orders that zero-ETL copied into the aurora_live database; your orders are marked."""
    if lesson == "zeroetl":
        _, cnt = run("SELECT (counts)", f"SELECT (SELECT count(*) FROM {LIVE_DB}.public.orders), (SELECT count(*) FROM {LIVE_DB}.public.order_items),"
                     f" (SELECT count(*) FROM {LIVE_DB}.public.customers), (SELECT count(*) FROM {LIVE_DB}.public.products)")
        _, rows = run("SELECT", f"SELECT order_id, visitor_id FROM {LIVE_DB}.public.orders ORDER BY order_date DESC LIMIT 96")
        vid = visitor_id()
        mine = [r for r in rows if r[1] == vid]
        others = [r for r in rows if r[1] != vid]
        return {"title": f"Redshift: {LIVE_DB} veritabanı (zero-ETL kopyası)",
                "text": "Aurora'daki orders tablosunun Redshift'teki kopyası. Her kare bir sipariş; en yeni 96 sipariş gösteriliyor.",
                "facts": [[cnt[0][0], "sipariş"], [cnt[0][1], "sipariş satırı"], [cnt[0][2], "müşteri"], [cnt[0][3], "ürün"], [len(mine), "sipariş senin"]],
                "groups": [{"label": "Senin siparişlerin", "items": [{"id": f"o:{r[0]}", "title": r[0], "hit": True} for r in mine]},
                           {"label": "Öteki siparişler", "items": [{"id": f"o:{r[0]}", "title": r[0], "hit": False} for r in others]}],
                "hit_label": "Senin checkout'ta verdiğin siparişler"}
    used = {DIM_COLS.get(f, f) for f in focus} | {"order_id", "qty", "amount"} if focus else {"order_date", "order_id", "qty", "amount"}
    _, cnt = run("SELECT", "SELECT count(*) FROM sales")
    _, rows = run("SELECT", f"SELECT {', '.join(SALES_COLS)} FROM sales ORDER BY order_date LIMIT 36")
    return {"title": "Redshift: sales tablosu, sütun sütun",
            "text": "Redshift tabloyu satır satır değil, sütun sütun saklar. Her raf bir sütun, her kare o sütunun bir değeri (ilk 36 satır).",
            "facts": [[cnt[0][0], "satır"], [len(SALES_COLS), "sütun"], ["customer_id", "DISTKEY"], ["order_date", "SORTKEY"],
                      [len(used), "sütun senin sorgunda"]],
            "groups": [{"label": col, "items": [{"id": f"c:{col}:{i}", "title": f"{col} = {_v(r[j])}", "hit": col in used}
                                                for i, r in enumerate(rows)]} for j, col in enumerate(SALES_COLS)],
            "hit_label": "Senin raporunun okuduğu sütunlar"}


def learn_item(lesson, item_id):
    kind, _, rest = item_id.partition(":")
    if kind == "o":
        oid = rest.replace("'", "")
        cols, rows = run("SELECT", f"SELECT * FROM {LIVE_DB}.public.orders WHERE order_id = '{oid}'")
        order = {c: _v(v) for c, v in zip(cols, rows[0])} if rows else {}
        cols, rows = run("SELECT", f"SELECT product_id, qty, unit_price FROM {LIVE_DB}.public.order_items WHERE order_id = '{oid}'")
        order["order_items (aynı veritabanında)"] = [{c: _v(v) for c, v in zip(cols, r)} for r in rows]
        return {"title": f"Sipariş {oid}", "sub": "Aurora'da yazılan satırın Redshift'teki kopyası. Bunu kimse kopyalamadı: zero-ETL kopyaladı.",
                "record": order, "marks": {"order_id": "kept", "order_date": "kept"}}
    col, _, idx = rest.partition(":")
    if col not in SALES_COLS:
        return {"title": col, "sub": "Bilinmeyen sütun.", "record": {}}
    _, st = run("SELECT", f"SELECT count(DISTINCT {col}), min({col}), max({col}) FROM sales")
    _, sample = run("SELECT", f"SELECT {col} FROM sales ORDER BY order_date LIMIT 36")
    _, typ = run("SELECT", f"SELECT type, encoding, distkey, sortkey FROM pg_table_def WHERE tablename = 'sales' AND \"column\" = '{col}'")
    t = typ[0] if typ else ("?", "?", False, 0)
    i = int(idx or 0)
    return {"title": f"Sütun: {col}", "sub": f"Bu sütunun bütün değerleri diskte yan yana durur ve birlikte sıkıştırılır ({t[1]}).",
            "record": {"sütun": col, "tip": t[0], "sıkıştırma (encoding)": t[1], "DISTKEY": bool(t[2]), "SORTKEY sırası": t[3],
                       "farklı değer sayısı": st[0][0], "en küçük": _v(st[0][1]), "en büyük": _v(st[0][2]),
                       "seçtiğin kare": {"satır": i + 1, "değer": _v(sample[i][0]) if i < len(sample) else None},
                       "ilk 8 değer (diskteki sırayla)": [_v(r[0]) for r in sample[:8]]},
            "marks": {"seçtiğin kare": "kept"}}
