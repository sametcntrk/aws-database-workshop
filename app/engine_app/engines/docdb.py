"""DocumentDB - document: the product catalog. Owns the home page, category lists, product pages and the Admin Console page."""
import json

from flask import jsonify, request
from pymongo import MongoClient

from .. import catalog, trace
from ..base import env, secret

CA_FILE = "/opt/engine-app/certs/global-bundle.pem"
META = catalog.META["docdb"]
PAGES = catalog.PAGES["docdb"]
CARD = {"name": 1, "price": 1, "rating": 1, "category": 1, "brand": 1, "tags": 1, "stock": 1}

_client = None


def db():
    global _client
    if _client is None:
        s = secret(env("DB_SECRET_ARN"))
        _client = MongoClient(host=env("DB_HOST"), port=int(env("DB_PORT", "27017")), username=s["username"],
                              password=s["password"], tls=True, tlsCAFile=CA_FILE, replicaSet="rs0",
                              readPreference="secondaryPreferred", retryWrites=False, serverSelectionTimeoutMS=15000)
    return _client["shop"]


def _doc(d):
    d = dict(d)
    d["product_id"] = d.pop("_id")
    return d


def register(bp):
    @bp.get("/api/home")
    def api_home():
        pipeline = [{"$group": {"_id": "$category", "products": {"$sum": 1}, "from_price": {"$min": "$price"}}},
                    {"$sort": {"_id": 1}}]
        with trace.call("aggregate", "db.products.aggregate([\n  { $group: { _id: '$category', products: { $sum: 1 }, from_price: { $min: '$price' } } },\n  { $sort: { _id: 1 } }\n])", {}) as t:
            cats = list(db().products.aggregate(pipeline))
            t.result(items=len(cats), note="One aggregation computes the category menu on the server.")
        with trace.call("find", "db.products.find({ rating: { $gte: 4.5 } }, <card fields>).sort({ rating: -1 }).limit(8)", {}) as t:
            featured = [_doc(d) for d in db().products.find({"rating": {"$gte": 4.5}}, CARD).sort("rating", -1).limit(8)]
            t.result(items=len(featured), note="The projection returns only the fields a product card needs.")
        return jsonify(trace.payload({"categories": [{"name": c["_id"], "products": c["products"], "from_price": c["from_price"]} for c in cats],
                                      "featured": featured}))

    @bp.get("/api/products")
    def api_products():
        cat = request.args.get("category")
        color = request.args.get("color")
        sort = request.args.get("sort", "rating")
        use_index = request.args.get("index", "on") == "on"
        flt = {"category": cat} if cat else {}
        if color:
            flt["attributes.renk"] = color
        order = [("price", 1)] if sort == "price" else [("rating", -1)]
        find = {"find": "products", "filter": flt, "projection": CARD, "sort": dict(order), "limit": 48}
        if not use_index:
            find["hint"] = {"$natural": 1}
        req = (f"db.products.find({json.dumps(flt, ensure_ascii=False)}, <card fields>)"
               f".sort({json.dumps(dict(order))}).limit(48)" + ("" if use_index else ".hint({ $natural: 1 })  // no index"))
        with trace.call("find + explain", req, {"index": "on" if use_index else "off (collection scan)"}) as t:
            cur = db().products.find(flt, CARD).sort(order).limit(48)
            if not use_index:
                cur = cur.hint([("$natural", 1)])
            items = [_doc(d) for d in cur]
            plan = db().command("explain", find, verbosity="executionStats")
            stats = plan.get("executionStats", {})
            stage = json.dumps(plan.get("queryPlanner", {}).get("winningPlan", {}))[:300]
            t.result(items=len(items), explain=f"docs examined: {stats.get('totalDocsExamined', '?')}, returned: {stats.get('nReturned', '?')}",
                     note=("The index on { category, rating } finds the documents directly." if use_index else
                           "Without an index DocumentDB reads every document in the collection (COLLSCAN)."),
                     plan=stage)
        colors = db().products.distinct("attributes.renk", {"category": cat} if cat else {})
        return jsonify(trace.payload({"items": items, "colors": sorted(colors)}))

    @bp.get("/api/product/<pid>")
    def api_product(pid):
        full = request.args.get("projection", "full") == "full"
        with trace.call("find_one", f"db.products.find_one({{ _id: '{pid}' }}{'' if full else ', <card fields>'})",
                        {"projection": "full document" if full else "card fields"}) as t:
            d = db().products.find_one({"_id": pid}, None if full else CARD)
            size = len(json.dumps(d, default=str, ensure_ascii=False).encode()) if d else 0
            t.result(items=1 if d else 0, note=f"Document size: {size} bytes. Nested attributes come back in one read, with no JOIN.")
        if not d:
            return jsonify(ok=False, error=f"Product {pid} does not exist.", trace=trace.payload()["trace"]), 404
        return jsonify(trace.payload(_doc(d)))


def learn_overview(lesson, focus):
    """101: every product document as a tile, by category; `focus` = the product ids that the call returned or read."""
    f = set(focus)
    with trace.call("find + collStats", "db.products.find({}, { name: 1, category: 1 }); db.runCommand({ collStats: 'products' })", {}) as t:
        docs = list(db().products.find({}, {"name": 1, "category": 1}).sort("_id", 1))
        stats = db().command("collStats", "products")
        indexes = db().products.index_information()
        t.result(items=len(docs))
    cats = sorted({d["category"] for d in docs})
    return {"title": "DocumentDB: products koleksiyonu", "text": "Kataloğun asıl kaydı. Her kare bir JSON belgesi; raflar kategoriler.",
            "facts": [[stats.get("count", len(docs)), "belge"], [f"{int(stats.get('avgObjSize', 0))} bayt", "ortalama belge boyutu"],
                      [len(indexes), "index (_id dahil)"], [len(f & {d["_id"] for d in docs}), "belge senin çağrında"]],
            "groups": [{"label": c, "items": [{"id": d["_id"], "title": f"{d['_id']}: {d['name']}", "hit": d["_id"] in f}
                                              for d in docs if d["category"] == c]} for c in cats],
            "hit_label": "Senin çağrının okuduğu belgeler"}


def learn_item(lesson, pid):
    with trace.call("find_one", f"db.products.find_one({{ _id: '{pid}' }})", {}) as t:
        d = db().products.find_one({"_id": pid})
        t.result(items=1 if d else 0)
    if not d:
        return {"title": pid, "sub": "Bu belge yok.", "record": {}}
    size = len(json.dumps(d, default=str, ensure_ascii=False).encode())
    marks = {"_id": "kept", "category": "kept", "rating": "kept", "attributes.renk": "kept"}
    return {"title": d["name"], "sub": f"products koleksiyonunda bir belge: {len(d)} alan, {size} bayt. Sarı alanların index'i var.",
            "record": d, "marks": marks}


def seed(ds):
    with trace.call("drop + insert_many + create_index", "db.products.drop(); db.products.insert_many([...]); create_index(...)", {}) as t:
        db().products.drop()
        docs = [{"_id": p["product_id"], **{k: v for k, v in p.items() if k != "product_id"}} for p in ds.products]
        db().products.insert_many(docs, ordered=False)
        db().products.create_index([("category", 1), ("rating", -1)])
        db().products.create_index([("attributes.renk", 1)])
        db().products.create_index([("rating", -1)])
        t.result(items=len(docs))
    return [f"Wrote {len(docs)} product documents.", "Created indexes on {category, rating}, {attributes.renk} and {rating}."]


def reset_visitors():
    return ["DocumentDB keeps no Visitor data."]


def status():
    return {"products": db().products.estimated_document_count()}
