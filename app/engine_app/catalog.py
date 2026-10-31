"""Engine descriptors and pages of all ten Engines. No database driver here, so every Engine App can import it.

The DocumentDB Engine App is the default ALB target. It renders the Home hub, the E2E tutorials and every page of the
Guided e-commerce app. The pages are shells: the browser calls each Engine App API (ADR-0002).
"""
ENGINE_IDS = ["docdb", "opensearch", "dynamodb", "aurora", "redshift", "elasticache", "keyspaces", "influxdb", "neptune", "s3"]


def page(pid, template, title, *paths):
    return {"id": pid, "template": template, "title": title, "paths": list(paths)}


META = {}
PAGES = {}

META["docdb"] = {
    "id": "docdb", "name": "Amazon DocumentDB", "data_type": "Semi-structured", "category": "Document",
    "auth": "Password (Secrets Manager)", "via": "DocumentDB cluster endpoint (data subnet, TLS 27017)",
    "section": "Catalog",
    "model": '{ "_id": "P0001", "name": "...", "category": "Elektronik", "price": 1299.9,\n'
             '  "attributes": { "renk": "siyah", "garanti_ay": 24 },  "tags": ["yeni"] }\n'
             "Indexes: { category: 1, rating: -1 }, { \"attributes.renk\": 1 }",
}
PAGES["docdb"] = [
    page("home", "home", "TDS Academy Market", "/"),
    page("category", "category", "Category", "/c/<category>"),
    page("product", "product", "Product", "/p/<pid>"),
    page("admin", "admin", "Admin Console", "/admin"),
]

META["opensearch"] = {
    "id": "opensearch", "name": "Amazon OpenSearch Service", "data_type": "Unstructured",
    "category": "Text search + Geospatial", "auth": "IAM role (SigV4)",
    "via": "OpenSearch VPC endpoint (data subnet, HTTPS 443)", "section": "Search and stores",
    "model": "index products: name (tr_folded) + name.std (standard), description, category (keyword), price, rating\n"
             "index stores:   name, city (keyword), location (geo_point)",
}
PAGES["opensearch"] = [page("search", "search", "Search", "/search"), page("stores", "stores", "Find a store", "/stores")]

META["dynamodb"] = {
    "id": "dynamodb", "name": "Amazon DynamoDB", "data_type": "Semi-structured", "category": "Key-value",
    "auth": "IAM role (SigV4)", "via": "S3/DynamoDB gateway endpoint → DynamoDB", "section": "Cart",
    "model": "Table dbws-cart\n  pk  CART#<visitor>        (partition key)\n  sk  ITEM#<product_id>     (sort key)\n"
             "  qty, name, unit_price, expires_at (TTL, 24 h)",
}
PAGES["dynamodb"] = [page("cart", "cart", "Your cart", "/cart")]

META["aurora"] = {
    "id": "aurora", "name": "Amazon Aurora PostgreSQL", "data_type": "Structured", "category": "Relational",
    "auth": "Password (Secrets Manager)", "via": "Aurora writer endpoint (data subnet, TLS 5432)",
    "section": "Checkout and orders",
    "model": "customers(customer_id PK, name, city, segment)\nproducts(product_id PK, name, category, price, stock CHECK >= 0)\n"
             "orders(order_id PK, customer_id FK, visitor_id, order_date, status, total)\n"
             "order_items(order_id FK, product_id FK, qty, unit_price, PK(order_id, product_id))",
}
PAGES["aurora"] = [page("checkout", "checkout", "Checkout", "/checkout"), page("orders", "orders", "My orders", "/orders"),
         page("order_report", "order_report", "Order report", "/admin/orders")]

META["redshift"] = {
    "id": "redshift", "name": "Amazon Redshift Serverless", "data_type": "Structured", "category": "Columnar",
    "auth": "Password (Secrets Manager)", "via": "Redshift Serverless workgroup endpoint (data subnet, TLS 5439)",
    "section": "Sales reports",
    "model": "dev.public.sales            history: DISTKEY customer_id, SORTKEY order_date\n"
             "aurora_live.public.*        live copy of the Aurora tables (zero-ETL integration)",
}
PAGES["redshift"] = [page("reports", "reports", "Sales reports", "/admin/reports")]

META["elasticache"] = {
    "id": "elasticache", "name": "Amazon ElastiCache (Valkey)", "data_type": "Semi-structured", "category": "In-memory",
    "auth": "Password (Secrets Manager, ACL user)", "via": "ElastiCache Serverless endpoint (data subnet, TLS 6379)",
    "section": "Flash deal and live data",
    "model": "lm:deal                 HASH   product, name, price, ends_at\nlm:deal:stock           STRING counter (DECR)\n"
             "lm:session:<visitor>    HASH   persona, last_page   (TTL)\nlm:leaderboard          ZSET   persona → revenue\n"
             "lm:orders:today         STRING counter (INCR)",
}
PAGES["elasticache"] = [page("deals", "deals", "Flash deal", "/deals"), page("live", "live", "Live leaderboard", "/admin/live")]

META["keyspaces"] = {
    "id": "keyspaces", "name": "Amazon Keyspaces", "data_type": "Semi-structured", "category": "Wide column",
    "auth": "IAM role (SigV4)", "via": "Keyspaces interface endpoint (data subnet ENI, TLS 9142)",
    "section": "Activity",
    "model": "CREATE TABLE dbws.activity_by_user (\n  user_id text, event_time timestamp, event_id uuid,\n"
             "  event_type text, product_id text, detail text,\n  PRIMARY KEY ((user_id), event_time, event_id)\n"
             ") WITH CLUSTERING ORDER BY (event_time DESC)   -- default TTL 7 days",
}
PAGES["keyspaces"] = [page("activity", "activity", "My activity", "/account/activity")]

META["influxdb"] = {
    "id": "influxdb", "name": "Amazon Timestream for InfluxDB", "data_type": "Semi-structured", "category": "Time-series",
    "auth": "Password (Secrets Manager)", "via": "InfluxDB endpoint (data subnet, HTTPS 8086)", "section": "Operations",
    "model": "bucket metrics\n  warehouse_env  tags: warehouse, sensor   field: value   every 5 minutes\n"
             "  orders         tags: channel              field: count   every minute",
}
PAGES["influxdb"] = [page("ops", "ops", "Operations", "/admin/ops")]

META["neptune"] = {
    "id": "neptune", "name": "Amazon Neptune", "data_type": "Semi-structured", "category": "Graph",
    "auth": "IAM role (SigV4, neptune-db)", "via": "Neptune cluster endpoint (data subnet, HTTPS 8182)",
    "section": "Recommendations",
    "model": "(:Customer {~id, name, city})-[:BOUGHT {order_id, qty}]->(:Product {~id, name, category})",
}
PAGES["neptune"] = [page("graph", "graph", "Customer graph", "/admin/graph")]

META["s3"] = {
    "id": "s3", "name": "Amazon S3", "data_type": "Unstructured", "category": "Blob", "auth": "IAM role (SigV4)",
    "via": "S3/DynamoDB gateway endpoint → S3", "section": "Seller panel and images",
    "model": "s3://<bucket>/products/<product_id>.jpg       Content-Type, x-amz-meta-name, -category, -author, -license\n"
             "s3://<bucket>/uploads/<visitor>/<file>        x-amz-meta-product-id   (versioning on)",
}
PAGES["s3"] = [page("seller", "seller", "Seller panel", "/seller")]
