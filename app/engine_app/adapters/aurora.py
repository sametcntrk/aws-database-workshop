"""Aurora PostgreSQL - relational: customers and orders with joins and transactions."""
import psycopg

from ..base import Adapter, ReadResult, SeedResult, env, secret

DDL = """\
DROP TABLE IF EXISTS order_items, orders, products, customers;
CREATE TABLE customers (customer_id text PRIMARY KEY, name text NOT NULL, email text UNIQUE,
                        city text, segment text, created_at timestamptz);
CREATE TABLE products  (product_id text PRIMARY KEY, name text, category text, price numeric(10,2));
CREATE TABLE orders    (order_id text PRIMARY KEY, customer_id text REFERENCES customers,
                        order_date timestamptz, status text, total numeric(12,2));
CREATE TABLE order_items (order_id text REFERENCES orders, product_id text REFERENCES products,
                          qty int, unit_price numeric(10,2), PRIMARY KEY (order_id, product_id));
CREATE INDEX ON orders (customer_id);"""

READ_SQL = """\
SELECT c.customer_id, c.name, c.city, c.segment,
       count(DISTINCT o.order_id)        AS orders,
       sum(oi.qty * oi.unit_price)       AS revenue,
       max(o.order_date)::date           AS last_order
FROM customers c
JOIN orders o       ON o.customer_id = c.customer_id AND o.status <> 'cancelled'
JOIN order_items oi ON oi.order_id = o.order_id
GROUP BY c.customer_id, c.name, c.city, c.segment
ORDER BY revenue DESC
LIMIT 10;"""


class Aurora(Adapter):
    engine_id = "aurora"
    title = "Amazon Aurora PostgreSQL"
    data_type = "Structured"
    category = "Relational"
    domain_slice = "müşteriler ve siparişler"
    why = ("Sabit şemalı, birbirine bağlı veriler (müşteri → sipariş → sipariş kalemi) ve ACID transaction gerektiğinde. "
           "JOIN, foreign key ve ad-hoc SQL raporlama güçlüdür. Serverless v2 kapasiteyi ACU olarak otomatik ölçekler.")
    model = DDL

    def _conn(self):
        s = secret(env("DB_SECRET_ARN"))
        return psycopg.connect(host=env("DB_HOST"), port=int(env("DB_PORT", "5432")), dbname=env("DB_NAME", "shop"),
                               user=s["username"], password=s["password"], sslmode="require", connect_timeout=10)

    def seed(self, ds):
        items = [(o["order_id"], i["product_id"], i["qty"], i["unit_price"]) for o in ds.orders for i in o["items"]]
        with self._conn() as conn, conn.cursor() as cur:   # one transaction: all or nothing
            cur.execute(DDL)
            with cur.copy("COPY customers (customer_id, name, email, city, segment, created_at) FROM STDIN") as cp:
                for c in ds.customers:
                    cp.write_row((c["customer_id"], c["name"], c["email"], c["city"], c["segment"], c["created_at"]))
            with cur.copy("COPY products (product_id, name, category, price) FROM STDIN") as cp:
                for p in ds.products:
                    cp.write_row((p["product_id"], p["name"], p["category"], p["price"]))
            with cur.copy("COPY orders (order_id, customer_id, order_date, status, total) FROM STDIN") as cp:
                for o in ds.orders:
                    cp.write_row((o["order_id"], o["customer_id"], o["order_date"], o["status"], o["total"]))
            with cur.copy("COPY order_items (order_id, product_id, qty, unit_price) FROM STDIN") as cp:
                for row in items:
                    cp.write_row(row)
        return SeedResult(
            summary=[f"{len(ds.customers)} müşteri", f"{len(ds.products)} ürün", f"{len(ds.orders)} sipariş",
                     f"{len(items)} sipariş kalemi", "Hepsi tek transaction içinde COPY ile yazıldı."],
            operation=DDL + "\n\nCOPY customers / products / orders / order_items FROM STDIN;  -- tek transaction",
            counts={"customers": len(ds.customers), "orders": len(ds.orders), "order_items": len(items)})

    def read(self):
        with self._conn() as conn, conn.cursor() as cur:
            cur.execute(READ_SQL)
            cols = [d.name for d in cur.description]
            rows = cur.fetchall()
        return ReadResult(cols, rows, READ_SQL, note="4 tablo, 2 JOIN: ilişkisel modelin gücü tek SQL ile rapor.")


ADAPTER = Aurora
