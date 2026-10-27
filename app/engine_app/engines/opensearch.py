"""OpenSearch Service - text search with facets and typo tolerance, and the store finder (geo_point)."""
import boto3
from flask import jsonify, request
from opensearchpy import AWSV4SignerAuth, OpenSearch, RequestsHttpConnection, helpers

from .. import catalog, trace
from ..base import env, region
from . import table as result_table

META = catalog.META["opensearch"]
PAGES = catalog.PAGES["opensearch"]

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


    @bp.post("/api/learn/analyze")
    def api_learn_analyze():
        """101 lesson: the tokens that each analyzer makes from a text (the same analyzers as the products index)."""
        texts = [str(t)[:200] for t in (request.get_json(silent=True) or {}).get("texts", [])][:6]
        out = []
        with trace.call("_analyze", "POST products/_analyze { analyzer: tr_folded | standard, text }", {"texts": len(texts)}) as t:
            for text in texts:
                row = {"text": text}
                for key, analyzer in (("folded", "tr_folded"), ("standard", "standard")):
                    r = client().indices.analyze(index="products", body={"analyzer": analyzer, "text": text})
                    row[key] = [tok["token"] for tok in r["tokens"]]
                out.append(row)
            t.result(items=len(out))
        return jsonify(trace.payload(out))

    @bp.get("/api/learn/index")
    def api_learn_index():
        """101 lesson: the big picture of the products index (every document id, name and category, and index facts)."""
        with trace.call("_search (match_all) + _stats", "GET products/_search { match_all, _source: [name, category] }; GET products/_stats", {}) as t:
            r = client().search(index="products", body={"query": {"match_all": {}}, "size": 1000, "_source": ["name", "category"],
                                                        "sort": [{"_doc": "asc"}]})
            stats = client().indices.stats(index="products")["indices"]["products"]["primaries"]
            settings = client().indices.get_settings(index="products")["products"]["settings"]["index"]
            t.result(items=len(r["hits"]["hits"]))
        return jsonify(trace.payload({
            "index": "products", "count": stats["docs"]["count"], "size_bytes": stats["store"]["size_in_bytes"],
            "shards": int(settings.get("number_of_shards", 1)), "replicas": int(settings.get("number_of_replicas", 0)),
            "items": [{"id": h["_id"], "name": h["_source"]["name"], "category": h["_source"]["category"]} for h in r["hits"]["hits"]]}))

    @bp.post("/api/learn/postings")
    def api_learn_postings():
        """101 lesson: one row of the inverted index per token: how many products have the token in `name`, and some of them."""
        tokens = [str(t)[:60] for t in (request.get_json(silent=True) or {}).get("tokens", [])][:6]
        out = []
        with trace.call("_search (term)", "GET products/_search { query: { term: { name: <token> } } }", {"tokens": len(tokens)}) as t:
            for tok in tokens:
                r = client().search(index="products", body={"query": {"term": {"name": tok}}, "size": 4, "_source": ["name"],
                                                            "track_total_hits": True})
                out.append({"token": tok, "count": r["hits"]["total"]["value"],
                            "sample": [{"product_id": h["_id"], "name": h["_source"]["name"]} for h in r["hits"]["hits"]]})
            t.result(items=len(out))
        return jsonify(trace.payload(out))


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


def learn_overview(lesson, focus):
    """101 for the suggest and geo lessons: the products or stores index as tiles; `focus` = the ids that the call returned."""
    f = set(focus)
    index = "stores" if lesson == "geo" else "products"
    group_field = "city" if index == "stores" else "category"
    with trace.call("_search (match_all)", f"GET {index}/_search {{ match_all, size: 1000 }}", {}) as t:
        r = client().search(index=index, body={"query": {"match_all": {}}, "size": 1000, "_source": ["name", group_field]})
        t.result(items=len(r["hits"]["hits"]))
    docs = [(h["_id"], h["_source"]) for h in r["hits"]["hits"]]
    groups = sorted({d[group_field] for _, d in docs})
    return {"title": f"OpenSearch: the {index} index", "text": "Each square is one document. " + ("The shelves are cities." if index == "stores" else "The shelves are categories."),
            "facts": [[len(docs), "documents"], [len(groups), "cities" if index == "stores" else "categories"], [len(f & {i for i, _ in docs}), "documents in your result"]],
            "groups": [{"label": g, "items": [{"id": i, "title": f"{i}: {d['name']}", "hit": i in f} for i, d in sorted(docs) if d[group_field] == g]}
                       for g in groups],
            "hit_label": "The documents that your call returned"}


def learn_item(lesson, doc_id):
    index = "stores" if lesson == "geo" else "products"
    with trace.call("GET _doc", f"GET {index}/_doc/{doc_id}", {}) as t:
        d = client().get(index=index, id=doc_id)
        t.result(items=1)
    rec = {"_index": d["_index"], "_id": d["_id"], "_source": d["_source"]}
    marks = {"_source.location": "kept"} if index == "stores" else {"_source.name": "kept"}
    sub = ("A store document. The location field is a geo_point: OpenSearch indexes the latitude and longitude in a map grid." if index == "stores"
           else "The document in OpenSearch. The name field is split into words, and it also supports prefix search for suggestions while you type.")
    return {"title": d["_source"].get("name", doc_id), "sub": sub, "record": rec, "marks": marks}


# ---------------------------------------------------------------- E2E tutorial queries (templates/e2e/opensearch.html)
def _search(op, index, body, note=None):
    with trace.call(op, f"GET {index}/_search\n{_show(body)}", {}) as t:
        r = client().search(index=index, body=body)
        t.result(items=r["hits"]["total"]["value"], note=f"OpenSearch took {r['took']} ms.")
    return r


