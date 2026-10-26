"""OpenSearch Service - text search + geospatial: fuzzy product search and nearby stores."""
import boto3
from opensearchpy import AWSV4SignerAuth, OpenSearch, RequestsHttpConnection, helpers

from ..base import Adapter, ReadResult, SeedResult, env, region

MODEL = """\
index products  { name: text (turkish analyzer), description: text, category: keyword, brand: keyword,
                  price: float, rating: float }
index stores    { name: text, city: keyword, location: geo_point }

Text fields are analyzed into an inverted index (tokens, stemming); geo_point enables distance queries."""

SEARCH = """GET products/_search
{ "query": { "multi_match": { "query": "kablosuz kulaklik", "fields": ["name^3", "description"],
                              "fuzziness": "AUTO" } },
  "size": 8 }"""

GEO = """GET stores/_search
{ "query": { "geo_distance": { "distance": "25km", "location": { "lat": 41.0082, "lon": 28.9784 } } },
  "sort": [ { "_geo_distance": { "location": { "lat": 41.0082, "lon": 28.9784 }, "order": "asc", "unit": "km" } } ] }"""


class OpenSearchAdapter(Adapter):
    engine_id = "opensearch"
    title = "Amazon OpenSearch Service"
    data_type = "Unstructured"
    category = "Text search + Geospatial"
    domain_slice = "ürün arama ve mağaza konumları"
    why = ("Serbest metin araması (yazım hatasına toleranslı, alaka sıralı), log analitiği ve coğrafi sorgular için. "
           "Ana veri deposu değil, arama indeksidir. CloudSearch yeni müşterilere kapalı; Keyspaces'te geo sorgu yok.")
    model = MODEL

    def __init__(self):
        creds = boto3.Session(region_name=region()).get_credentials()
        self.client = OpenSearch(hosts=[{"host": env("OS_HOST"), "port": 443}], http_auth=AWSV4SignerAuth(creds, region(), "es"),
                                 use_ssl=True, verify_certs=True, connection_class=RequestsHttpConnection, timeout=60)

    def seed(self, ds):
        for idx in ("products", "stores"):
            if self.client.indices.exists(index=idx):
                self.client.indices.delete(index=idx)
        self.client.indices.create(index="products", body={"mappings": {"properties": {
            "name": {"type": "text", "analyzer": "turkish"}, "description": {"type": "text", "analyzer": "turkish"},
            "category": {"type": "keyword"}, "brand": {"type": "keyword"}, "price": {"type": "float"},
            "rating": {"type": "float"}}}})
        self.client.indices.create(index="stores", body={"mappings": {"properties": {
            "name": {"type": "text"}, "city": {"type": "keyword"}, "location": {"type": "geo_point"}}}})
        n_p, _ = helpers.bulk(self.client, ({"_index": "products", "_id": p["product_id"],
                                             "_source": {k: p[k] for k in ("name", "description", "category", "brand", "price", "rating")}}
                                            for p in ds.products))
        n_s, _ = helpers.bulk(self.client, ({"_index": "stores", "_id": s["store_id"],
                                             "_source": {"name": s["name"], "city": s["city"],
                                                         "location": {"lat": s["lat"], "lon": s["lon"]}}}
                                            for s in ds.stores))
        self.client.indices.refresh(index="products,stores")
        return SeedResult(
            summary=["products ve stores indeksleri silindi ve yeniden oluşturuldu", f"{n_p} ürün indekslendi (turkish analyzer)",
                     f"{n_s} mağaza indekslendi (geo_point)"],
            operation="PUT products  { mappings: name/description text (turkish), category keyword, ... }\n"
                      "PUT stores    { mappings: location geo_point }\nPOST _bulk  { index: ... } ...",
            counts={"products": n_p, "stores": n_s})

    def read(self):
        hits = self.client.search(index="products", body={
            "query": {"multi_match": {"query": "kablosuz kulaklik", "fields": ["name^3", "description"], "fuzziness": "AUTO"}},
            "size": 8})["hits"]["hits"]
        rows = [("ürün", h["_id"], h["_source"]["name"], h["_source"]["category"], round(h["_score"], 2)) for h in hits]
        geo = self.client.search(index="stores", body={
            "query": {"geo_distance": {"distance": "25km", "location": {"lat": 41.0082, "lon": 28.9784}}},
            "sort": [{"_geo_distance": {"location": {"lat": 41.0082, "lon": 28.9784}, "order": "asc", "unit": "km"}}]})["hits"]["hits"]
        rows += [("mağaza", h["_id"], h["_source"]["name"], h["_source"]["city"], f"{h['sort'][0]:.1f} km") for h in geo]
        return ReadResult(["tip", "id", "name", "category / city", "score / distance"], rows, SEARCH + "\n\n" + GEO,
                          note="'kablosuz kulaklik' (ı yerine i) yazım hatasına rağmen bulunur: fuzziness. "
                               "Mağazalar İstanbul merkezine 25 km içindekiler, yakından uzağa.")


ADAPTER = OpenSearchAdapter
