# Scope: Amazon DocumentDB (with MongoDB compatibility) (docdb)

status: verified domain-map row, regenerated in model 2 (weighted R1 "Engine uyumu")
domain-map row: verified
date: 2026-10-31 (model 2); first version 2026-10-29 (model 1)

Page: `app/engine_app/templates/e2e/docdb.tr.html` (Turkish only; the old English `docdb.html` stays untouched and still renders the model 1 data). Data: `DOCDB_W` at the end of `app/engine_app/e2e_usecases_w.py` (model 2, sources in the comment block above it), registered as `USECASES_W["docdb"]` and `PAGE_SVC["docdb"] = "doc"`; new entries `CATEGORY["doce"]`, `LINK["doce"]` (DocumentDB elastic cluster, the twin) and `SVC["doce"]` in `e2e_sims.py`. Simulations: `docdb()` in `app/engine_app/e2e_sims.py` adds `weighted_scorecard` for the five cards with a `sim` when `lang == "tr"` (`w_catalog`, `w_profiles`, `w_events`, `w_search`, `w_sessions`); the mechanism simulations `scan`, `index`, `pipeline`, `update` are unchanged. Kept for the English page: `DOCDB_USECASES` (model 1), `decide_*`, and the model 1 scorecards. Check: `check_usecases.py --app <abs app> docdb`.

## Part A topic and the everyday picture (A1)

- Category in one general term: the document database (JSON documents, nested fields, arrays)
- Everyday picture: an insurance office with one folder per customer; the defter (ledger) set of a relational database as the contrast
- The trade (what it gives, what it takes): a whole object in one record and one read / shared facts are copied or need a second read; every record carries its own fields / the database does not validate the inside, most rules live in the application; queries on any field, nested and array fields / fast answers need an index, otherwise every document is read; one atomic write changes a part of a document / several documents need a transaction, all writes go through one primary

## Feature list Ö1–Ö8 (F1–F8 of the domain map)