def _e2e_analyze():
    text = "Alpen Kablosuz Kulaklık 1"
    rows = []
    with trace.call("_analyze", f"POST products/_analyze {{ analyzer: tr_folded | standard, text: '{text}' }}", {}) as t:
        for analyzer in ("tr_folded", "standard"):
            toks = client().indices.analyze(index="products", body={"analyzer": analyzer, "text": text})["tokens"]
            rows.append([analyzer, " | ".join(tok["token"] for tok in toks), len(toks)])
        t.result(items=2)
    return result_table(["analyzer", "tokens", "count"], rows, note=f"Input text: {text}")


def _e2e_postings():
    rows = []
    for field, tok in (("name", "kablosuz"), ("name", "kulaklik"), ("name", "kulaklık"), ("name.std", "kulaklık"), ("name.std", "kulaklik"), ("name", "alpen")):
        body = {"query": {"term": {field: tok}}, "size": 5, "_source": False, "track_total_hits": True}
        r = _search("_search (term)", "products", body)
        rows.append([field, tok, r["hits"]["total"]["value"], ", ".join(h["_id"] for h in r["hits"]["hits"])])
    return result_table(["field", "token", "documents", "first ids (the posting list)"], rows,
                        note="A term query looks up one token in the inverted index of one field, with no analysis.")


def _e2e_match():
    body = {"query": {"match": {"name": "kablosuz kulaklik"}}, "size": 6, "_source": ["name", "category"]}
    r = _search("_search (match)", "products", body)
    return result_table(["_id", "name", "category", "_score"], [[h["_id"], h["_source"]["name"], h["_source"]["category"], round(h["_score"], 3)]
                                                                 for h in r["hits"]["hits"]], total=r["hits"]["total"]["value"])


def _e2e_fuzzy():
    rows = []
    for fuzz in ("AUTO", None):
        m = {"query": "kulaklk"}
        if fuzz:
            m["fuzziness"] = fuzz
        r = _search("_search (match)", "products", {"query": {"match": {"name": m}}, "size": 3, "_source": ["name"]})
        rows.append([fuzz or "off", r["hits"]["total"]["value"], ", ".join(h["_source"]["name"] for h in r["hits"]["hits"])])
    return result_table(["fuzziness", "hits", "first names"], rows, note='"kulaklk" is one edit (a missing letter) away from "kulaklik".')


def _e2e_facets():
    body = {"size": 3, "_source": ["name", "price"],
            "query": {"bool": {"must": [{"match": {"description": "hafif"}}],
                               "filter": [{"range": {"price": {"lte": 2000}}}]}},
            "aggs": {"categories": {"terms": {"field": "category"}},
                     "price": {"range": {"field": "price", "ranges": [{"to": 500}, {"from": 500, "to": 1000}, {"from": 1000}]}}}}
    r = _search("_search (bool + aggs)", "products", body)
    rows = [["category", b["key"], b["doc_count"]] for b in r["aggregations"]["categories"]["buckets"]]
    rows += [["price range", b["key"], b["doc_count"]] for b in r["aggregations"]["price"]["buckets"]]
    return result_table(["aggregation", "bucket", "documents"], rows, total=r["hits"]["total"]["value"],
                        note=f'{r["hits"]["total"]["value"]} products match. The buckets count them in the same request.')


def _e2e_explain():
    body = {"query": {"match": {"name": "kablosuz kulaklik"}}, "size": 1, "explain": True, "_source": ["name"]}
    r = _search("_search (explain)", "products", body)
    h = r["hits"]["hits"][0]
    rows = []

    def walk(node, depth):
        if depth > 3:
            return
        rows.append([depth, round(node["value"], 4), node["description"][:140]])
        for d in node.get("details", [])[:4]:
            walk(d, depth + 1)
    walk(h["_explanation"], 0)
    return result_table(["depth", "value", "description"], rows, note=f'Why {h["_source"]["name"]} has score {round(h["_score"], 3)}.')


def _e2e_geo():
    body = {"query": {"geo_distance": {"distance": "25km", "location": {"lat": 41.0082, "lon": 28.9784}}},
            "sort": [{"_geo_distance": {"location": {"lat": 41.0082, "lon": 28.9784}, "order": "asc", "unit": "km"}}], "size": 10}
    r = _search("_search (geo_distance)", "stores", body)
    return result_table(["_id", "name", "city", "location", "distance_km"],
                        [[h["_id"], h["_source"]["name"], h["_source"]["city"], h["_source"]["location"], round(h["sort"][0], 2)] for h in r["hits"]["hits"]])


def _e2e_mapping():
    with trace.call("GET _mapping + _settings", "GET products/_mapping; GET products/_settings", {}) as t:
        props = client().indices.get_mapping(index="products")["products"]["mappings"]["properties"]
        st = client().indices.get_settings(index="products")["products"]["settings"]["index"]
        t.result()
    rows = [[f, p.get("type"), p.get("analyzer", ""), ", ".join(f"{k} ({v.get('analyzer', v.get('type'))})" for k, v in p.get("fields", {}).items())]
            for f, p in props.items()]
    return result_table(["field", "type", "analyzer", "sub-fields"], rows,
                        note=f"Index products: {st.get('number_of_shards')} primary shard(s), {st.get('number_of_replicas')} replica(s) of each.")


E2E = {"O1": _e2e_analyze, "O2": _e2e_postings, "O3": _e2e_match, "O4": _e2e_fuzzy, "O5": _e2e_facets, "O6": _e2e_explain,
       "O7": _e2e_geo, "O8": _e2e_mapping}
