"""DynamoDB - key-value: the Visitor's cart, addressed by partition key, with TTL and conditional writes."""
import time
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key
from flask import jsonify, request

from .. import simlimit, trace
from ..base import env, region
from ..visitor import visitor_id
from . import PRICE_READ_RU, PRICE_WRITE_RU, page, usd

META = {
    "id": "dynamodb", "name": "Amazon DynamoDB", "data_type": "Semi-structured", "category": "Key-value",
    "auth": "IAM role (SigV4)", "via": "S3/DynamoDB gateway endpoint → DynamoDB", "section": "Cart",
    "model": "Table dbws-cart\n  pk  CART#<visitor>        (partition key)\n  sk  ITEM#<product_id>     (sort key)\n"
             "  qty, name, unit_price, expires_at (TTL, 24 h)",
}
PAGES = [page("cart", "cart", "Your cart", "/cart")]
CART_TTL = 24 * 3600
MAX_QTY = 5

_table = None


def table():
    global _table
    if _table is None:
        _table = boto3.resource("dynamodb", region_name=region()).Table(env("TABLE_NAME"))
    return _table


def _units(resp, kind):
    cap = resp.get("ConsumedCapacity") or {}
    units = cap.get("CapacityUnits") or cap.get(f"{kind}CapacityUnits")
    price = PRICE_READ_RU if kind == "Read" else PRICE_WRITE_RU
    return (f"{units} {'RRU' if kind == 'Read' else 'WRU'}", usd(units * price)) if units else (None, None)


def get_cart(consistent):
    pk = f"CART#{visitor_id()}"
    req = (f"table.query(\n  KeyConditionExpression=Key('pk').eq('{pk}'),\n"
           f"  ConsistentRead={consistent}, ReturnConsumedCapacity='TOTAL')")
    with trace.call("Query", req, {"pk": pk, "ConsistentRead": consistent}) as t:
        resp = table().query(KeyConditionExpression=Key("pk").eq(pk), ConsistentRead=consistent,
                             ReturnConsumedCapacity="TOTAL")
        units, cost = _units(resp, "Read")
        t.result(items=resp["Count"], capacity=units, cost=cost,
                 note=("Strongly consistent read: you see your last write. It costs 2x an eventually consistent read."
                       if consistent else "Eventually consistent read: half the cost. A write from the last second can be missing."))
    items = [{"product_id": it["sk"].split("#", 1)[1], "name": it.get("name"), "qty": int(it["qty"]),
              "unit_price": float(it["unit_price"]), "expires_at": int(it.get("expires_at", 0))} for it in resp["Items"]]
    return items


