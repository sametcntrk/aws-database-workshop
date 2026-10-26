"""DocumentDB - document: product catalog with nested, per-category attributes."""
import json

from pymongo import MongoClient

from ..base import Adapter, ReadResult, SeedResult, env, secret

CA_FILE = "/opt/engine-app/certs/global-bundle.pem"   # downloaded by bootstrap.sh

MODEL = """\
db.products  (one JSON document per product, schema can differ per category)
{
  "_id": "P0001", "name": "Anadolu Kablosuz Kulaklık 1", "category": "Elektronik",
  "brand": "Anadolu", "price": 1299.9, "stock": 120, "rating": 4.6,
  "attributes": {"renk": "siyah", "garanti_ay": 24, "agirlik_kg": 0.3},
  "tags": ["yeni", "hızlı kargo"]
}
Index: {category: 1, "attributes.renk": 1}"""

FIND = """db.products.find(
  {"category": "Elektronik", "attributes.renk": "siyah", "rating": {"$gte": 4}},
  {"name": 1, "price": 1, "rating": 1, "attributes": 1, "tags": 1}
).sort("rating", -1).limit(10)"""

AGG = """db.products.aggregate([
  {"$group": {"_id": "$category", "products": {"$sum": 1}, "avg_price": {"$avg": "$price"}}},
  {"$sort": {"products": -1}}
])"""


class DocDb(Adapter):
    engine_id = "docdb"
    title = "Amazon DocumentDB (MongoDB uyumlu)"
    data_type = "Semi-structured"
    category = "Document"
    domain_slice = "ürün kataloğu"
    why = ("Her kaydın kendi iç içe yapısı olabildiği, nesneyi bir bütün olarak okuyan uygulamalar için: katalog, profil, "
           "içerik. Şema esnektir; iç içe alanlar indekslenip sorgulanabilir. MongoDB API ve sürücüleriyle çalışır.")
    model = MODEL

    def _db(self):
        s = secret(env("DB_SECRET_ARN"))
        client = MongoClient(host=env("DB_HOST"), port=int(env("DB_PORT", "27017")), username=s["username"],
                             password=s["password"], tls=True, tlsCAFile=CA_FILE, replicaSet="rs0",
                             readPreference="secondaryPreferred", retryWrites=False, serverSelectionTimeoutMS=15000)
        return client, client["shop"]

    def seed(self, ds):
        client, db = self._db()
        try:
            db.products.drop()
            docs = [{"_id": p["product_id"], **{k: v for k, v in p.items() if k != "product_id"}} for p in ds.products]
            db.products.insert_many(docs, ordered=False)
            db.products.create_index([("category", 1), ("attributes.renk", 1)])
        finally:
            client.close()
        return SeedResult(
            summary=["products koleksiyonu silindi ve yeniden oluşturuldu", f"{len(docs)} ürün dokümanı yazıldı (insert_many)",
                     "İndeks: {category: 1, attributes.renk: 1}"],
            operation="db.products.drop()\ndb.products.insert_many([...], ordered=False)\n"
                      "db.products.create_index([('category', 1), ('attributes.renk', 1)])",
            counts={"products": len(docs)})

    def read(self):
        client, db = self._db()
        try:
            found = list(db.products.find({"category": "Elektronik", "attributes.renk": "siyah", "rating": {"$gte": 4}},
                                          {"name": 1, "price": 1, "rating": 1, "attributes": 1, "tags": 1})
                         .sort("rating", -1).limit(10))
            agg = list(db.products.aggregate([{"$group": {"_id": "$category", "products": {"$sum": 1},
                                                          "avg_price": {"$avg": "$price"}}}, {"$sort": {"products": -1}}]))
        finally:
            client.close()
        rows = [(d["_id"], d["name"], d["price"], d["rating"], json.dumps(d["attributes"], ensure_ascii=False),
                 ", ".join(d["tags"])) for d in found]
        summary = " · ".join(f"{a['_id']}: {a['products']} ürün, ort. {a['avg_price']:.0f} TL" for a in agg)
        return ReadResult(["_id", "name", "price", "rating", "attributes", "tags"], rows, FIND + "\n\n" + AGG,
                          note=f"İç içe alan (attributes.renk) üzerinde filtre. Aggregation: {summary}")


ADAPTER = DocDb