| No | Feature | Defining section | Official sentence (URL) | Limit |
|---|---|---|---|---|
| Ö1 | Document by `_id` | A2 | `_id` required and unique; DocumentDB "Writes … are atomic within a single document" (https://docs.aws.amazon.com/documentdb/latest/developerguide/how-it-works.html) | shared parts are copied or referenced |
| Ö2 | Nested fields and arrays in one record | A2, A3 | Document size 16 MiB, nesting 200 levels (https://docs.aws.amazon.com/documentdb/latest/developerguide/limits.html); MongoDB nesting 100 levels; embedding vs references (https://www.mongodb.com/docs/manual/data-modeling/concepts/embedding-vs-references/) | unbounded arrays cannot be embedded; no validation unless `$jsonSchema` |
| Ö3 | Query by any field (filters) | A4 | Supported MongoDB APIs (https://docs.aws.amazon.com/documentdb/latest/developerguide/mongo-apis.html) | no typo-tolerant relevance search; joins limited (`$lookup`) |
| Ö4 | Indexes on fields and arrays (multikey) | A5 | single field, compound, multikey, sparse, partial, TTL, text, vector; 64 indexes per collection, 32 keys per compound (indexes-multikey.html, limits.html) | each index costs on every write; compound order matters |
| Ö5 | Partial updates (`$set`, `arrayFilters`) | A6 | MongoDB "write operations are atomic on the single-document level" (https://www.mongodb.com/docs/manual/core/write-operations-atomicity/); DocumentDB transactions 4.0+, one minute limit (https://docs.aws.amazon.com/documentdb/latest/developerguide/transactions.html) | atomic per document only; updateMany not atomic as a whole |
| Ö6 | Aggregation pipeline | A7 | stage support per version 3.6/4.0/5.0/8.0 (mongo-apis.html) | some stages only in 8.0.2+, some not at all |
| Ö7 | Change streams | A8 | retention default three hours, "between 1 hour and 7 days" (https://docs.aws.amazon.com/documentdb/latest/developerguide/change_streams.html) | not on elastic clusters; consumer is the team's part |
| Ö8 | Replicas for reads | A9 | one primary, up to 15 replicas, replica lag "usually less than 100 milliseconds"; failover "up to 30 seconds … often less" (how-it-works.html, https://docs.aws.amazon.com/whitepapers/latest/get-started-documentdb/amazon-documentdb-architecture.html) | all writes through one primary; elastic clusters for write scale |

## All cases per concept

| Section | Concept | Cases (including the impossible one) |
|---|---|---|
| A2 | shape of documents in a collection | same fields; different fields; missing field; null value; same field different type; validation schema; foreign document existence (cannot); size over 16 MiB (cannot) |
| A2 | `_id` | given by app; generated ObjectId; duplicate (refused); 1 vs "1"; embedded document `_id`; array `_id` (cannot); change `_id` (cannot) |
| A3 | array elements | scalars; embedded documents; empty; nested arrays; change one element; unbounded growth (cannot) |
| A3 | embed or reference | one owner small; snapshot copy; shared and changing; shared never changing; hundreds (separate + embed newest); unbounded (cannot embed); many-to-many |
| A4 | what a filter can ask | top field; nested field; array element; range; `$in`; `$or`; `$exists`; `$elemMatch`; sort and paging; typo-tolerant relevance (no); join by filter (no); field without index (COLLSCAN) |
| A5 | index forms; a query and an index | single, compound, multikey, embedded, unique, TTL; full prefix; prefix + range; second field only (no); field without index (no); middle-of-text regex (no); tiny collection |
| A6 | write paths | insert; replace; `$set`; `$inc`; `$push`/`$pull`; `arrayFilters`; version condition; upsert; updateMany (not atomic as a whole); transaction (time-limited); rule in another collection (cannot) |
| A7 | pipeline stages | `$match` first; `$unwind`; `$group`; sort/limit/project; `$lookup`; stage missing in version (does not work); multi-year report |
| A8 | what goes into the change stream | insert; update; replace; delete; read (nothing); consumer paused; duplicate processing; paused longer than retention (lost) |
| A9 | failure, copies and writes | replica down; primary down with/without replica; failover mid-write; AZ down; read-after-write on replica; second writer (cannot); sharding; wrong delete (replica is not a backup) |
| A10 | MongoDB code on DocumentDB | standard CRUD; supported operator; only newer version (does not work); not supported at all; driver default (retryable writes); explain output |
| C2 | which job to which endpoint | writes; catalog reads; read-your-write; long report; failover with an open connection |

## Anatomy list and colors

- Core data structures: document, field, embedded document, array, `_id`, index (and in Part B: BSON, ObjectId)
- Colors (document anatomies only, `.docanat` block added to `site.css`): `_id` yellow, embedded document blue, array green, plain field grey; stated in the A2 anatomy lead

## Matrix products (A10)

MongoDB, Amazon DocumentDB, DynamoDB

## Use cases (M2), model 2: candidates, totals, simulations

| No | Use case | Candidates (best fit first) | Totals | R1 subtotals | sim |
|---|---|---|---|---|---|
| 1 | Product catalog with variable attributes (Lale Market) | DocumentDB, Aurora PostgreSQL, OpenSearch | 93,3 · 81,8 · 71,8 | 54,2 / 42,7 / 40,7 of 55 | w_catalog |
| 2 | User profiles with nested preferences | DocumentDB, DynamoDB, Aurora PostgreSQL | 88,2 · 82,6 · 73,2 | 36,8 / 28,4 / 28,4 of 38 | w_profiles |
| 3 | Content management: articles and blocks | DocumentDB, DynamoDB, Aurora PostgreSQL | 92,4 · 79,2 · 79,2 | 42,8 / 31,8 / 34,2 of 46 | |
| 4 | Event logs with flexible schema | DynamoDB, DocumentDB elastic cluster, DocumentDB | 85,9 · 82,2 · 66,2 (close race) | 46,4 / 45,2 / 45,2 of 50 | w_events |
| 5 | IoT device registry and configuration | DocumentDB, DynamoDB, Aurora PostgreSQL | 90,6 · 83,6 · 76,2 | 44,6 / 36,0 / 35,0 of 46 | |
| 6 | Mobile app sync: list documents | DocumentDB, DynamoDB, DocumentDB elastic cluster | 89,4 · 83,8 · 82,2 | 42,8 / 35,4 / 42,8 of 44 | |
| 7 | Order documents: read model next to Aurora | DocumentDB, Aurora PostgreSQL, DynamoDB | 92,8 · 82,6 · 80,2 | 46,0 / 38,8 / 37,8 of 46 | |
| 8 | Catalog search by nested fields (filters, facets) | DocumentDB, OpenSearch, Aurora PostgreSQL | 77,6 · 76,8 · 68,0 (close race) | 30,4 / 40,8 / 31,0 of 42 | w_search |
| 9 | Session documents (quote wizard) | ElastiCache (Valkey), DynamoDB, DocumentDB | 85,2 · 79,2 · 64,0 | 41,0 / 32,4 / 32,8 of 46 | w_sessions |
| 10 | Feature flags and settings | DocumentDB, DynamoDB, Aurora PostgreSQL | 94,1 · 88,4 · 75,6 | 37,6 / 36,4 / 31,6 of 40 | |

DocumentDB is not the best fit in card 4 (DynamoDB; DocumentDB instance-based is third, a clear loss) and card 9 (ElastiCache; DocumentDB third). Another engine wins R1 but loses the total in card 8 (OpenSearch). Twins of one engine: DocumentDB instance-based and elastic cluster have the same R1 in cards 4 and 6; R2 (write scale) puts the elastic cluster second in card 4, R4 (no change streams) puts it third in card 6; the other cards say in the verdict why the twin is not a candidate. "Both together": card 1 and 8 (catalog in DocumentDB, search copy in OpenSearch), card 4 (Kinesis copy to the warehouse), card 5 (registry in DocumentDB, telemetry in Timestream for InfluxDB), card 7 (order record in Aurora, read model in DocumentDB), card 9 (live session in ElastiCache, finished quote in DocumentDB), card 10 (AppConfig for staged rollout when no content query is needed). Not candidates, with the reason on the page: MongoDB Atlas (not an AWS service, differs only in R3-R5), Kinesis (card 4), AWS AppConfig (card 10, not a database).

Weights: R1 38-55 and the heaviest group on every card; R2-R5 at least 5. Placement rules used: the single primary is the scaling model of the instance-based cluster (R2), instance/replica/shard sizing is R4, the I/O price of TTL deletes and renewals is R5, missing elastic-cluster features are R3/R4.

## Facts added for model 2 (official sources)

- Elastic clusters: hash sharding, up to 32 shards, a shard has one writer and 0-15 replicas; not supported: ACID transactions, change streams, point-in-time restore, unique, partial, text and vector indexes, multi-field shard key, change shard key, DDL during scaling (https://docs.aws.amazon.com/documentdb/latest/devguide/elastic-how-it-works.html, https://docs.aws.amazon.com/documentdb/latest/devguide/docdb-using-elastic-clusters.html)
- Elastic cluster pricing per vCPU-hour of each shard instance (US East example 0.132 USD), storage per GB-month (https://aws.amazon.com/documentdb/pricing/)
- "Both TTL and change streams incur I/O's when data is written, read, and deleted" (https://docs.aws.amazon.com/documentdb/latest/devguide/best_practices.html)
- AWS DMS homogeneous migration to DocumentDB: full load and CDC through the source oplog (https://aws.amazon.com/blogs/database/aws-dms-homogenous-migration-from-document-oriented-databases-to-amazon-documentdb/)
- The other limits of the card reasons are listed with URLs in the comment block above `DOCDB_W`.

## Known traps (handled explicitly in Part A)

1. One primary for writes → A9 card "Primary ve replica", the "second writer: cannot" row, the "Replica eklersem yazma hızım artar mı?" and "Tek bir primary saniyede kaç yazma taşır?" boxes; M3 first row; card 4.
2. COLLSCAN without an index → A4 last row, A5 all-cases tables (second field only, regex, no index), B2 live plans (40 vs 200 examined) and the `scan` and `index` simulations.
3. Embed versus reference → A3 all-cases table (with "unbounded: cannot embed"), two "Aklına şu gelebilir" boxes, the order document anatomy.
4. Document size limit → A2 table row (16 MiB, nesting), A3 unbounded array row, quiz doc-q2, recall doc-r3.
5. MongoDB API version differences → A10 all-cases table "MongoDB kodu DocumentDB'de çalışır mı?", the API flow, two boxes; B3 retryable writes and the live `retryWrites=False` of Lale Market (engine 8.0.0).

## Live artifacts

| Structure | Artifact | How to take it |
|---|---|---|
| document | P0001, 12 top-level fields, 406 bytes | `/docdb/api/e2e/M1` (B1) |
| collection | collStats: 200 documents, avg 503 bytes, 4 indexes, 81,920 bytes of index | `/docdb/api/e2e/M7` (B1) |
| index | `getIndexes()`: `_id_`, `category_1_rating_-1`, `attributes.renk_1`, `rating_-1` | `/docdb/api/e2e/M6` (B1) |
| filter on nested field | 9 black electronics | `/docdb/api/e2e/M2` (B2) |
| filter on array | 55 documents with tag indirim | `/docdb/api/e2e/M3` (B2) |
| query plans | IXSCAN 40 examined / 40 returned; COLLSCAN 200 / 40 with SORT | `/docdb/api/e2e/M4` (B2) |
| aggregation | tag counts summing to 400 | `/docdb/api/e2e/M5` (B4) |
| cluster | engine 8.0.0, db.r6g.large × 2 in eu-central-1b/1c, volume in three AZs, endpoints, BackupRetentionPeriod 1 | `aws docdb describe-db-clusters`, `describe-db-instances` (read-only) and `cloudformation/workshop.yaml` (C3) |

## Teaching data

`DOCS` in `e2e_sims.py`: seven real Lale Market products (P0001, P0005, P0026, P0044, P0095, P0142, P0179) with `name`, `category`, `price`, `rating`, `attributes.renk`, `attributes.garanti_ay`, `tags`; rendered flattened with `k.sample("products_docs")` in A2. The order document of A3 (O000001) and the list L1 of A6/B3 are examples.

## Images

`docdb-btree.png` (Wikimedia, CC BY-SA 3.0), `docdb-cluster.png`, `docdb-endpoints.png` (AWS documentation, existing records), new: `docdb-shard-key.png` and `docdb-elastic.png` (AWS DocumentDB Developer Guide, elastic clusters; records added to `e2e/images.yaml`). Every image was looked at. A1, A3, A4, A6, A7, A8, A10 use the page's own `.flow`, `.parts` and `.docanat` drawings.
