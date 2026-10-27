"""Neptune - graph: "bought together" recommendations and the customer graph Report Screen."""
import json
from urllib.parse import urlencode

import boto3
import requests
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from flask import jsonify, request

from .. import catalog, trace
from ..base import env, region
from ..visitor import persona_id

META = catalog.META["neptune"]
PAGES = catalog.PAGES["neptune"]

BY_PRODUCT = """MATCH (p:Product {`~id`: $pid})<-[:BOUGHT]-(c:Customer)-[:BOUGHT]->(rec:Product)
WHERE rec <> p
RETURN rec.`~id` AS product_id, rec.name AS name, rec.category AS category, count(DISTINCT c) AS score
ORDER BY score DESC, product_id LIMIT 6"""
BY_PERSONA = """MATCH (me:Customer {`~id`: $cid})-[:BOUGHT]->(:Product)<-[:BOUGHT]-(o:Customer)-[:BOUGHT]->(rec:Product)
WHERE o <> me AND NOT (me)-[:BOUGHT]->(rec)
RETURN rec.`~id` AS product_id, rec.name AS name, rec.category AS category, count(DISTINCT o) AS score
ORDER BY score DESC, product_id LIMIT 6"""


def _q(query, params=None):
    url = f"https://{env('NEPTUNE_HOST')}:{env('NEPTUNE_PORT', '8182')}/openCypher"
    body = {"query": query}
    if params is not None:
        body["parameters"] = json.dumps(params)
    req = AWSRequest(method="POST", url=url, data=urlencode(body), headers={"Content-Type": "application/x-www-form-urlencoded"})
    SigV4Auth(boto3.Session(region_name=region()).get_credentials().get_frozen_credentials(), "neptune-db", region()).add_auth(req)
    resp = requests.post(url, data=req.body, headers=dict(req.headers), timeout=60)
    if resp.status_code != 200:
        raise RuntimeError(f"Neptune {resp.status_code}: {resp.text[:300]}")
    return resp.json()["results"]


def register(bp):
    @bp.get("/api/recs")
    def api_recs():
        mode = request.args.get("mode", "product")
        if mode == "persona":
            params, query = {"cid": persona_id()}, BY_PERSONA
            note = "3 hops: your purchases → customers with the same purchases → what they bought. Personal, but it needs history."
        else:
            params, query = {"pid": request.args.get("product", "P0001")}, BY_PRODUCT
            note = "2 hops: this product → customers who bought it → their other products. It works for every Visitor."
        with trace.call("openCypher", f"POST /openCypher\n{query}", params) as t:
            rows = _q(query, params)
            t.result(items=len(rows), note=note + " In SQL each hop is one more JOIN on a large table.")
        return jsonify(trace.payload(rows))

    @bp.get("/api/graph")
    def api_graph():
        cid = request.args.get("persona") or persona_id()
        query = """MATCH (me:Customer {`~id`: $cid})-[:BOUGHT]->(p:Product)
OPTIONAL MATCH (p)<-[:BOUGHT]-(o:Customer) WHERE o <> me
WITH me, p, collect(DISTINCT o)[0..3] AS others
RETURN me.name AS me, p.`~id` AS pid, p.name AS pname, p.category AS cat,
       [x IN others | {id: x.`~id`, name: x.name}] AS others LIMIT 12"""
        with trace.call("openCypher", f"POST /openCypher\n{query}", {"cid": cid}) as t:
            rows = _q(query, {"cid": cid})
            t.result(items=len(rows), note="The Report Screen draws the neighbourhood of one customer: products and other buyers.")
        nodes, edges, seen = [{"id": cid, "label": rows[0]["me"] if rows else cid, "group": "me"}], [], {cid}
        for r in rows:
            if r["pid"] not in seen:
                nodes.append({"id": r["pid"], "label": r["pname"], "group": r["cat"]})
                seen.add(r["pid"])
            edges.append({"from": cid, "to": r["pid"]})
            for o in r["others"] or []:
                if o["id"] not in seen:
                    nodes.append({"id": o["id"], "label": o["name"], "group": "customer"})
                    seen.add(o["id"])
                edges.append({"from": o["id"], "to": r["pid"]})
        return jsonify(trace.payload({"nodes": nodes, "edges": edges}))

    @bp.post("/api/purchase")
    def api_purchase():
        body = request.get_json(force=True)
        rows = [{"c": persona_id(), "p": pid, "o": body.get("order_id", "web")} for pid in body.get("products", [])]
        query = "UNWIND $rows AS r MATCH (c {`~id`: r.c}) MATCH (p {`~id`: r.p}) CREATE (c)-[:BOUGHT {order_id: r.o, qty: 1}]->(p)"
        with trace.call("openCypher (write)", f"POST /openCypher\n{query}", {"edges": len(rows)}) as t:
            _q(query, {"rows": rows})
            t.result(items=len(rows), note="New BOUGHT edges change the next recommendation at once. There is no batch rebuild.")
        return jsonify(trace.payload({"edges": len(rows)}))


def seed(ds):
    with trace.call("openCypher (bulk)", "MATCH (n) DETACH DELETE n; UNWIND $rows CREATE ...", {}) as t:
        _q("MATCH (n) DETACH DELETE n")
        _q("UNWIND $rows AS r CREATE (:Customer {`~id`: r.id, name: r.name, city: r.city})",
           {"rows": [{"id": c["customer_id"], "name": c["name"], "city": c["city"]} for c in ds.customers]})
        _q("UNWIND $rows AS r CREATE (:Product {`~id`: r.id, name: r.name, category: r.category})",
           {"rows": [{"id": p["product_id"], "name": p["name"], "category": p["category"]} for p in ds.products]})
        edges = [{"c": o["customer_id"], "p": i["product_id"], "o": o["order_id"], "q": i["qty"]}
                 for o in ds.orders if o["status"] != "cancelled" for i in o["items"]]
        for k in range(0, len(edges), 500):
            _q("UNWIND $rows AS r MATCH (c {`~id`: r.c}) MATCH (p {`~id`: r.p}) CREATE (c)-[:BOUGHT {order_id: r.o, qty: r.q}]->(p)",
               {"rows": edges[k:k + 500]})
        t.result(items=len(edges))
    return [f"Created {len(ds.customers)} Customer and {len(ds.products)} Product vertices.", f"Created {len(edges)} BOUGHT edges."]


