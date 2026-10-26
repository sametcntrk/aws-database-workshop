"""Neptune - graph: customers BOUGHT products; "bought together" recommendations with openCypher."""
import json
from urllib.parse import urlencode

import boto3
import requests
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest

from ..base import Adapter, ReadResult, SeedResult, env, region

MODEL = """\
(:Customer {id, name, city})-[:BOUGHT {order_id, qty}]->(:Product {id, name, category})

The relationship is stored as an edge, so "who else bought this" is a traversal, not a JOIN:
(me)-[:BOUGHT]->(p)<-[:BOUGHT]-(other)-[:BOUGHT]->(rec)"""

READ = """\
MATCH (me:Customer {`~id`: 'C00001'})-[:BOUGHT]->(p:Product)<-[:BOUGHT]-(other:Customer)-[:BOUGHT]->(rec:Product)
WHERE other <> me AND NOT (me)-[:BOUGHT]->(rec)
RETURN rec.id AS product_id, rec.name AS name, rec.category AS category,
       count(DISTINCT other) AS customers_in_common
ORDER BY customers_in_common DESC, product_id
LIMIT 10"""


class Neptune(Adapter):
    engine_id = "neptune"
    title = "Amazon Neptune"
    data_type = "Semi-structured"
    category = "Graph"
    domain_slice = "birlikte satın alınanlar grafı"
    why = ("İlişkinin kendisinin veri olduğu durumlar için: öneri, sosyal ağ, dolandırıcılık tespiti, bilgi grafı. "
           "Çok adımlı ilişki gezinmesi (traversal) indeksli kenarlarla yapılır; ilişkisel modelde her adım bir JOIN olurdu.")
    model = MODEL

    def __init__(self):
        self.url = f"https://{env('NEPTUNE_HOST')}:{env('NEPTUNE_PORT', '8182')}/openCypher"
        self.session = boto3.Session(region_name=region())

    def _q(self, query, params=None):
        body = {"query": query}
        if params is not None:
            body["parameters"] = json.dumps(params)
        req = AWSRequest(method="POST", url=self.url, data=urlencode(body),
                         headers={"Content-Type": "application/x-www-form-urlencoded"})
        SigV4Auth(self.session.get_credentials().get_frozen_credentials(), "neptune-db", region()).add_auth(req)
        resp = requests.post(self.url, data=req.body, headers=dict(req.headers), timeout=120)
        if resp.status_code != 200:
            raise RuntimeError(f"Neptune {resp.status_code}: {resp.text[:400]}")
        return resp.json()["results"]

    def seed(self, ds):
        self._q("MATCH (n) DETACH DELETE n")
        # explicit vertex IDs (~id): edges are then created by ID lookup, the fastest access path in Neptune
        self._q("UNWIND $rows AS r CREATE (:Customer {`~id`: r.id, id: r.id, name: r.name, city: r.city})",
                {"rows": [{"id": c["customer_id"], "name": c["name"], "city": c["city"]} for c in ds.customers]})
        self._q("UNWIND $rows AS r CREATE (:Product {`~id`: r.id, id: r.id, name: r.name, category: r.category})",
                {"rows": [{"id": p["product_id"], "name": p["name"], "category": p["category"]} for p in ds.products]})
        edges = [{"c": o["customer_id"], "p": i["product_id"], "o": o["order_id"], "q": i["qty"]}
                 for o in ds.orders if o["status"] != "cancelled" for i in o["items"]]
        for k in range(0, len(edges), 500):
            self._q("UNWIND $rows AS r MATCH (c {`~id`: r.c}) MATCH (p {`~id`: r.p}) "
                    "CREATE (c)-[:BOUGHT {order_id: r.o, qty: r.q}]->(p)", {"rows": edges[k:k + 500]})
        return SeedResult(
            summary=["Graf temizlendi (MATCH (n) DETACH DELETE n)", f"{len(ds.customers)} Customer, {len(ds.products)} Product düğümü",
                     f"{len(edges)} BOUGHT kenarı (500'lük UNWIND grupları, ~id ile eşleşme)"],
            operation="UNWIND $rows AS r CREATE (:Customer {`~id`: r.id, id: r.id, name: r.name, city: r.city})\n"
                      "UNWIND $rows AS r MATCH (c {`~id`: r.c}) MATCH (p {`~id`: r.p})\n"
                      "  CREATE (c)-[:BOUGHT {order_id: r.o, qty: r.q}]->(p)\n"
                      "-- HTTPS POST /openCypher, IAM SigV4 (neptune-db)",
            counts={"customers": len(ds.customers), "products": len(ds.products), "edges": len(edges)})

    def read(self):
        res = self._q(READ)
        cols = ["product_id", "name", "category", "customers_in_common"]
        return ReadResult(cols, [[r[c] for c in cols] for r in res], READ,
                          note="3 adımlık gezinme: C00001'in aldıkları → onları alan diğer müşteriler → onların aldıkları.")


ADAPTER = Neptune
