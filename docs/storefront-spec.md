# Lale Market Storefront - specification

Agreed in the grilling session of 2026-10-26. Terms: see `GLOSSARY.md`. Decisions with trade-offs: `docs/adr/`.

## Sections and paths

The ALB default action forwards to the DocumentDB App, so `/` and unknown paths reach the catalog.

| Engine App | Storefront Section / Report Screen | Paths |
|---|---|---|
| DocumentDB | Home, category list, product page, Admin Console | `/`, `/c/<category>`, `/p/<product>`, `/admin` (default rule) |
| OpenSearch | Search with facets and typo tolerance, store finder map | `/search`, `/stores` |
| Neptune | "Bought together" on the product page; graph Report Screen | widget, `/admin/graph` |
| DynamoDB | Cart, mini-cart | `/cart` |
| Aurora | Checkout (ACID order + stock), order history, order Report Screen | `/checkout`, `/orders`, `/admin/orders` |
| ElastiCache | Flash sale, live leaderboard Report Screen | `/deals`, `/admin/live` |
| Keyspaces | Recently viewed strip, activity page | widget, `/account/activity` |
| S3 | Seller panel (image upload, gallery), product images | `/seller`, images |
| Redshift | Sales Report Screen (live through zero-ETL) | `/admin/reports` |
| InfluxDB | Operations Report Screen | `/admin/ops` |

Every Engine App also serves `/<engine>/api/*`, `/<engine>/static/*` and `/<engine>/health`.

## Teaching layer

- Every API response carries a `trace` list. The Behind-the-Scenes Panel shows each entry: Engine, operation, request text, parameters, duration, network path, authentication type, capacity and approximate cost when the Engine reports them.
- Tutorials and Experiments live in `app/engine_app/tutorials/<engine>.yaml`, written in ASD-STE100 English.
- A Guided shopping journey walks: home → search → product → cart → checkout → orders → reports.

## Data

- Shared Catalog: Seeded only from the Admin Console (`dbws/admin` secret).
- Visitor: cookie `lm_visitor` (random id) and `lm_persona` (one of six Customers).
- Personas: Ayşe Yılmaz (premium, İstanbul), Mert Doğan (corporate, Ankara), Elif Kaya (new, İzmir), Lukas Weber (books, Frankfurt), Zeynep Şahin (fashion, browses a lot), Can Demir (sports, deal hunter).
- Retention: cart 24 h (DynamoDB TTL), activity 7 days (Keyspaces TTL), orders until the Admin Console resets them.

## Scale and cost limits

- Load Simulation on DynamoDB, ElastiCache (flash sale) and Keyspaces.
- At most 2,000 requests per run, one run per Engine at a time, three runs per Visitor per hour. The Admin Console can turn it off.

## Infrastructure changes

- ALB rules for the paths above; default action forwards to DocumentDB.
- `dbws/admin` secret; every Engine App role may read it.
- DynamoDB TTL attribute `expires_at`; Keyspaces default TTL 7 days.
- Aurora → Redshift zero-ETL (ADR-0001).

## UI

- English, ASD-STE100. Lale Market brand, marketplace layout, dark code-style Behind-the-Scenes Panel on the right.
- Flask + Jinja + plain JS; vendored Chart.js, vis-network, Leaflet. Desktop first.
