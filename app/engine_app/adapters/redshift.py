"""Redshift Serverless - columnar: a sales fact table for analytics."""
import redshift_connector

from ..base import Adapter, ReadResult, SeedResult, env, secret

DDL = """\
DROP TABLE IF EXISTS sales;
CREATE TABLE sales (
  order_id    varchar(10),
  order_date  date        SORTKEY,
  customer_id varchar(8)  DISTKEY,
  city        varchar(32),
  category    varchar(32),
  product_id  varchar(8),
  qty         smallint,
  amount      decimal(12,2)
);"""

READ_SQL = """\
SELECT date_trunc('month', order_date)::date AS month,
       category,
       count(DISTINCT order_id)              AS orders,
       sum(qty)                              AS units,
       sum(amount)                           AS revenue
FROM sales
GROUP BY 1, 2
ORDER BY month DESC, revenue DESC
LIMIT 30;"""


class Redshift(Adapter):
    engine_id = "redshift"
    title = "Amazon Redshift Serverless"
    data_type = "Structured"
    category = "Columnar"
    domain_slice = "satış analitiği"
    why = ("Milyonlarca satır üzerinde az sayıda sütunu tarayan analitik sorgular (GROUP BY, SUM) için. "
           "Sütun bazlı depolama ve sıkıştırma sadece gereken sütunları okur. OLTP için değil, raporlama ve BI için.")
    model = DDL

    def _conn(self):
        s = secret(env("DB_SECRET_ARN"))
        return redshift_connector.connect(host=env("DB_HOST"), port=int(env("DB_PORT", "5439")),
                                          database=env("DB_NAME", "dev"), user=s["username"], password=s["password"],
                                          ssl=True, sslmode="verify-ca", timeout=20)

    def seed(self, ds):
        city = {c["customer_id"]: c["city"] for c in ds.customers}
        rows = [(o["order_id"], o["order_date"][:10], o["customer_id"], city[o["customer_id"]], i["category"],
                 i["product_id"], i["qty"], round(i["qty"] * i["unit_price"], 2))
                for o in ds.orders if o["status"] != "cancelled" for i in o["items"]]
        conn = self._conn()
        try:
            cur = conn.cursor()
            for stmt in DDL.split(";"):
                if stmt.strip():
                    cur.execute(stmt)
            batch = 1000
            for k in range(0, len(rows), batch):
                chunk = rows[k:k + batch]
                values = ",".join(["(%s,%s,%s,%s,%s,%s,%s,%s)"] * len(chunk))
                cur.execute(f"INSERT INTO sales VALUES {values}", [v for r in chunk for v in r])
            conn.commit()
        finally:
            conn.close()
        return SeedResult(
            summary=[f"{len(rows)} satış satırı (iptal edilmeyen siparişlerin kalemleri)",
                     "DISTKEY customer_id, SORTKEY order_date",
                     "Gerçek hayatta S3'ten COPY kullanılır; burada çok satırlı INSERT ile 1000'lik gruplar halinde yazıldı."],
            operation=DDL + "\n\nINSERT INTO sales VALUES (...), (...), ...;  -- 1000 satırlık gruplar",
            counts={"sales": len(rows)})

    def read(self):
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute(READ_SQL)
            cols = [d[0] for d in cur.description]
            rows = cur.fetchall()
        finally:
            conn.close()
        return ReadResult(cols, rows, READ_SQL,
                          note="Sorgu 8 sütundan sadece 5'ini okur: sütun bazlı depolamada diğer sütunlar diskten hiç okunmaz.")


ADAPTER = Redshift