def reset_visitors():
    with trace.call("openCypher", "MATCH ()-[b:BOUGHT]->() WHERE b.order_id STARTS WITH 'W' DELETE b", {}) as t:
        _q("MATCH ()-[b:BOUGHT]->() WHERE b.order_id STARTS WITH 'W' DELETE b")
        t.result()
    return ["Deleted the BOUGHT edges that Visitors created."]


def status():
    r = _q("MATCH (n) RETURN count(n) AS vertices")
    return {"vertices": r[0]["vertices"] if r else 0}


def learn_overview(lesson, focus):
    """101: every Product node by category, and some Customer nodes (the persona first). `focus` marks the nodes of the call."""
    f = set(focus) | {persona_id()}
    q = "MATCH (p:Product) RETURN p.`~id` AS id, p.name AS name, p.category AS category ORDER BY id"
    with trace.call("openCypher", f"POST /openCypher\n{q}", {}) as t:
        products = _q(q)
        t.result(items=len(products))
    q2 = "MATCH (c:Customer) RETURN c.`~id` AS id, c.name AS name ORDER BY id LIMIT 60"
    with trace.call("openCypher", f"POST /openCypher\n{q2}", {}) as t:
        customers = _q(q2)
        t.result(items=len(customers))
    q3 = "MATCH ()-[b:BOUGHT]->() RETURN count(b) AS edges"
    with trace.call("openCypher", f"POST /openCypher\n{q3}", {}) as t:
        edges = _q(q3)[0]["edges"]
        t.result(items=1)
    cats = sorted({p["category"] for p in products})
    return {"title": "Neptune: the customer and product graph", "text": "Each square is one vertex (node). The products are on category shelves, and a sample of customers is at the bottom.",
            "facts": [[len(products), "Product vertices"], [edges, "BOUGHT edges"], [len([x for x in products + customers if x["id"] in f]), "vertices in your call"]],
            "groups": [{"label": c, "items": [{"id": p["id"], "title": f"{p['id']}: {p['name']}", "hit": p["id"] in f}
                                              for p in products if p["category"] == c]} for c in cats]
                      + [{"label": "Customers", "items": [{"id": x["id"], "title": f"{x['id']}: {x['name']}", "hit": x["id"] in f}
                                                          for x in sorted(customers, key=lambda x: x["id"] not in f)]}],
            "hit_label": "The vertices that your call touched (and your persona)"}


def learn_item(lesson, node_id):
    if node_id.startswith("C"):
        q = """MATCH (c:Customer {`~id`: $id}) OPTIONAL MATCH (c)-[b:BOUGHT]->(p:Product)
RETURN c.name AS name, c.city AS city, collect({product: p.`~id`, name: p.name, order_id: b.order_id})[0..10] AS bought, count(b) AS n"""
        with trace.call("openCypher", f"POST /openCypher\n{q}", {"id": node_id}) as t:
            rows = _q(q, {"id": node_id})
            t.result(items=len(rows))
        r0 = rows[0] if rows else {}
        rec = {"~id": node_id, "~label": "Customer", "name": r0.get("name"), "city": r0.get("city"),
               f"BOUGHT edges (outgoing, {r0.get('n', 0)}, first 10)": [{"→ Product": b["product"], "name": b["name"], "order_id": b["order_id"]}
                                                                          for b in r0.get("bought") or [] if b.get("product")]}
        return {"title": r0.get("name") or node_id, "sub": "A Customer vertex and its outgoing BOUGHT edges. An edge is a record too: it holds an order_id.",
                "record": rec, "marks": {"~id": "kept", "~label": "kept"}}
    q = """MATCH (p:Product {`~id`: $id}) OPTIONAL MATCH (p)<-[b:BOUGHT]-(c:Customer)
WITH p, collect(DISTINCT {id: c.`~id`, name: c.name})[0..5] AS buyers, count(b) AS n
OPTIONAL MATCH (p)<-[:BOUGHT]-(:Customer)-[:BOUGHT]->(o:Product) WHERE o <> p
RETURN p.name AS name, p.category AS category, buyers, n, o.`~id` AS other, o.name AS other_name, count(*) AS score
ORDER BY score DESC LIMIT 5"""
    with trace.call("openCypher", f"POST /openCypher\n{q}", {"id": node_id}) as t:
        rows = _q(q, {"id": node_id})
        t.result(items=len(rows))
    r0 = rows[0] if rows else {}
    rec = {"~id": node_id, "~label": "Product", "name": r0.get("name"), "category": r0.get("category"),
           f"BOUGHT edges (incoming, {r0.get('n', 0)}), first 5 customers": [{"← Customer": b["id"], "name": b["name"]} for b in r0.get("buyers") or [] if b.get("id")],
           "2 hops away: bought together": [{"Product": x["other"], "name": x["other_name"], "shared customers": x["score"]} for x in rows if x.get("other")]}
    return {"title": r0.get("name") or node_id, "sub": "A Product vertex, its incoming edges and the products two hops away (the recommendation comes from this path).",
            "record": rec, "marks": {"~id": "kept", "~label": "kept", "2 hops away: bought together": "kept"}}