def register(bp):
    @bp.get("/api/cart")
    def api_cart():
        consistent = request.args.get("consistent", "true") == "true"
        items = get_cart(consistent)
        return jsonify(trace.payload({"items": items, "total": round(sum(i["qty"] * i["unit_price"] for i in items), 2)}))

    @bp.post("/api/cart/items")
    def api_add():
        body = request.get_json(force=True)
        pid, limit = body["product_id"], body.get("limit", True)
        pk, sk = f"CART#{visitor_id()}", f"ITEM#{pid}"
        qty = int(body.get("qty", 1))
        expires = int(time.time()) + CART_TTL
        kwargs = dict(Key={"pk": pk, "sk": sk},
                      UpdateExpression="ADD qty :q SET #n = :n, unit_price = :p, expires_at = :e",
                      ExpressionAttributeNames={"#n": "name"},
                      ExpressionAttributeValues={":q": qty, ":n": body.get("name", pid),
                                                 ":p": Decimal(str(body.get("unit_price", 0))), ":e": expires},
                      ReturnValues="ALL_NEW", ReturnConsumedCapacity="TOTAL")
        if limit:
            kwargs["ConditionExpression"] = "attribute_not_exists(qty) OR qty <= :max"
            kwargs["ExpressionAttributeValues"][":max"] = MAX_QTY - qty
        req = ("table.update_item(\n  Key={'pk': '%s', 'sk': '%s'},\n  UpdateExpression='ADD qty :q SET #n = :n, unit_price = :p, expires_at = :e',%s\n"
               "  ReturnConsumedCapacity='TOTAL')" % (pk, sk, "\n  ConditionExpression='attribute_not_exists(qty) OR qty <= :max'," if limit else ""))
        refused = None
        with trace.call("UpdateItem", req, {"qty": qty, "expires_at": expires, "limit": f"{MAX_QTY} per product" if limit else "off"}) as t:
            try:
                resp = table().update_item(**kwargs)
                units, cost = _units(resp, "Write")
                t.result(capacity=units, cost=cost, note="ADD is atomic: two tabs can add at the same time and no update is lost. "
                         "expires_at makes DynamoDB delete the item after 24 hours (TTL), with no cost.")
            except table().meta.client.exceptions.ConditionalCheckFailedException:
                refused = f"You can add at most {MAX_QTY} pieces of one product."
                t.result(note="The ConditionExpression was false, so DynamoDB did not write. The check and the write are one atomic step.",
                         capacity="1 WRU (a failed conditional write also costs)")
        items = get_cart(True)
        return jsonify(trace.payload({"items": items, "refused": refused}))

    @bp.delete("/api/cart/items/<pid>")
    def api_remove(pid):
        pk = f"CART#{visitor_id()}"
        with trace.call("DeleteItem", f"table.delete_item(Key={{'pk': '{pk}', 'sk': 'ITEM#{pid}'}})", {}) as t:
            resp = table().delete_item(Key={"pk": pk, "sk": f"ITEM#{pid}"}, ReturnConsumedCapacity="TOTAL")
            units, cost = _units(resp, "Write")
            t.result(capacity=units, cost=cost)
        return jsonify(trace.payload({"items": get_cart(True)}))

    @bp.delete("/api/cart")
    def api_clear():
        pk = f"CART#{visitor_id()}"
        items = table().query(KeyConditionExpression=Key("pk").eq(pk), ProjectionExpression="pk, sk")["Items"]
        with trace.call("BatchWriteItem", f"batch_writer(): delete_item × {len(items)}  # pk = {pk}", {"items": len(items)}) as t:
            with table().batch_writer() as bw:
                for it in items:
                    bw.delete_item(Key={"pk": it["pk"], "sk": it["sk"]})
            t.result(items=len(items), note="Checkout empties the cart. BatchWriteItem sends up to 25 deletes in one request.")
        return jsonify(trace.payload({"items": []}))

    @bp.post("/api/simulate")
    def api_simulate():
        body = request.get_json(silent=True) or {}
        with simlimit.run(visitor_id(), body.get("requests", 1000)) as n:
            run = f"SIM#{int(time.time())}"
            expires = int(time.time()) + 600
            latencies, units = [], 0.0
            started = time.perf_counter()

            def one(i):
                t0 = time.perf_counter()
                r = table().put_item(Item={"pk": f"{run}#{i % 200}", "sk": f"ITEM#P{i % 50:04d}", "qty": 1,
                                           "expires_at": expires}, ReturnConsumedCapacity="TOTAL")
                return (time.perf_counter() - t0) * 1000, r["ConsumedCapacity"]["CapacityUnits"]

            req = (f"{n} × table.put_item(Item={{'pk': '{run}#<shopper>', 'sk': 'ITEM#<product>', 'expires_at': now+600}})\n"
                   "# 32 threads, 200 synthetic shoppers")
            with trace.call("PutItem × N", req, {"requests": n, "threads": 32}) as t:
                with ThreadPoolExecutor(max_workers=32) as pool:
                    for ms, u in pool.map(one, range(n)):
                        latencies.append(ms)
                        units += u
                elapsed = time.perf_counter() - started
                latencies.sort()
                stats = {"requests": n, "seconds": round(elapsed, 2), "per_second": round(n / elapsed),
                         "p50_ms": round(latencies[len(latencies) // 2], 1), "p95_ms": round(latencies[int(len(latencies) * 0.95)], 1),
                         "p99_ms": round(latencies[int(len(latencies) * 0.99) - 1], 1)}
                t.result(items=n, capacity=f"{units:.0f} WRU", cost=usd(units * PRICE_WRITE_RU),
                         note="On-demand mode needs no capacity planning: DynamoDB served the burst at single-digit milliseconds. "
                              "The synthetic items expire after 10 minutes (TTL).")
        return jsonify(trace.payload(stats))


def seed(ds):
    return ["DynamoDB keeps no Shared Catalog data. Each Visitor builds a cart.", reset_visitors()[0]]


def reset_visitors():
    deleted, scan = 0, {"ProjectionExpression": "pk, sk"}
    with trace.call("Scan + BatchWriteItem", "table.scan(ProjectionExpression='pk, sk') → batch delete", {}) as t:
        with table().batch_writer() as bw:
            while True:
                page_ = table().scan(**scan)
                for it in page_["Items"]:
                    bw.delete_item(Key={"pk": it["pk"], "sk": it["sk"]})
                    deleted += 1
                if "LastEvaluatedKey" not in page_:
                    break
                scan["ExclusiveStartKey"] = page_["LastEvaluatedKey"]
        t.result(items=deleted)
    return [f"Deleted {deleted} cart items."]


def status():
    d = table().meta.client.describe_table(TableName=env("TABLE_NAME"))["Table"]
    return {"items (approx.)": d.get("ItemCount"), "billing": d.get("BillingModeSummary", {}).get("BillingMode")}


def learn_overview(lesson, focus):
    """101: the table as partitions (one row per partition key) of items (sort keys). Your cart partition comes first."""
    mine = f"CART#{visitor_id()}"
    with trace.call("Scan + DescribeTable", "table.scan(ProjectionExpression='pk, sk', Limit=3000); describe_table()", {}) as t:
        resp = table().scan(ProjectionExpression="pk, sk", Limit=3000, ReturnConsumedCapacity="TOTAL")
        desc = table().meta.client.describe_table(TableName=table().name)["Table"]
        t.result(items=resp["Count"], capacity=_units(resp, "Read")[0])
    parts = {}
    for it in resp["Items"]:
        parts.setdefault(it["pk"], []).append(it["sk"])
    with trace.call("Query", f"table.query(KeyConditionExpression=Key('pk').eq('{mine}'), ProjectionExpression='pk, sk')", {}) as t:
        own = table().query(KeyConditionExpression=Key("pk").eq(mine), ProjectionExpression="pk, sk")["Items"]
        t.result(items=len(own))
    if own:
        parts[mine] = [it["sk"] for it in own]
    order = sorted(parts, key=lambda k: (k != mine, not k.startswith("CART#"), k))[:24]
    short = lambda pk: pk if len(pk) <= 22 else pk[:20] + "…"
    groups = [{"label": ("Senin sepetin" if pk == mine else short(pk)),
               "items": [{"id": f"{pk}|{sk}", "title": f"pk={pk}  sk={sk}", "hit": pk == mine} for sk in sorted(parts[pk])]}
              for pk in order]
    mode = desc.get("BillingModeSummary", {}).get("BillingMode", "PROVISIONED")
    return {"title": f"DynamoDB: {table().name} tablosu",
            "text": "Her satır bir partition (aynı pk), her kare o partition'daki bir item (sk). İlk 24 partition gösteriliyor.",
            "facts": [[desc.get("ItemCount", resp["Count"]), "item (yaklaşık, 6 saatte bir güncellenir)"], [len(parts), "partition örnekte"],
                      [mode.replace("PAY_PER_REQUEST", "on-demand"), "kapasite modu"], [len(parts.get(mine, [])), "item senin sepetinde"]],
            "groups": groups, "hit_label": "Senin sepetinin item'ları (pk = CART#<senin id>)"}


def learn_item(lesson, item_id):
    pk, _, sk = item_id.partition("|")
    with trace.call("GetItem", f"table.get_item(Key={{'pk': '{pk}', 'sk': '{sk}'}})", {}) as t:
        it = table().get_item(Key={"pk": pk, "sk": sk}).get("Item")
        t.result(items=1 if it else 0)
    if not it:
        return {"title": sk, "sub": "Bu item artık yok (TTL ile silinmiş olabilir).", "record": {}}
    rec = {k: (float(v) if isinstance(v, Decimal) else v) for k, v in it.items()}
    rec = {k: (int(v) if isinstance(v, float) and v.is_integer() else v) for k, v in rec.items()}
    order = ["pk", "sk"] + sorted(k for k in rec if k not in ("pk", "sk"))
    exp = rec.get("expires_at")
    left = f" TTL: süresi {max(0, int(exp - time.time())) // 60} dakika sonra doluyor." if exp else ""
    return {"title": f"{pk}  /  {sk}", "sub": f"Bir item: {len(rec)} attribute.{left} Sarı: anahtar (pk + sk) ve TTL.",
            "record": {k: rec[k] for k in order}, "marks": {"pk": "kept", "sk": "kept", "expires_at": "kept"}}
