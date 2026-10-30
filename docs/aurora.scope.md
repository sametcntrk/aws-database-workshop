# Scope: Aurora PostgreSQL (aurora)

status: verified domain-map row, regenerated in model 2 (weighted R1 "Engine uyumu")
domain-map row: verified
date: 2026-10-30 (model 2); first version 2026-10-29 (model 1)

Page: `app/engine_app/templates/e2e/aurora.tr.html` (Turkish only; the old English `aurora.html` stays untouched and still renders the model 1 data). Data: `AURORA_W` at the end of `app/engine_app/e2e_usecases_w.py` (model 2), registered as `USECASES_W["aurora"]` and `PAGE_SVC["aurora"] = "aur"`. Simulations: `_aurora()` in `app/engine_app/e2e_sims.py` adds `weighted_scorecard` for every card with a `sim` when `lang == "tr"` (`w_checkout`, `w_catalog`, `w_ledger`, `w_tenant`, `w_reporting`); the nine mechanism simulations are unchanged. Kept for the English page: `AURORA_USECASES` (model 1), the `win_checkout`, `lose_reporting`, `race_*` and `decide_*` simulations. Check: `check_usecases.py --app app aurora`.

## Part A topic and the everyday picture (A1)

- Category in one general term: the relational database (tables, rows, keys, SQL, transactions)
- Everyday picture: a bookshop with three cashiers and one shared spreadsheet file; the database is the single clerk behind the counter
- The trade (what it gives, what it takes): every fact once and tables linked by keys / a screen joins several tables at query time; a question on any column without redesign / the planner decides the path, a wrong plan is a slow query; rules in the database, applied on every write / rules are written up front, a new column is a schema change; several writes in several tables all-or-nothing, the second writer waits / all writes go through one writer

## Feature list Ö1–Ö8 (F1–F8 of the domain map)

