"""Neptune - graph: "bought together" recommendations and the customer graph Report Screen."""
import json
from urllib.parse import urlencode

import boto3
import requests
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from flask import jsonify, request

from .. import trace
from ..base import env, region
from ..visitor import persona_id
from . import page

META = {
    "id": "neptune", "name": "Amazon Neptune", "data_type": "Semi-structured", "category": "Graph",
    "auth": "IAM role (SigV4, neptune-db)", "via": "Neptune cluster endpoint (data subnet, HTTPS 8182)",
    "section": "Recommendations",
    "model": "(:Customer {~id, name, city})-[:BOUGHT {order_id, qty}]->(:Product {~id, name, category})",
}
PAGES = [page("graph", "graph", "Customer graph", "/admin/graph")]

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
