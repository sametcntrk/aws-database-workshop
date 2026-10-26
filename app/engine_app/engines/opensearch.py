"""OpenSearch Service - text search with facets and typo tolerance, and the store finder (geo_point)."""
import boto3
from flask import jsonify, request
from opensearchpy import AWSV4SignerAuth, OpenSearch, RequestsHttpConnection, helpers

from .. import trace
from ..base import env, region
from . import page

META = {
    "id": "opensearch", "name": "Amazon OpenSearch Service", "data_type": "Unstructured",
    "category": "Text search + Geospatial", "auth": "IAM role (SigV4)",
    "via": "OpenSearch VPC endpoint (data subnet, HTTPS 443)", "section": "Search and stores",
    "model": "index products: name (tr_folded) + name.std (standard), description, category (keyword), price, rating\n"
             "index stores:   name, city (keyword), location (geo_point)",
}
PAGES = [page("search", "search", "Search", "/search"), page("stores", "stores", "Find a store", "/stores")]

_client = None


def client():
    global _client
    if _client is None:
        creds = boto3.Session(region_name=region()).get_credentials()
        _client = OpenSearch(hosts=[{"host": env("OS_HOST"), "port": 443}], http_auth=AWSV4SignerAuth(creds, region(), "es"),
                             use_ssl=True, verify_certs=True, connection_class=RequestsHttpConnection, timeout=60)
    return _client


def _show(body):
    import json
    return json.dumps(body, ensure_ascii=False, indent=1)


def register(bp):
    @bp.get("/api/search")
    def api_search():
        q = request.args.get("q", "").strip()
        fuzzy = request.args.get("fuzzy", "on") == "on"
        analyzer = request.args.get("analyzer", "folded")
        cat = request.args.get("category")
        field = "name" if analyzer == "folded" else "name.std"
        match = {"multi_match": {"query": q, "fields": [f"{field}^3", "description"]}}
        if fuzzy:
            match["multi_match"]["fuzziness"] = "AUTO"
        query = {"bool": {"must": [match] if q else [{"match_all": {}}], "filter": [{"term": {"category": cat}}] if cat else []}}
        body = {"query": query, "size": 24,
                "aggs": {"categories": {"terms": {"field": "category"}},
                         "price": {"range": {"field": "price", "ranges": [{"to": 500}, {"from": 500, "to": 2000}, {"from": 2000}]}}}}
        with trace.call("_search", f"GET products/_search\n{_show(body)}", {"fuzziness": "AUTO" if fuzzy else "off", "analyzer": analyzer}) as t:
            r = client().search(index="products", body=body)
            t.result(items=r["hits"]["total"]["value"], note=f"OpenSearch took {r['took']} ms. "
                     + ("Fuzziness lets 'kulaklik' and 'kulaklk' match 'Kulaklık'. " if fuzzy else "Fuzziness is off: a typo finds nothing. ")
                     + ("The tr_folded analyzer turns ı, ş, ğ into i, s, g, so ASCII queries match." if analyzer == "folded"
                        else "The standard analyzer keeps Turkish letters: 'kulaklik' is a different word than 'kulaklık'."))
        hits = [{"product_id": h["_id"], "score": round(h["_score"] or 0, 2), **h["_source"]} for h in r["hits"]["hits"]]
        aggs = {"categories": [{"name": b["key"], "count": b["doc_count"]} for b in r["aggregations"]["categories"]["buckets"]],
                "price": [{"key": b["key"], "count": b["doc_count"]} for b in r["aggregations"]["price"]["buckets"]]}
        return jsonify(trace.payload({"hits": hits, "aggs": aggs, "total": r["hits"]["total"]["value"]}))

    @bp.get("/api/suggest")
    def api_suggest():
        q = request.args.get("q", "").strip()
        body = {"query": {"match_phrase_prefix": {"name": q}}, "size": 6, "_source": ["name", "category"]}
        with trace.call("_search (prefix)", f"GET products/_search\n{_show(body)}", {"q": q}) as t:
            r = client().search(index="products", body=body)
            t.result(items=len(r["hits"]["hits"]), note="match_phrase_prefix gives search-as-you-type suggestions.")
        return jsonify(trace.payload([{"product_id": h["_id"], **h["_source"]} for h in r["hits"]["hits"]]))

    @bp.get("/api/stores")
    def api_stores():
        lat, lon = float(request.args.get("lat", 41.0082)), float(request.args.get("lon", 28.9784))
        km = int(request.args.get("km", 25))
        body = {"query": {"geo_distance": {"distance": f"{km}km", "location": {"lat": lat, "lon": lon}}},
                "sort": [{"_geo_distance": {"location": {"lat": lat, "lon": lon}, "order": "asc", "unit": "km"}}], "size": 20}
        with trace.call("_search (geo_distance)", f"GET stores/_search\n{_show(body)}", {"radius": f"{km} km"}) as t:
            r = client().search(index="stores", body=body)
            t.result(items=len(r["hits"]["hits"]), note="geo_point fields support distance filters and distance sorting.")
        stores = [{"store_id": h["_id"], "distance_km": round(h["sort"][0], 1), **h["_source"]} for h in r["hits"]["hits"]]
        return jsonify(trace.payload(stores))


def seed(ds):
    c = client()
    with trace.call("indices.create + _bulk", "PUT products {...}; PUT stores {...}; POST _bulk", {}) as t:
        for idx in ("products", "stores"):
            if c.indices.exists(index=idx):
                c.indices.delete(index=idx)
        c.indices.create(index="products", body={
            "settings": {"analysis": {"filter": {"tr_lower": {"type": "lowercase", "language": "turkish"}},
                                      "analyzer": {"tr_folded": {"tokenizer": "standard", "filter": ["tr_lower", "asciifolding"]}}}},
            "mappings": {"properties": {
                "name": {"type": "text", "analyzer": "tr_folded", "fields": {"std": {"type": "text", "analyzer": "standard"}}},
                "description": {"type": "text", "analyzer": "tr_folded"}, "category": {"type": "keyword"},
                "brand": {"type": "keyword"}, "price": {"type": "float"}, "rating": {"type": "float"}}}})
        c.indices.create(index="stores", body={"mappings": {"properties": {
            "name": {"type": "text"}, "city": {"type": "keyword"}, "location": {"type": "geo_point"}}}})
        n_p, _ = helpers.bulk(c, ({"_index": "products", "_id": p["product_id"],
                                   "_source": {k: p[k] for k in ("name", "description", "category", "brand", "price", "rating")}}
                                  for p in ds.products))
        n_s, _ = helpers.bulk(c, ({"_index": "stores", "_id": s["store_id"],
                                   "_source": {"name": s["name"], "city": s["city"], "location": {"lat": s["lat"], "lon": s["lon"]}}}
                                  for s in ds.stores))
        c.indices.refresh(index="products,stores")
        t.result(items=n_p + n_s)
    return [f"Indexed {n_p} products (tr_folded + standard analyzers).", f"Indexed {n_s} stores (geo_point)."]


def reset_visitors():
    return ["OpenSearch keeps no Visitor data."]


def status():
    return {"products": client().count(index="products")["count"], "stores": client().count(index="stores")["count"]}