| No | Feature | Defining section | Official sentence (URL) | Limit |
|---|---|---|---|---|
| Ö1 | Schema with types and constraints | A2 | "a check constraint is satisfied if the check expression evaluates to true or the null value" (https://www.postgresql.org/docs/current/ddl-constraints.html) | rules are written up front; a frequently changing shape needs JSONB or a migration |
| Ö2 | Primary and foreign keys (relations) | A3 | "Adding a primary key will automatically create a unique B-tree index" (same URL) | no relation means pure overhead; many-to-many needs a link table |
| Ö3 | SQL on any column, JOIN, GROUP BY | A4 | PostgreSQL SQL tutorial (https://www.postgresql.org/docs/current/tutorial-sql.html) | full scans run on one server and read whole rows; no typo-tolerant relevance search |
| Ö4 | Indexes chosen by a planner | A5 | B-tree default, EXPLAIN (https://www.postgresql.org/docs/current/indexes-types.html, https://www.postgresql.org/docs/current/using-explain.html) | every index costs on every write; the planner may skip an index (function, '%x%', non-selective) |
| Ö5 | Transactions and row locks (ACID) | A6 | Read Committed default, UPDATE re-evaluates the WHERE on the new row version, Serializable needs retries (https://www.postgresql.org/docs/current/transaction-iso.html) | one writer; a hot row becomes a queue; long transactions keep locks and dead tuples |
| Ö6 | Views and functions (triggers) | A7 | PostgreSQL views and triggers (https://www.postgresql.org/docs/current/sql-createview.html) | not a workflow engine; trigger code needs versioning and tests |
| Ö7 | Replication and failover | A8 | six storage nodes in three AZs, up to 15 Aurora Replicas, failover "typically restored in less than 60 seconds, and often less than 30 seconds", replica lag "usually considerably less than 100 milliseconds" (https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Concepts.AuroraHighAvailability.html, https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Aurora.Managing.Performance.html) | the writer is single; write volume beyond one writer needs sharding (Limitless) or another model |
| Ö8 | Extensions (JSONB, PostGIS, pgvector) and row-level security | A9 | RLS definition and bypass by superusers and owners (https://www.postgresql.org/docs/current/ddl-rowsecurity.html); Aurora PostgreSQL 17.9 extension versions, PostGIS 3.5.1, pgvector 0.8.1 (https://docs.aws.amazon.com/AmazonRDS/latest/AuroraPostgreSQLReleaseNotes/AuroraPostgreSQL.Extensions.html) | no foreign key inside JSONB; only the supported extension list; policies need per-role tests |

## All cases per concept

| Section | Concept | Cases (including the impossible one) |
|---|---|---|
| A2 | value written into a column | fits the type; wrong type (refused); NULL allowed; NOT NULL (refused); CHECK broken (refused, CHECK accepts NULL); DEFAULT; column not in the schema (cannot) |
| A2 | schema change | add column; drop column; change type; add rule with an existing violating row (refused); drop a table that is referenced (refused) |
| A3 | two rows, primary key and foreign key | same primary key (no); different / same foreign key (group); different / different; foreign key without owner (no); NULL foreign key |
| A3 | owner row deleted | RESTRICT (refused); CASCADE; SET NULL; no foreign key (no check) |
| A4 | a question and its SQL | by primary key; any column; range, pattern, list; JOIN; LEFT JOIN; GROUP BY; HAVING; ORDER BY LIMIT; information not in the schema (cannot); typo-tolerant ranked search (cannot at scale) |
| A4 | JOIN matching | owner exists; owner with many borrowers; owner without borrowers; join without condition (cross product); many-to-many needs a link table |
| A5 | a condition and the planner | primary key equality; indexed range; prefix LIKE; '%x%' (index unusable); function on column (index unusable); no index; non-selective condition (seq scan); tiny table |
| A6 | how a transaction ends | COMMIT; ROLLBACK; crash before COMMIT; error inside (aborted state); undo after COMMIT (cannot); long open transaction |
| A6 | two sessions on one row | read/read; write/read (MVCC); write/write (lock wait, re-test); read then write both (lost update); opposite order (deadlock); SELECT FOR UPDATE |
| A7 | forms of a view | plain view read; materialized read; refresh; write into a view (cannot in general); drop a column used by a view (refused) |
| A7 | where logic lives | constraint; trigger or application transaction; view; materialized view; workflow (not the database's job) |
| A8 | failure and copies | reader down; writer down (failover); AZ down; Region down; replica lag; second writer (cannot); wrong DELETE committed (copy is not a backup) |
| A9 | shape and place of data | fixed columns; JSONB; JSONB with GIN; foreign key inside JSONB (cannot); PostGIS; pgvector; row-level security; large files (not in the database) |
| C2 | which job to which endpoint | writes (cluster); read-your-own-write (cluster); reports (reader); failover with an open connection |

## Anatomy list and colors

- Core data structures: table, row, column, primary key, foreign key, index, transaction (and in Part B: page, tuple)
- Colors: primary key yellow (`c-pk`), foreign key blue (`c-sk`), other columns grey; stated in the A3 anatomy caption; `k.sample(..., pk=, sk=)` and the anatomy diagrams of A3 and B1 use the same colors

## Matrix products (A10)

PostgreSQL (community), MySQL, Aurora PostgreSQL

## R1 catalog of the domain

Domain: database. Catalog: `R1_CATALOG` of `e2e_usecases_w.py` (VM, ŞE, EY, OY, TA, DA, YD, AO), accepted by the owner on 2026-10-29. The page shows it under the R1–R5 callout with an Aurora PostgreSQL example per code.

## Use cases (M2): candidates, weights, results (model 2)

| No | Use case | Candidates (best fit first) | R1 sub-items (codes) | R1 weight | Totals /100 | sim |
|---|---|---|---|---|---|---|
| 1 | Checkout: order, stock, payment (Lale Market) | Aurora, DocumentDB, DynamoDB | TA, ŞE, EY, OY | 50 | 96.9 / 79.2 / 75.7 | w_checkout |
| 2 | Product catalog with relations | Aurora, DocumentDB, OpenSearch | VM, ŞE, EY, TA | 50 | 86.8 / 82.1 / 62 (race; DocumentDB wins R1 43.2 to 42.2) | w_catalog |
| 3 | Warehouse stock with reservations | Aurora, DynamoDB, MemoryDB | TA, OY, YD, EY | 48 | 90.6 / 79.9 / 78.8 | |
| 4 | Customer accounts, addresses, consents | Aurora, RDS for PostgreSQL, DocumentDB | ŞE, TA, EY, VM | 48 | 96.6 / 92.6 / 82.8 (R1 equal with RDS) | |
| 5 | Multi-tenant SaaS with row-level security | **RDS for PostgreSQL**, Aurora, DynamoDB | AO, ŞE, EY | 40 (R5 20, R2 18; note says why) | 90 / 88 / 64.4 (race, R1 equal) | w_tenant |
| 6 | Reporting: 90 days to three years | **Redshift**, Aurora, OpenSearch | DA, EY, AO, OY | 48 | 93.6 / 63.8 / 62 | w_reporting |
| 7 | Invoices and double-entry ledger | Aurora, RDS for PostgreSQL, DynamoDB | TA, ŞE, EY, AO | 48 | 94 / 87 / 69.6 (R1 equal) | w_ledger |
| 8 | Appointments: non-overlapping ranges | Aurora, DynamoDB, MemoryDB | TA, EY, VM, YD | 48 | 94.6 / 74 / 71 | |
| 9 | Workflow state with audit trail | Aurora, RDS for PostgreSQL, DynamoDB | TA, ŞE, EY, YD | 56 | 96 / 96 / 78.2 (tie with RDS, close race) | |
| 10 | Geospatial: zones and nearest points (PostGIS) | Aurora, OpenSearch, DynamoDB | EY, VM, DA, TA | 48 | 92.5 / 67 / 61.6 | |

Changes after the reader simulation (2026-10-30, docs/aurora.reader-report.md): RDS for PostgreSQL replaced DynamoDB in card 4 and DocumentDB in card 9 (same engine, small or flat loads); in cards 1, 2, 3, 8, 10 the verdict or the M2 summary says why RDS is not shown (R1 equal, the race the card teaches is with another engine; card 1: Aurora already runs in Lale Market). ACU range choice is always R4, a known peak is R2. Card 9 R4 weight 18 → 10 (the rule moved to R1). Amazon Location Service: not a database; named in card 10 as the routing/geofence companion. Prices used: eu-central-1 on demand 2026-10-29, ACU-hour 0.14 USD, db.r6g.xlarge RDS 0.549 / Aurora 0.627 USD/h.

Candidate changes against model 1: card 3 and card 8 replace ElastiCache with MemoryDB (stock and appointments are official records; ElastiCache Serverless has no durable log, the same rule as the DynamoDB page). Card 1 now ranks DocumentDB second (multi-document transactions, `$jsonSchema`). Services checked and left out: Aurora DSQL and Limitless (no card needs multi-Region writes or more than one writer), Athena (card 6 needs data within seconds; an S3 export is periodic), ElastiCache (no durable log), Neptune (no card has multi-hop relations), Step Functions (card 9: named in the verdict as the workflow engine next to Aurora, not a database candidate).

- Aurora clearly loses: card 6 (Redshift, gap 29.8; R1 · DA row store vs columnar).
- Aurora loses a close race: card 5 (RDS for PostgreSQL, gap 2; same engine, R5 price on flat traffic). Card 9 is a tie with RDS (96 / 96).
- Another engine wins R1 but loses on the total: card 2 (DocumentDB R1 43.2 vs 42.2; Aurora wins on R4/R5 because the orders already run in Aurora and the team knows SQL).
- R1 equal and service design decides: cards 4, 5, 7 and 9 (RDS for PostgreSQL), a pair that flips on the traffic shape.
- "Both together": card 6 (Aurora as system of record + zero-ETL to Redshift), card 2 (Aurora catalog + OpenSearch for search via OpenSearch Ingestion), card 9 (verdict: Step Functions for a growing workflow, Aurora for state and audit), card 10 (OpenSearch for a text-plus-geo discovery screen).

Consistency rules applied across the cards (and with the DynamoDB page): no TTL in PostgreSQL = YD 7 when the expiry is inside the condition (cards 3, 8; same as the DynamoDB seat card), 4 when a cleanup job is the only way (DynamoDB page); MVCC on hot updates = OY/DA 1–2 off; MemoryDB R4 5 (no serverless + new API for a SQL team), R5 5; DocumentDB R4 6 (new cluster + new API); DynamoDB TTL "within a few days" = YD 5 when stock must return in 15 minutes (card 3), 7 when the expiry is a condition (card 8); DynamoDB transaction conflicts on hot items = TA 2–3 off.

## New facts used in model 2 (with source)

| Claim | Source |
|---|---|
| RDS for PostgreSQL: up to 15 read replicas per source instance | https://aws.amazon.com/rds/faqs/ |
| RDS Multi-AZ instance failover "typically complete within one to two minutes" | https://aws.amazon.com/rds/features/multi-az/ |
| RDS Multi-AZ DB cluster failover "typically less than 35 seconds" | https://docs.aws.amazon.com/cli/latest/reference/rds/failover-db-cluster.html |
| eu-central-1 on demand, db.r6g.large: RDS for PostgreSQL 0.274 USD/h, Aurora PostgreSQL 0.313 USD/h, Aurora I/O-Optimized 0.407 USD/h | AWS Price List API (AmazonRDS), publication 2026-10-29 |
| Aurora storage grows to 128 TiB; I/O-Optimized saves when I/O exceeds 25% of spend; RDS storage auto scaling | https://aws.amazon.com/blogs/database/is-amazon-rds-for-postgresql-or-amazon-aurora-postgresql-a-better-choice-for-me/ |
| DynamoDB transaction conflicts: TransactionConflictException / TransactionCanceledException on concurrent requests to the same item | https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/transaction-apis.html |
| DocumentDB `$jsonSchema` validation (4.0 and later), document size 16 MiB | https://docs.aws.amazon.com/documentdb/latest/devguide/json-schema-validation.html, https://docs.aws.amazon.com/documentdb/latest/devguide/limits.html |
| Redshift: columnar store in 1 MB blocks, per-column compression | https://aws.amazon.com/blogs/big-data/getting-the-most-out-of-your-analytics-stack-with-amazon-redshift/ |
| Redshift Serverless: RPU-hours per second, 60-second minimum, base 4–1024 RPU, no charge when idle | https://aws.amazon.com/redshift/pricing/ |
| OpenSearch Ingestion streams Aurora PostgreSQL changes (CDC) into OpenSearch | https://docs.aws.amazon.com/opensearch-service/latest/developerguide/configure-client-aurora.html |
| OpenSearch geo_distance, geo_bounding_box, geo_shape | https://aws.amazon.com/blogs/database/building-search-experiences-for-json-data-with-amazon-opensearch-service/ |

The model 1 facts (six copies in three AZs, failover under 60/30 seconds, 15 replicas, replica lag, Serverless v2 ACU, zero-ETL within seconds, RLS, exclusion constraints, VACUUM) keep their sources in the page and in the comment block of `AURORA_W`.

## Known traps (handled explicitly in Part A)

1. One writer → A8 concept "Replica", the "second writer: cannot" row, the "You may ask" box on why writes do not scale with replicas; M3 first row.
2. MVCC and dead rows (vacuum) → A6 "Row lock" card (MVCC), the "long open transaction" row; B1 "Tuple" card; B6 vacuum row and checkpoint.
3. A lost update without a lock → A6 two flow diagrams and the "read then write" row of the two-session table; B5 `lost` and `locked` simulations.
4. An index that the planner does not use → A5 all-cases table ('%x%', function on column, non-selective condition, tiny table) and the "You may ask" box; B2 live plans.
5. ACU minimum cost → M5 Serverless v2 row (0.5–256 ACU, 0 with auto-pause on supported versions), B6 cost table; every card's R5 reason names the minimum capacity.

## Live artifacts

| Structure | Artifact | How to take it |
|---|---|---|
| row | `SELECT * FROM customers WHERE customer_id = 'C00001'` | live site `/aurora/api/e2e/A2` (B1) |
| table sizes | row counts of the four tables (1000, 200, 5007, 12519) | `/aurora/api/e2e/A1` (B1) |
| JOIN result | O000001 with customer and product names, 4 rows | `/aurora/api/e2e/A3` (B3) |
| GROUP BY result | revenue per category over 12,519 lines | `/aurora/api/e2e/A4` (B3) |
| indexes | `pg_indexes` of the public schema | `/aurora/api/e2e/A5` (B1) |
| query plans | Index Scan (shared hit=3) and Seq Scan (shared hit=20, 999 rows removed) | `/aurora/api/e2e/A6`, `A7` (B2) |
| refused writes | foreign key violation and check violation messages | `/aurora/api/e2e/A8`, `A9` (B4) |
| conditional UPDATE | `RETURNING stock_after = 123`, then ROLLBACK | `/aurora/api/e2e/A10` (B5) |
| cluster | engine 17.9, Serverless v2 0.5–4 ACU, writer in eu-central-1a, reader in 1b, three AZs, endpoints | `aws rds describe-db-clusters` (C3) |

## Teaching data

The four tables of `e2e_sims.py` (`CUSTOMERS` 6 rows, `PRODUCTS` 5 rows, `ORDERS` 4 rows, `ITEMS` 9 rows), rendered with `k.sample` in A2 and A3; names and prices come from the real Lale Market data, stock values and the orders after O000001 are examples.
