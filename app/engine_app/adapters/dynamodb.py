"""DynamoDB - key-value: shopping carts addressed by partition key."""
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key

from ..base import Adapter, ReadResult, SeedResult, env, region
from ..domain import sample_customer

MODEL = """\
Table dbws-cart (on-demand)
  pk  (partition key)  CART#<customer_id>
  sk  (sort key)       ITEM#<product_id>   | META
  attributes           name, qty, unit_price, added_at   (schemaless: each item may differ)

Access pattern: "get the whole cart of one customer" = Query(pk = CART#C00001)"""


class DynamoDb(Adapter):
    engine_id = "dynamodb"
    title = "Amazon DynamoDB"
    data_type = "Semi-structured"
    category = "Key-value"
    domain_slice = "alışveriş sepeti"
    why = ("Erişim deseni önceden bilinen, anahtarla okunan/yazılan veriler için: her ölçekte tek haneli milisaniye. "
           "Sunucu yok, on-demand kapasite. JOIN yok: model, sorguya göre tasarlanır (partition key + sort key).")
    model = MODEL

    def __init__(self):
        self.table = boto3.resource("dynamodb", region_name=region()).Table(env("TABLE_NAME"))

    def seed(self, ds):
        deleted = 0
        scan = {"ProjectionExpression": "pk, sk"}
        with self.table.batch_writer() as bw:
            while True:
                page = self.table.scan(**scan)
                for it in page["Items"]:
                    bw.delete_item(Key={"pk": it["pk"], "sk": it["sk"]})
                    deleted += 1
                if "LastEvaluatedKey" not in page:
                    break
                scan["ExclusiveStartKey"] = page["LastEvaluatedKey"]
        price = {p["product_id"]: p for p in ds.products}
        first_order = {}                                 # one open cart per customer, built from their first order
        for o in ds.orders:
            first_order.setdefault(o["customer_id"], o)
        carts = list(first_order.values())
        written = 0
        with self.table.batch_writer(overwrite_by_pkeys=["pk", "sk"]) as bw:
            for o in carts:
                pk = f"CART#{o['customer_id']}"
                bw.put_item(Item={"pk": pk, "sk": "META", "customer_id": o["customer_id"], "updated_at": o["order_date"]})
                for i in o["items"]:
                    p = price[i["product_id"]]
                    bw.put_item(Item={"pk": pk, "sk": f"ITEM#{i['product_id']}", "name": p["name"], "qty": i["qty"],
                                      "unit_price": Decimal(str(i["unit_price"])), "added_at": o["order_date"]})
                    written += 1
        # the sample customer always has a cart, so Read shows data
        c = sample_customer(ds)
        with self.table.batch_writer(overwrite_by_pkeys=["pk", "sk"]) as bw:
            for p in ds.products[:3]:
                bw.put_item(Item={"pk": f"CART#{c['customer_id']}", "sk": f"ITEM#{p['product_id']}", "name": p["name"],
                                  "qty": 1, "unit_price": Decimal(str(p["price"])), "added_at": "now"})
        return SeedResult(
            summary=[f"{deleted} eski öğe silindi (Scan + BatchWriteItem)", f"{len(carts)} sepet, {written} sepet kalemi yazıldı",
                     "Her öğe pk=CART#<müşteri>, sk=ITEM#<ürün>"],
            operation="table.batch_writer():  # BatchWriteItem, 25 öğelik gruplar\n"
                      "  put_item({'pk': 'CART#C00001', 'sk': 'ITEM#P0001', 'qty': 1, 'unit_price': 499.0, ...})",
            counts={"carts": len(carts), "items": written})

    def read(self):
        pk = "CART#C00001"
        resp = self.table.query(KeyConditionExpression=Key("pk").eq(pk) & Key("sk").begins_with("ITEM#"))
        rows = [(it["sk"].split("#", 1)[1], it.get("name"), int(it["qty"]), float(it["unit_price"]),
                 round(int(it["qty"]) * float(it["unit_price"]), 2)) for it in resp["Items"]]
        return ReadResult(["product_id", "name", "qty", "unit_price", "line_total"], rows,
                          f"table.query(KeyConditionExpression=Key('pk').eq('{pk}') & Key('sk').begins_with('ITEM#'))",
                          note=f"Tek partition okundu, tablo boyutundan bağımsız. Tüketilen okuma: {resp.get('Count')} öğe, Scan yok.")


ADAPTER = DynamoDb
